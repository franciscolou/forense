"""Registration use-cases for each account type.

This service orchestrates repositories, password hashing and OAB validation
inside a single unit of work (the DB session). Business rules that the schemas
cannot express — unique email, unique OAB/CNPJ, "a firm needs >= 1 lawyer" —
are enforced here.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.security import hash_password
from app.models.client import Client
from app.models.firm import Firm
from app.models.lawyer import Lawyer, LawyerEducation, LawyerLanguage
from app.models.user import User, UserRole
from app.repositories.firm import FirmRepository
from app.repositories.lawyer import LawyerRepository
from app.repositories.practice_area import PracticeAreaRepository
from app.repositories.user import UserRepository
from app.schemas.auth import AuthResponse
from app.schemas.client import ClientRegisterRequest
from app.schemas.firm import FirmRegisterRequest
from app.schemas.lawyer import LawyerRegisterRequest
from app.services.auth_service import AuthService
from app.services.oab_validation import OABValidator


class RegistrationService:
    def __init__(
        self,
        session: AsyncSession,
        users: UserRepository,
        lawyers: LawyerRepository,
        firms: FirmRepository,
        practice_areas: PracticeAreaRepository,
        oab_validator: OABValidator,
        auth_service: AuthService,
    ) -> None:
        self._session = session
        self._users = users
        self._lawyers = lawyers
        self._firms = firms
        self._practice_areas = practice_areas
        self._oab = oab_validator
        self._auth = auth_service

    # -- Client ----------------------------------------------------------
    async def register_client(self, data: ClientRegisterRequest) -> AuthResponse:
        await self._ensure_email_available(data.email)

        user = User(
            email=data.email,
            hashed_password=hash_password(data.password),
            full_name=data.full_name,
            role=UserRole.CLIENT,
        )
        user.client = Client(phone=data.phone, city=data.city, state=data.state)
        self._users.add(user)

        await self._session.commit()
        await self._session.refresh(user)
        return self._auth.issue_token(user)

    # -- Lawyer ----------------------------------------------------------
    async def register_lawyer(self, data: LawyerRegisterRequest) -> AuthResponse:
        await self._ensure_email_available(data.email)
        await self._ensure_oab_available(data.oab_uf, data.oab_number)

        user = await self._build_lawyer_user(data)
        self._users.add(user)

        await self._session.commit()
        await self._session.refresh(user)
        return self._auth.issue_token(user)

    # -- Firm ------------------------------------------------------------
    async def register_firm(self, data: FirmRegisterRequest) -> AuthResponse:
        await self._ensure_email_available(data.email)
        if await self._firms.get_by_cnpj(data.cnpj) is not None:
            raise ConflictError("Já existe um escritório com este CNPJ")

        # Business rule: a firm must be composed of at least one lawyer.
        if not data.existing_lawyer_ids and not data.new_lawyers:
            raise ValidationError("O escritório deve ter ao menos um advogado")

        members: list[Lawyer] = []

        # Attach lawyers that already exist.
        if data.existing_lawyer_ids:
            existing = await self._lawyers.get_many_by_ids(data.existing_lawyer_ids)
            found_ids = {l.id for l in existing}
            missing = set(data.existing_lawyer_ids) - found_ids
            if missing:
                raise NotFoundError(f"Advogado(s) não encontrado(s): {sorted(missing)}")
            members.extend(existing)

        # Create brand-new lawyers on the spot.
        for new_lawyer in data.new_lawyers:
            await self._ensure_email_available(new_lawyer.email)
            await self._ensure_oab_available(new_lawyer.oab_uf, new_lawyer.oab_number)
            member_user = await self._build_lawyer_user(new_lawyer)
            self._users.add(member_user)
            members.append(member_user.lawyer)

        firm_user = User(
            email=data.email,
            hashed_password=hash_password(data.password),
            full_name=data.legal_name,
            role=UserRole.FIRM,
        )
        firm_user.firm = Firm(
            legal_name=data.legal_name,
            cnpj=data.cnpj,
            oab_registration=data.oab_registration,
            description=data.description,
            city=data.city,
            state=data.state,
            website=data.website,
            logo_url=data.logo_url,
            practice_areas=await self._resolve_practice_areas(data.practice_area_ids),
            lawyers=members,
        )
        self._users.add(firm_user)

        await self._session.commit()
        await self._session.refresh(firm_user)
        return self._auth.issue_token(firm_user)

    # -- Helpers ---------------------------------------------------------
    async def _build_lawyer_user(self, data: LawyerRegisterRequest) -> User:
        """Construct (but do not commit) a lawyer ``User`` with its profile."""
        oab_result = await self._oab.validate(data.oab_uf, data.oab_number)

        lawyer = Lawyer(
            oab_uf=data.oab_uf,
            oab_number=data.oab_number,
            oab_verified=oab_result.verified,
            bio=data.bio,
            years_of_experience=data.years_of_experience,
            city=data.city,
            state=data.state,
            photo_url=data.photo_url,
            practice_areas=await self._resolve_practice_areas(data.practice_area_ids),
            educations=[
                LawyerEducation(
                    degree=e.degree,
                    institution=e.institution,
                    field_of_study=e.field_of_study,
                    year=e.year,
                )
                for e in data.educations
            ],
            languages=[
                LawyerLanguage(language=l.language, proficiency=l.proficiency)
                for l in data.languages
            ],
        )
        user = User(
            email=data.email,
            hashed_password=hash_password(data.password),
            full_name=data.full_name,
            role=UserRole.LAWYER,
        )
        user.lawyer = lawyer
        return user

    async def _resolve_practice_areas(self, ids: list[int]):
        if not ids:
            return []
        areas = await self._practice_areas.get_by_ids(ids)
        missing = set(ids) - {a.id for a in areas}
        if missing:
            raise NotFoundError(f"Área(s) de atuação inexistente(s): {sorted(missing)}")
        return areas

    async def _ensure_email_available(self, email: str) -> None:
        if await self._users.email_exists(email):
            raise ConflictError("Já existe uma conta com este email")

    async def _ensure_oab_available(self, uf: str, number: str) -> None:
        if await self._lawyers.get_by_oab(uf, number) is not None:
            raise ConflictError(f"Já existe um advogado com a OAB/{uf} {number}")
