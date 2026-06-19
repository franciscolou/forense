"""Idempotent development seed data.

Populates the canonical list of practice areas and a handful of demo lawyers /
firms so the client-view search returns something on a fresh database. Safe to
run repeatedly; it skips work that is already present.
"""
from __future__ import annotations

import logging

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.availability import AvailabilityRule
from app.models.booking_configuration import (
    AgendaVisibility,
    ApprovalMode,
    BookingConfiguration,
    PaymentMode,
    TriageMode,
)
from app.models.client import Client
from app.models.firm import Firm
from app.models.lawyer import Lawyer, LawyerEducation, LawyerLanguage
from app.models.practice_area import PracticeArea
from app.models.triage import QuestionType, TriageQuestion
from app.models.user import User, UserRole

logger = logging.getLogger(__name__)

PRACTICE_AREAS = [
    ("Direito Trabalhista", "trabalhista"),
    ("Direito Tributário", "tributario"),
    ("Direito Penal", "penal"),
    ("Direito Civil", "civil"),
    ("Direito de Família", "familia"),
    ("Direito Empresarial", "empresarial"),
    ("Direito do Consumidor", "consumidor"),
    ("Direito Imobiliário", "imobiliario"),
    ("Direito Previdenciário", "previdenciario"),
    ("Direito Digital", "digital"),
]


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        # --- Practice areas (upsert by slug) ---------------------------
        existing = {
            pa.slug: pa
            for pa in (await session.execute(select(PracticeArea))).scalars().all()
        }
        for name, slug in PRACTICE_AREAS:
            if slug not in existing:
                pa = PracticeArea(name=name, slug=slug)
                session.add(pa)
                existing[slug] = pa
        await session.flush()

        # --- Demo accounts: only seed if no lawyers exist yet ----------
        has_lawyer = (await session.execute(select(Lawyer.id).limit(1))).first()
        if not has_lawyer:
            ana = User(
                email="ana.advogada@forense.dev",
                hashed_password=hash_password("senha1234"),
                full_name="Ana Beatriz Martins",
                role=UserRole.LAWYER,
            )
            ana.lawyer = Lawyer(
                oab_uf="SP",
                oab_number="123456",
                oab_verified=True,
                bio="Especialista em Direito Trabalhista com atuação em causas de rescisão e assédio.",
                years_of_experience=12,
                city="São Paulo",
                state="SP",
                practice_areas=[existing["trabalhista"], existing["civil"]],
                educations=[
                    LawyerEducation(
                        degree="graduacao",
                        institution="USP",
                        field_of_study="Direito",
                        year=2012,
                    ),
                    LawyerEducation(
                        degree="pos-graduacao",
                        institution="FGV",
                        field_of_study="Direito do Trabalho",
                        year=2015,
                    ),
                ],
                languages=[
                    LawyerLanguage(language="Português", proficiency="nativo"),
                    LawyerLanguage(language="Inglês", proficiency="avancado"),
                ],
            )

            carlos = User(
                email="carlos.tributario@forense.dev",
                hashed_password=hash_password("senha1234"),
                full_name="Carlos Henrique Souza",
                role=UserRole.LAWYER,
            )
            carlos.lawyer = Lawyer(
                oab_uf="RJ",
                oab_number="987654",
                oab_verified=False,
                bio="Atuação em planejamento tributário para empresas de tecnologia.",
                years_of_experience=8,
                city="Rio de Janeiro",
                state="RJ",
                practice_areas=[existing["tributario"], existing["empresarial"]],
                languages=[LawyerLanguage(language="Português", proficiency="nativo")],
            )

            session.add_all([ana, carlos])
            await session.flush()

            firm_user = User(
                email="contato@martinssouza.adv.br",
                hashed_password=hash_password("senha1234"),
                full_name="Martins & Souza Advogados Associados",
                role=UserRole.FIRM,
            )
            firm_user.firm = Firm(
                legal_name="Martins & Souza Advogados Associados",
                cnpj="12345678000190",
                oab_registration="OAB/SP 9999",
                description="Banca full-service com foco em direito empresarial e tributário.",
                city="São Paulo",
                state="SP",
                website="https://martinssouza.adv.br",
                practice_areas=[existing["tributario"], existing["empresarial"], existing["trabalhista"]],
                lawyers=[ana.lawyer, carlos.lawyer],
            )
            session.add(firm_user)

            # Demo client — needed to exercise the booking flow end-to-end.
            client_user = User(
                email="cliente@forense.dev",
                hashed_password=hash_password("senha1234"),
                full_name="João da Silva",
                role=UserRole.CLIENT,
            )
            client_user.client = Client(
                phone="(11) 99999-0000",
                city="São Paulo",
                state="SP",
            )
            session.add(client_user)

        await session.commit()
        await _seed_booking(session)
    logger.info("Seed completed.")


