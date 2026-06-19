"""Generic triage questionnaire.

The structure is deliberately content-agnostic: a provider owns a list of
``TriageQuestion`` rows (customisable), and each booking that goes through triage
gets one ``TriageResponse`` holding a ``TriageAnswer`` per question. Answer values
are stored as JSON so any question type (text, boolean, choice) fits the same
shape. The seeded questions are placeholders to validate the mechanism.
"""
from __future__ import annotations

import enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.booking import Booking
    from app.models.booking_configuration import BookingConfiguration


class QuestionType(str, enum.Enum):
    TEXT = "text"
    BOOLEAN = "boolean"
    SINGLE_CHOICE = "single_choice"
    MULTI_CHOICE = "multi_choice"


class TriageQuestion(Base):
    __tablename__ = "triage_questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    configuration_id: Mapped[int] = mapped_column(
        ForeignKey("booking_configurations.id", ondelete="CASCADE"), nullable=False
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    qtype: Mapped[QuestionType] = mapped_column(
        SAEnum(QuestionType), default=QuestionType.TEXT, nullable=False
    )
    # Choices for SINGLE_CHOICE / MULTI_CHOICE; ignored for TEXT / BOOLEAN.
    options: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    configuration: Mapped["BookingConfiguration"] = relationship(back_populates="questions")


class TriageResponse(Base):
    __tablename__ = "triage_responses"

    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(
        ForeignKey("bookings.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    booking: Mapped["Booking"] = relationship(back_populates="triage_response")
    answers: Mapped[list["TriageAnswer"]] = relationship(
        back_populates="response", cascade="all, delete-orphan"
    )


class TriageAnswer(Base):
    __tablename__ = "triage_answers"

    id: Mapped[int] = mapped_column(primary_key=True)
    response_id: Mapped[int] = mapped_column(
        ForeignKey("triage_responses.id", ondelete="CASCADE"), nullable=False
    )
    question_id: Mapped[int] = mapped_column(
        ForeignKey("triage_questions.id", ondelete="CASCADE"), nullable=False
    )
    # Free-form JSON: a string, a bool, or a list of strings depending on type.
    value: Mapped[Any] = mapped_column(JSON, nullable=True)
    # Snapshot of the question text so historical responses stay readable even if
    # the provider later edits/removes the question.
    question_text: Mapped[str] = mapped_column(String(500), nullable=False)

    response: Mapped["TriageResponse"] = relationship(back_populates="answers")
