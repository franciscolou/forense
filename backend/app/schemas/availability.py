from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.schemas.common import ORMModel


# --- Recurring weekly rules --------------------------------------------
class RuleInput(BaseModel):
    weekday: int = Field(ge=0, le=6, description="0=segunda … 6=domingo")
    start_hour: int = Field(ge=0, le=23)
    end_hour: int = Field(ge=1, le=24)

    @model_validator(mode="after")
    def _check_range(self) -> "RuleInput":
        if self.end_hour <= self.start_hour:
            raise ValueError("end_hour deve ser após start_hour")
        return self


class RuleRead(ORMModel):
    id: int
    weekday: int
    start_hour: int
    end_hour: int


class RulesUpdate(BaseModel):
    """Replace-all of the weekly grid (declarative)."""

    rules: list[RuleInput] = Field(default_factory=list)


# --- Exceptions (blocked intervals) ------------------------------------
class ExceptionInput(BaseModel):
    start_at: datetime
    end_at: datetime
    note: str | None = None

    @model_validator(mode="after")
    def _check_range(self) -> "ExceptionInput":
        if self.end_at <= self.start_at:
            raise ValueError("end_at deve ser após start_at")
        return self


class ExceptionRead(ORMModel):
    id: int
    start_at: datetime
    end_at: datetime
    note: str | None = None


class ScheduleRead(BaseModel):
    rules: list[RuleRead]
    exceptions: list[ExceptionRead]


# --- Derived open slots / materialised slot ----------------------------
class OpenSlotRead(BaseModel):
    """A derived, bookable one-hour window (not yet persisted)."""

    start_at: datetime
    end_at: datetime


class SlotRead(ORMModel):
    id: int
    start_at: datetime
    end_at: datetime
    is_booked: bool
