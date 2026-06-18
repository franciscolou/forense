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
from app.models.firm import Firm
from app.models.lawyer import Lawyer, LawyerEducation, LawyerLanguage
from app.models.practice_area import PracticeArea
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

        await session.commit()
    logger.info("Seed completed.")
