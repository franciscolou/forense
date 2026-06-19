"""Pipeline steps — the composable units a booking flows through.

Each step is a small, self-contained descriptor of *one* stage in the booking
pipeline. Steps carry only flow logic (who acts, which action completes them,
what status the booking holds while waiting, what happens on entry). They are
deliberately free of any database/persistence concern, so the engine that
composes them is pure and trivially unit-testable.

Adding a new stage to the product = add a ``Step`` subclass here and one line in
``flow.resolve_steps`` — no flow-specific conditionals anywhere else.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass

from app.models.booking import Booking, BookingStatus, PaymentState, StepKey

# Action names a client/provider sends to complete the corresponding step.
ACTION_SELECT_LAWYER = "select_lawyer"
ACTION_SUBMIT_TRIAGE = "submit_triage"
ACTION_SELECT_SLOT = "select_slot"
ACTION_APPROVE = "approve"
ACTION_SUBMIT_PAYMENT = "submit_payment"


class Actor(str, enum.Enum):
    CLIENT = "client"
    PROVIDER = "provider"


@dataclass(frozen=True)
class Step:
    """Base step. Subclasses customise metadata and the optional entry hook."""

    key: StepKey
    actor: Actor
    action: str
    status_while_waiting: BookingStatus
    label: str

    def on_enter(self, booking: Booking) -> None:
        """Hook invoked when a booking arrives at this step. Default: no-op."""

    def describe(self) -> dict:
        """Serializable descriptor for the API / dynamic frontend rendering."""
        return {
            "key": self.key.value,
            "actor": self.actor.value,
            "action": self.action,
            "label": self.label,
        }


@dataclass(frozen=True)
class LawyerSelectionStep(Step):
    # ``required`` is False in HYBRID mode (the client may defer to the firm).
    required: bool = True

    def describe(self) -> dict:
        return {**super().describe(), "required": self.required}


@dataclass(frozen=True)
class TriageStep(Step):
    required: bool = True

    def describe(self) -> dict:
        return {**super().describe(), "required": self.required}


@dataclass(frozen=True)
class AgendaStep(Step):
    pass


@dataclass(frozen=True)
class ApprovalStep(Step):
    pass


@dataclass(frozen=True)
class PaymentStep(Step):
    # ``after_confirmation`` payment happens once the booking is already
    # CONFIRMED (status stays CONFIRMED while payment is pending).
    after_confirmation: bool = False

    def on_enter(self, booking: Booking) -> None:
        booking.payment_state = PaymentState.PENDING

    def describe(self) -> dict:
        return {**super().describe(), "after_confirmation": self.after_confirmation}


# --- Factories with the canonical metadata for each step ----------------
def make_lawyer_step(*, required: bool) -> LawyerSelectionStep:
    return LawyerSelectionStep(
        key=StepKey.LAWYER,
        actor=Actor.CLIENT,
        action=ACTION_SELECT_LAWYER,
        status_while_waiting=BookingStatus.PENDING,
        label="Escolha do advogado",
        required=required,
    )


def make_triage_step(*, required: bool) -> TriageStep:
    return TriageStep(
        key=StepKey.TRIAGE,
        actor=Actor.CLIENT,
        action=ACTION_SUBMIT_TRIAGE,
        status_while_waiting=BookingStatus.PENDING,
        label="Triagem",
        required=required,
    )


def make_agenda_step() -> AgendaStep:
    return AgendaStep(
        key=StepKey.AGENDA,
        actor=Actor.CLIENT,
        action=ACTION_SELECT_SLOT,
        status_while_waiting=BookingStatus.PENDING,
        label="Escolha de horário",
    )


def make_approval_step() -> ApprovalStep:
    return ApprovalStep(
        key=StepKey.APPROVAL,
        actor=Actor.PROVIDER,
        action=ACTION_APPROVE,
        status_while_waiting=BookingStatus.AWAITING_APPROVAL,
        label="Aprovação",
    )


def make_payment_step(*, after_confirmation: bool) -> PaymentStep:
    return PaymentStep(
        key=StepKey.PAYMENT,
        actor=Actor.CLIENT,
        action=ACTION_SUBMIT_PAYMENT,
        # Before confirmation the client is still completing the request
        # (PENDING); after confirmation the booking is already CONFIRMED.
        status_while_waiting=(
            BookingStatus.CONFIRMED if after_confirmation else BookingStatus.PENDING
        ),
        label="Pagamento",
        after_confirmation=after_confirmation,
    )
