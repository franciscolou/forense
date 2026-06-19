"""Unit tests for the booking flow engine.

These are pure (no DB): they validate that combining the four independent
settings produces the documented flows and the correct state transitions —
exactly the property the architecture promises.
"""
from __future__ import annotations

import pytest

from app.core.exceptions import ConflictError
from app.models.booking import Booking, BookingStatus, PaymentState, StepKey
from app.models.booking_configuration import (
    AgendaVisibility,
    ApprovalMode,
    PaymentMode,
    TriageMode,
)
from app.services.booking.flow import BookingFlowEngine, describe_flow, resolve_steps
from app.services.booking.steps import Actor


def make_booking(triage, agenda, approval, payment) -> Booking:
    return Booking(
        provider_user_id=1,
        client_user_id=2,
        triage_mode=triage,
        agenda_visibility=agenda,
        approval_mode=approval,
        payment_mode=payment,
    )


def keys(booking: Booking) -> list[str]:
    return [s.key.value for s in resolve_steps(booking)]


@pytest.fixture
def engine() -> BookingFlowEngine:
    return BookingFlowEngine()


# --- The four documented scenarios --------------------------------------
def test_doctoralia_like(engine):
    b = make_booking(
        TriageMode.DISABLED, AgendaVisibility.IMMEDIATE, ApprovalMode.AUTOMATIC, PaymentMode.NONE
    )
    assert keys(b) == ["agenda"]
    engine.start(b)
    assert b.status == BookingStatus.PENDING and b.current_step == StepKey.AGENDA
    engine.advance(b, "select_slot")
    assert b.status == BookingStatus.CONFIRMED and b.current_step is None


def test_triage_then_agenda_auto(engine):
    b = make_booking(
        TriageMode.REQUIRED, AgendaVisibility.AFTER_TRIAGE, ApprovalMode.AUTOMATIC, PaymentMode.NONE
    )
    assert keys(b) == ["triage", "agenda"]
    engine.start(b)
    assert b.current_step == StepKey.TRIAGE
    engine.advance(b, "submit_triage")
    assert b.current_step == StepKey.AGENDA and b.status == BookingStatus.PENDING
    engine.advance(b, "select_slot")
    assert b.status == BookingStatus.CONFIRMED


def test_triage_then_agenda_manual(engine):
    b = make_booking(
        TriageMode.REQUIRED, AgendaVisibility.AFTER_TRIAGE, ApprovalMode.MANUAL, PaymentMode.NONE
    )
    assert keys(b) == ["triage", "agenda", "approval"]
    engine.start(b)
    engine.advance(b, "submit_triage")
    engine.advance(b, "select_slot")
    assert b.status == BookingStatus.AWAITING_APPROVAL and b.current_step == StepKey.APPROVAL
    engine.advance(b, "approve")
    assert b.status == BookingStatus.CONFIRMED and b.current_step is None


def test_request_without_public_agenda(engine):
    b = make_booking(
        TriageMode.OPTIONAL, AgendaVisibility.HIDDEN, ApprovalMode.MANUAL, PaymentMode.NONE
    )
    assert keys(b) == ["triage", "approval"]
    engine.start(b)
    engine.advance(b, "submit_triage")
    assert b.status == BookingStatus.AWAITING_APPROVAL
    engine.advance(b, "approve")
    assert b.status == BookingStatus.CONFIRMED


# --- Payment placement --------------------------------------------------
def test_payment_before_confirmation(engine):
    b = make_booking(
        TriageMode.DISABLED, AgendaVisibility.IMMEDIATE, ApprovalMode.MANUAL,
        PaymentMode.BEFORE_CONFIRMATION,
    )
    assert keys(b) == ["agenda", "approval", "payment"]
    engine.start(b)
    engine.advance(b, "select_slot")
    engine.advance(b, "approve")
    assert b.current_step == StepKey.PAYMENT and b.status == BookingStatus.PENDING
    assert b.payment_state == PaymentState.PENDING
    engine.advance(b, "submit_payment")
    assert b.status == BookingStatus.CONFIRMED