def _example_questions() -> list[TriageQuestion]:
    """Placeholder triage questions — structure over content (to be revised)."""
    return [
        TriageQuestion(
            text="Qual é a área do seu problema?",
            qtype=QuestionType.SINGLE_CHOICE,
            options=["Trabalhista", "Tributário", "Penal", "Família", "Outro"],
            order=1,
            required=True,
        ),
        TriageQuestion(
            text="Existe processo em andamento?",
            qtype=QuestionType.BOOLEAN,
            order=2,
            required=True,
        ),
        TriageQuestion(
            text="Há urgência?",
            qtype=QuestionType.BOOLEAN,
            order=3,
            required=False,
        ),
        TriageQuestion(
            text="Deseja atendimento presencial ou online?",
            qtype=QuestionType.SINGLE_CHOICE,
            options=["Presencial", "Online"],
            order=4,
            required=True,
        ),
    ]


def _weekly_rules(provider_user_id: int, weekdays: list[int]) -> list[AvailabilityRule]:
    """Two daily windows (manhã 9–12, tarde 14–18) on the given weekdays."""
    rules = []
    for wd in weekdays:
        rules.append(
            AvailabilityRule(
                provider_user_id=provider_user_id, weekday=wd, start_hour=9, end_hour=12
            )
        )
        rules.append(
            AvailabilityRule(
                provider_user_id=provider_user_id, weekday=wd, start_hour=14, end_hour=18
            )
        )
    return rules


async def _seed_booking(session) -> None:
    """Give the demo providers distinct booking configurations + slots, showing
    that different setting combinations yield different flows. Idempotent."""
    if (await session.execute(select(BookingConfiguration.id).limit(1))).first():
        return

    async def user_by_email(email: str) -> User | None:
        return (
            await session.execute(select(User).where(User.email == email))
        ).scalar_one_or_none()

    ana = await user_by_email("ana.advogada@forense.dev")
    carlos = await user_by_email("carlos.tributario@forense.dev")
    firm = await user_by_email("contato@martinssouza.adv.br")
    if not (ana and carlos and firm):
        return

    # Ana → Doctoralia-like: sem triagem, agenda imediata, aprovação automática.
    session.add(
        BookingConfiguration(
            user_id=ana.id,
            triage_mode=TriageMode.DISABLED,
            agenda_visibility=AgendaVisibility.IMMEDIATE,
            approval_mode=ApprovalMode.AUTOMATIC,
            payment_mode=PaymentMode.NONE,
            max_advance_days=30,
        )
    )
    # Seg–Sex (0–4) com janelas manhã/tarde.
    session.add_all(_weekly_rules(ana.id, [0, 1, 2, 3, 4]))

    # Carlos → triagem obrigatória, agenda após triagem, aprovação manual.
    session.add(
        BookingConfiguration(
            user_id=carlos.id,
            triage_mode=TriageMode.REQUIRED,
            agenda_visibility=AgendaVisibility.AFTER_TRIAGE,
            approval_mode=ApprovalMode.MANUAL,
            payment_mode=PaymentMode.NONE,
            min_advance_days=1,
            max_advance_days=90,
            questions=_example_questions(),
        )
    )
    # Ter/Qui (1,3).
    session.add_all(_weekly_rules(carlos.id, [1, 3]))

    # Escritório → triagem opcional, sem agenda pública, aprovação manual.
    session.add(
        BookingConfiguration(
            user_id=firm.id,
            triage_mode=TriageMode.OPTIONAL,
            agenda_visibility=AgendaVisibility.HIDDEN,
            approval_mode=ApprovalMode.MANUAL,
            payment_mode=PaymentMode.NONE,
            questions=_example_questions(),
        )
    )

    await session.commit()
