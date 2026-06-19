"""Per-provider booking configuration.

The four independent settings below combine to produce every possible booking
flow — there are no hard-coded "modes". The pipeline of steps a client goes
through is *derived* from this configuration by the flow engine
(``app.services.booking.flow``), never branched on ad hoc throughout the code.

The "provider" is a ``User`` whose role is ``lawyer`` or ``firm`` (both are
already Users at the auth root), so the configuration links straight to a user.
"""
from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.triage import TriageQuestion
    from app.models.user import User

# Janela de antecedência de agendamento (em dias a partir de hoje):
# `min_advance_days` é a antecedência mínima (ex.: não permitir marcar para hoje);
# `max_advance_days` é a máxima (quão longe no futuro um cliente pode marcar).
DEFAULT_MIN_ADVANCE_DAYS = 0
DEFAULT_MAX_ADVANCE_DAYS = 60
MAX_ADVANCE_DAYS_LIMIT = 365


class TriageMode(str, enum.Enum):
    DISABLED = "disabled"
    OPTIONAL = "optional"
    REQUIRED = "required"


class AgendaVisibility(str, enum.Enum):
    IMMEDIATE = "immediate"        # mostra a agenda de imediato
    AFTER_TRIAGE = "after_triage"  # mostra a agenda só após a triagem
    HIDDEN = "hidden"              # não mostra agenda (apenas solicitação)


class ApprovalMode(str, enum.Enum):
    AUTOMATIC = "automatic"
    MANUAL = "manual"


class PaymentMode(str, enum.Enum):
    NONE = "none"
    BEFORE_CONFIRMATION = "before_confirmation"
    AFTER_CONFIRMATION = "after_confirmation"


class LawyerSelectionMode(str, enum.Enum):
    """How the responsible lawyer is chosen on a firm's bookings.

    Only meaningful for ``firm`` providers; lawyers/clients stay ``NONE``.
    ``NONE`` keeps the legacy behaviour (booking goes to the firm, no lawyer
    routing). The other modes insert a client-facing "lawyer selection" step
    and/or require the firm to assign a responsible lawyer.
    """

    NONE = "none"                    # feature off (legacy behaviour)
    CLIENT_CHOOSES = "client_chooses"  # client picks the lawyer
    FIRM_CHOOSES = "firm_chooses"      # firm assigns the lawyer afterwards
    HYBRID = "hybrid"                  # client may pick, or defer to the firm


class BookingConfiguration(Base, TimestampMixin):
    __tablename__ = "booking_configurations"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    triage_mode: Mapped[TriageMode] = mapped_column(
        SAEnum(TriageMode), default=TriageMode.DISABLED, nullable=False
    )
    agenda_visibility: Mapped[AgendaVisibility] = mapped_column(
        SAEnum(AgendaVisibility), default=AgendaVisibility.IMMEDIATE, nullable=False
    )
    approval_mode: Mapped[ApprovalMode] = mapped_column(
        SAEnum(ApprovalMode), default=ApprovalMode.AUTOMATIC, nullable=False
    )
    payment_mode: Mapped[PaymentMode] = mapped_column(
        SAEnum(PaymentMode), default=PaymentMode.NONE, nullable=False
    )
    # Como o advogado responsável é definido (apenas relevante para escritórios).
    lawyer_selection_mode: Mapped[LawyerSelectionMode] = mapped_column(
        SAEnum(LawyerSelectionMode),
        default=LawyerSelectionMode.NONE,
        server_default=LawyerSelectionMode.NONE.value,
        nullable=False,
    )
    # Janela de antecedência: agenda aberta de min_advance_days até
    # max_advance_days dias a partir de hoje.
    min_advance_days: Mapped[int] = mapped_column(
        Integer, default=DEFAULT_MIN_ADVANCE_DAYS, server_default=str(DEFAULT_MIN_ADVANCE_DAYS), nullable=False
    )
    max_advance_days: Mapped[int] = mapped_column(
        Integer, default=DEFAULT_MAX_ADVANCE_DAYS, server_default=str(DEFAULT_MAX_ADVANCE_DAYS), nullable=False
    )

    user: Mapped["User"] = relationship()
    questions: Mapped[list["TriageQuestion"]] = relationship(
        back_populates="configuration",
        cascade="all, delete-orphan",
        order_by="TriageQuestion.order",
    )
