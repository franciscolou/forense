from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from app.models.booking_configuration import (
    MAX_ADVANCE_DAYS_LIMIT,
    AgendaVisibility,
    ApprovalMode,
    LawyerSelectionMode,
    PaymentMode,
    TriageMode,
)
from app.schemas.common import ORMModel
from app.schemas.triage import TriageQuestionRead


class BookingConfigurationUpdate(BaseModel):
    triage_mode: TriageMode
    agenda_visibility: AgendaVisibility
    approval_mode: ApprovalMode
    payment_mode: PaymentMode
    lawyer_selection_mode: LawyerSelectionMode = LawyerSelectionMode.NONE
    min_advance_days: int = Field(ge=0, le=MAX_ADVANCE_DAYS_LIMIT)
    max_advance_days: int = Field(ge=1, le=MAX_ADVANCE_DAYS_LIMIT)

    @model_validator(mode="after")
    def _check_coherence(self) -> "BookingConfigurationUpdate":
        # Showing the agenda only after triage requires triage to be enabled.
        if (
            self.agenda_visibility == AgendaVisibility.AFTER_TRIAGE
            and self.triage_mode == TriageMode.DISABLED
        ):
            raise ValueError(
                "Para 'mostrar agenda após triagem', a triagem não pode estar desabilitada"
            )
        if self.min_advance_days > self.max_advance_days:
            raise ValueError(
                "A antecedência mínima não pode ser maior que a máxima"
            )
        return self


class BookingConfigurationRead(ORMModel):
    id: int
    triage_mode: TriageMode
    agenda_visibility: AgendaVisibility
    approval_mode: ApprovalMode
    payment_mode: PaymentMode
    lawyer_selection_mode: LawyerSelectionMode
    min_advance_days: int
    max_advance_days: int
    questions: list[TriageQuestionRead]