def test_payment_after_confirmation_keeps_confirmed(engine):
    b = make_booking(
        TriageMode.DISABLED, AgendaVisibility.IMMEDIATE, ApprovalMode.AUTOMATIC,
        PaymentMode.AFTER_CONFIRMATION,
    )
    assert keys(b) == ["agenda", "payment"]
    engine.start(b)
    engine.advance(b, "select_slot")
    # Booking is confirmed but still waiting on payment.
    assert b.status == BookingStatus.CONFIRMED and b.current_step == StepKey.PAYMENT
    assert b.payment_state == PaymentState.PENDING
    engine.advance(b, "submit_payment")
    assert b.status == BookingStatus.CONFIRMED and b.current_step is None


# --- Guards / descriptors ----------------------------------------------
def test_wrong_action_is_rejected(engine):
    b = make_booking(
        TriageMode.REQUIRED, AgendaVisibility.AFTER_TRIAGE, ApprovalMode.AUTOMATIC, PaymentMode.NONE
    )
    engine.start(b)  # at triage
    with pytest.raises(ConflictError):
        engine.advance(b, "select_slot")


def test_no_steps_auto_confirms(engine):
    b = make_booking(
        TriageMode.DISABLED, AgendaVisibility.HIDDEN, ApprovalMode.AUTOMATIC, PaymentMode.NONE
    )
    assert keys(b) == []
    engine.start(b)
    assert b.status == BookingStatus.CONFIRMED


def test_describe_flow_exposes_actor_and_required(engine):
    b = make_booking(
        TriageMode.OPTIONAL, AgendaVisibility.IMMEDIATE, ApprovalMode.MANUAL, PaymentMode.NONE
    )
    desc = describe_flow(b)
    triage = next(d for d in desc if d["key"] == "triage")
    approval = next(d for d in desc if d["key"] == "approval")
    assert triage["actor"] == "client" and triage["required"] is False
    assert approval["actor"] == "provider"


# --- Lifecycle table ----------------------------------------------------
def test_reject_only_from_pending_or_awaiting(engine):
    b = make_booking(
        TriageMode.DISABLED, AgendaVisibility.HIDDEN, ApprovalMode.MANUAL, PaymentMode.NONE
    )
    engine.start(b)
    assert b.status == BookingStatus.AWAITING_APPROVAL
    engine.transition(b, "reject", by=Actor.PROVIDER)
    assert b.status == BookingStatus.REJECTED


def test_cannot_complete_unconfirmed(engine):
    b = make_booking(
        TriageMode.REQUIRED, AgendaVisibility.AFTER_TRIAGE, ApprovalMode.MANUAL, PaymentMode.NONE
    )
    engine.start(b)  # at triage, PENDING
    with pytest.raises(ConflictError):
        engine.transition(b, "complete", by=Actor.PROVIDER)


def test_complete_from_confirmed(engine):
    b = make_booking(
        TriageMode.DISABLED, AgendaVisibility.IMMEDIATE, ApprovalMode.AUTOMATIC, PaymentMode.NONE
    )
    engine.start(b)
    engine.advance(b, "select_slot")
    assert b.status == BookingStatus.CONFIRMED
    engine.transition(b, "complete", by=Actor.PROVIDER)
    assert b.status == BookingStatus.COMPLETED


def test_cancel_by_either_party(engine):
    b = make_booking(
        TriageMode.DISABLED, AgendaVisibility.IMMEDIATE, ApprovalMode.AUTOMATIC, PaymentMode.NONE
    )
    engine.start(b)
    engine.transition(b, "cancel", by=Actor.CLIENT)
    assert b.status == BookingStatus.CANCELLED


def test_reject_requires_provider_actor(engine):
    b = make_booking(
        TriageMode.DISABLED, AgendaVisibility.HIDDEN, ApprovalMode.MANUAL, PaymentMode.NONE
    )
    engine.start(b)
    with pytest.raises(ConflictError):
        engine.transition(b, "reject", by=Actor.CLIENT)
