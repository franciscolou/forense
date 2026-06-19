"""FastAPI dependency wiring (composition root).

Repositories and services are constructed here and injected into routers via
``Depends``. This is the single place that knows how the object graph is wired,
keeping the rest of the code decoupled and testable (swap a dependency override
in tests).
"""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_session
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.core.security import decode_access_token
from app.models.user import User, UserRole
from app.repositories.availability import (
    AvailabilityExceptionRepository,
    AvailabilityRepository,
    AvailabilityRuleRepository,
)
from app.repositories.booking import BookingRepository
from app.repositories.booking_configuration import BookingConfigurationRepository
from app.repositories.firm import FirmRepository
from app.repositories.lawyer import LawyerRepository
from app.repositories.practice_area import PracticeAreaRepository
from app.repositories.triage import TriageQuestionRepository
from app.repositories.user import UserRepository
from app.services.auth_service import AuthService
from app.services.availability_service import AvailabilityService
from app.services.booking.flow import BookingFlowEngine
from app.services.booking_configuration_service import BookingConfigurationService
from app.services.booking_service import BookingService
from app.services.directory_service import DirectoryService
from app.services.oab_validation import OABValidator, get_oab_validator
from app.services.registration_service import RegistrationService

SessionDep = Annotated[AsyncSession, Depends(get_session)]

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/login", auto_error=False
)


# --- Repositories -------------------------------------------------------
def get_user_repository(session: SessionDep) -> UserRepository:
    return UserRepository(session)


def get_lawyer_repository(session: SessionDep) -> LawyerRepository:
    return LawyerRepository(session)


def get_firm_repository(session: SessionDep) -> FirmRepository:
    return FirmRepository(session)


def get_practice_area_repository(session: SessionDep) -> PracticeAreaRepository:
    return PracticeAreaRepository(session)


UserRepoDep = Annotated[UserRepository, Depends(get_user_repository)]
LawyerRepoDep = Annotated[LawyerRepository, Depends(get_lawyer_repository)]
FirmRepoDep = Annotated[FirmRepository, Depends(get_firm_repository)]
PracticeAreaRepoDep = Annotated[PracticeAreaRepository, Depends(get_practice_area_repository)]


# --- Strategies ---------------------------------------------------------
def get_oab_validator_dep() -> OABValidator:
    return get_oab_validator()


# --- Services -----------------------------------------------------------
def get_auth_service(users: UserRepoDep) -> AuthService:
    return AuthService(users)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


def get_registration_service(
    session: SessionDep,
    users: UserRepoDep,
    lawyers: LawyerRepoDep,
    firms: FirmRepoDep,
    practice_areas: PracticeAreaRepoDep,
    auth_service: AuthServiceDep,
    oab_validator: Annotated[OABValidator, Depends(get_oab_validator_dep)],
) -> RegistrationService:
    return RegistrationService(
        session=session,
        users=users,
        lawyers=lawyers,
        firms=firms,
        practice_areas=practice_areas,
        oab_validator=oab_validator,
        auth_service=auth_service,
    )


def get_directory_service(
    lawyers: LawyerRepoDep,
    firms: FirmRepoDep,
    practice_areas: PracticeAreaRepoDep,
) -> DirectoryService:
    return DirectoryService(lawyers, firms, practice_areas)


RegistrationServiceDep = Annotated[RegistrationService, Depends(get_registration_service)]
DirectoryServiceDep = Annotated[DirectoryService, Depends(get_directory_service)]


# --- Auth ---------------------------------------------------------------
async def get_current_user(
    users: UserRepoDep,
    token: Annotated[str | None, Depends(oauth2_scheme)],
) -> User:
    if not token:
        raise AuthenticationError("Não autenticado")
    subject = decode_access_token(token)
    if subject is None:
        raise AuthenticationError("Token inválido ou expirado")
    user = await users.get(int(subject))
    if user is None or not user.is_active:
        raise AuthenticationError("Usuário não encontrado ou inativo")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def require_provider(current_user: CurrentUser) -> User:
    """Guard for endpoints only a provider (lawyer or firm) may call."""
    if current_user.role not in (UserRole.LAWYER, UserRole.FIRM):
        raise AuthorizationError("Disponível apenas para advogados e escritórios")
    return current_user


ProviderUser = Annotated[User, Depends(require_provider)]


# --- Booking repositories ----------------------------------------------
def get_booking_repository(session: SessionDep) -> BookingRepository:
    return BookingRepository(session)


def get_booking_config_repository(session: SessionDep) -> BookingConfigurationRepository:
    return BookingConfigurationRepository(session)


def get_triage_question_repository(session: SessionDep) -> TriageQuestionRepository:
    return TriageQuestionRepository(session)


def get_availability_repository(session: SessionDep) -> AvailabilityRepository:
    return AvailabilityRepository(session)


def get_availability_rule_repository(session: SessionDep) -> AvailabilityRuleRepository:
    return AvailabilityRuleRepository(session)


def get_availability_exception_repository(
    session: SessionDep,
) -> AvailabilityExceptionRepository:
    return AvailabilityExceptionRepository(session)


BookingRepoDep = Annotated[BookingRepository, Depends(get_booking_repository)]
BookingConfigRepoDep = Annotated[
    BookingConfigurationRepository, Depends(get_booking_config_repository)
]
TriageQuestionRepoDep = Annotated[
    TriageQuestionRepository, Depends(get_triage_question_repository)
]
AvailabilityRepoDep = Annotated[AvailabilityRepository, Depends(get_availability_repository)]
AvailabilityRuleRepoDep = Annotated[
    AvailabilityRuleRepository, Depends(get_availability_rule_repository)
]
AvailabilityExceptionRepoDep = Annotated[
    AvailabilityExceptionRepository, Depends(get_availability_exception_repository)
]


# --- Availability service ----------------------------------------------
def get_availability_service(
    session: SessionDep,
    rules: AvailabilityRuleRepoDep,
    exceptions: AvailabilityExceptionRepoDep,
    slots: AvailabilityRepoDep,
    configs: BookingConfigRepoDep,
) -> AvailabilityService:
    return AvailabilityService(session, rules, exceptions, slots, configs)


AvailabilityServiceDep = Annotated[AvailabilityService, Depends(get_availability_service)]


# --- Booking services --------------------------------------------------
def get_booking_flow_engine() -> BookingFlowEngine:
    return BookingFlowEngine()


def get_booking_configuration_service(
    session: SessionDep,
    configs: BookingConfigRepoDep,
    questions: TriageQuestionRepoDep,
) -> BookingConfigurationService:
    return BookingConfigurationService(session, configs, questions)


BookingConfigurationServiceDep = Annotated[
    BookingConfigurationService, Depends(get_booking_configuration_service)
]


def get_booking_service(
    session: SessionDep,
    bookings: BookingRepoDep,
    availability: AvailabilityRepoDep,
    availability_service: AvailabilityServiceDep,
    questions: TriageQuestionRepoDep,
    users: UserRepoDep,
    config_service: BookingConfigurationServiceDep,
    engine: Annotated[BookingFlowEngine, Depends(get_booking_flow_engine)],
) -> BookingService:
    return BookingService(
        session=session,
        bookings=bookings,
        availability=availability,
        availability_service=availability_service,
        questions=questions,
        users=users,
        config_service=config_service,
        engine=engine,
    )


BookingServiceDep = Annotated[BookingService, Depends(get_booking_service)]
