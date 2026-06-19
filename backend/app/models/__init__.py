"""ORM models package.

Importing the models here ensures they are all registered on
``Base.metadata`` whenever ``app.models`` is imported (used by ``init_db``).
"""
from app.models.user import User, UserRole
from app.models.client import Client
from app.models.lawyer import Lawyer, LawyerEducation, LawyerLanguage
from app.models.firm import Firm
from app.models.practice_area import PracticeArea
from app.models.associations import (
    firm_lawyers,
    lawyer_practice_areas,
    firm_practice_areas,
)
from app.models.booking_configuration import (
    BookingConfiguration,
    TriageMode,
    AgendaVisibility,
    ApprovalMode,
    PaymentMode,
)
from app.models.triage import (
    QuestionType,
    TriageQuestion,
    TriageResponse,
    TriageAnswer,
)
from app.models.availability import (
    AvailabilityException,
    AvailabilityRule,
    AvailabilitySlot,
)
from app.models.booking import Booking, BookingStatus, PaymentState, StepKey

__all__ = [
    "User",
    "UserRole",
    "Client",
    "Lawyer",
    "LawyerEducation",
    "LawyerLanguage",
    "Firm",
    "PracticeArea",
    "firm_lawyers",
    "lawyer_practice_areas",
    "firm_practice_areas",
    "BookingConfiguration",
    "TriageMode",
    "AgendaVisibility",
    "ApprovalMode",
    "PaymentMode",
    "QuestionType",
    "TriageQuestion",
    "TriageResponse",
    "TriageAnswer",
    "AvailabilitySlot",
    "AvailabilityRule",
    "AvailabilityException",
    "Booking",
    "BookingStatus",
    "PaymentState",
    "StepKey",
]
