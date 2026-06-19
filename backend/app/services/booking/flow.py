"""The booking flow engine.

This is the single place that knows how settings compose into a flow:

  * ``resolve_steps`` — the *only* source of the pipeline's composition & order.
  * ``advance`` — the *only* state-progression function.
  * ``LIFECYCLE`` — the *only* table of out-of-pipeline transitions
    (cancel / reject / complete).

Because the pipeline is derived from configuration, there are no flow-specific
``if mode == ...`` chains scattered across the codebase. The engine is pure (it
mutates the in-memory ``Booking`` only); persistence is the service's job.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.core.exceptions import ConflictError
from app.models.booking import Booking, BookingStatus, PaymentState, StepKey
from app.models.booking_configuration import (
    AgendaVisibility,
    ApprovalMode,
    LawyerSelectionMode,
    PaymentMode,
    TriageMode,
)
from app.services.booking.steps import (
    Actor,
    Step,
    make_agenda_step,
    make_approval_step,
    make_lawyer_step,
    make_payment_step,
    make_triage_step,
)


class BookingConfigLike(Protocol):
    """Anything exposing the four settings — both ``BookingConfiguration`` and a
    ``Booking`` (which snapshots them) satisfy this."""

    triage_mode: TriageMode
    agenda_visibility: AgendaVisibility
    approval_mode: ApprovalMode
    payment_mode: PaymentMode
    lawyer_selection_mode: LawyerSelectionMode


# Lawyer-selection modes that put a client-facing choice step in the pipeline.
_LAWYER_STEP_MODES = {LawyerSelectionMode.CLIENT_CHOOSES, LawyerSelectionMode.HYBRID}


def resolve_steps(config: BookingConfigLike) -> list[Step]:
    """Derive the ordered pipeline from a configuration snapshot.

    Canonical order:
        LAWYER → TRIAGE → AGENDA → APPROVAL → PAYMENT(before)
        → [CONFIRMED] → PAYMENT(after)
    """
    steps: list[Step] = []
    if config.lawyer_selection_mode in _LAWYER_STEP_MODES:
        steps.append(
            make_lawyer_step(
                required=config.lawyer_selection_mode == LawyerSelectionMode.CLIENT_CHOOSES
            )
        )
    if config.triage_mode != TriageMode.DISABLED:
        steps.append(make_triage_step(required=config.triage_mode == TriageMode.REQUIRED))
    if config.agenda_visibility != AgendaVisibility.HIDDEN:
        steps.append(make_agenda_step())
    if config.approval_mode == ApprovalMode.MANUAL:
        steps.append(make_approval_step())
    if config.payment_mode == PaymentMode.BEFORE_CONFIRMATION:
        steps.append(make_payment_step(after_confirmation=False))
    if config.payment_mode == PaymentMode.AFTER_CONFIRMATION:
        steps.append(make_payment_step(after_confirmation=True))
    return steps


def describe_flow(config: BookingConfigLike) -> list[dict]:
    """Serializable step descriptors so the client UI can render the flow
    dynamically, with no flow logic of its own."""
    return [step.describe() for step in resolve_steps(config)]


@dataclass(frozen=True)
class LifecycleTransition:
    allowed_from: frozenset[BookingStatus]
    to: BookingStatus
    actor: Actor | None  # None = either party may trigger it


# Out-of-pipeline transitions, centralised. Actor is advisory; the service
# enforces who is allowed to call each one.
LIFECYCLE: dict[str, LifecycleTransition] = {
    "reject": LifecycleTransition(
        frozenset({BookingStatus.PENDING, BookingStatus.AWAITING_APPROVAL}),
        BookingStatus.REJECTED,
        Actor.PROVIDER,
    ),
    "cancel": LifecycleTransition(
        frozenset(
            {BookingStatus.PENDING, BookingStatus.AWAITING_APPROVAL, BookingStatus.CONFIRMED}
        ),
        BookingStatus.CANCELLED,
        None,
    ),
    "complete": LifecycleTransition(
        frozenset({BookingStatus.CONFIRMED}),
        BookingStatus.COMPLETED,
        Actor.PROVIDER,
    ),
}


class BookingFlowEngine:
    """Drives a booking through its derived pipeline and lifecycle."""

    def resolve_steps(self, config: BookingConfigLike) -> list[Step]:
        return resolve_steps(config)

    def current_step(self, booking: Booking) -> Step | None:
        if booking.current_step is None:
            return None
        for step in self.resolve_steps(booking):
            if step.key == booking.current_step:
                return step
        return None

    def start(self, booking: Booking) -> None:
        """Place a freshly created booking at its first pending step (or confirm
        immediately if the configuration yields no steps)."""
        steps = self.resolve_steps(booking)
        booking.payment_state = PaymentState.NOT_REQUIRED
        if not steps:
            self._finish(booking)
        else:
            self._enter(booking, steps[0])

    def advance(self, booking: Booking, action: str) -> None:
        """Complete the current step (validating ``action``) and move on."""
        steps = self.resolve_steps(booking)
        idx = self._current_index(steps, booking)
        current = steps[idx]
        if action != current.action:
            raise ConflictError(
                f"Ação '{action}' não é válida na etapa atual ('{current.action}')"
            )
        next_idx = idx + 1
        if next_idx < len(steps):
            self._enter(booking, steps[next_idx])
        else:
            self._finish(booking)

    def transition(self, booking: Booking, kind: str, *, by: Actor) -> None:
        """Apply a lifecycle transition (cancel / reject / complete)."""
        t = LIFECYCLE[kind]
        if t.actor is not None and t.actor != by:
            raise ConflictError(f"'{kind}' só pode ser feito por {t.actor.value}")
        if booking.status not in t.allowed_from:
            raise ConflictError(
                f"Não é possível '{kind}' um agendamento com status '{booking.status.value}'"
            )
        booking.status = t.to
        booking.current_step = None

    # -- internals -------------------------------------------------------
    def _enter(self, booking: Booking, step: Step) -> None:
        booking.current_step = step.key
        booking.status = step.status_while_waiting
        step.on_enter(booking)

    def _finish(self, booking: Booking) -> None:
        booking.current_step = None
        booking.status = BookingStatus.CONFIRMED

    def _current_index(self, steps: list[Step], booking: Booking) -> int:
        for i, step in enumerate(steps):
            if step.key == booking.current_step:
                return i
        raise ConflictError("O agendamento não está em uma etapa que aceite esta ação")
