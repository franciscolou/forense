"""Configuration coherence validation."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.models.booking_configuration import (
    AgendaVisibility,
    ApprovalMode,
    PaymentMode,
    TriageMode,
)
from app.schemas.booking_configuration import BookingConfigurationUpdate


def test_after_triage_requires_triage_enabled():
    with pytest.raises(ValidationError):
        BookingConfigurationUpdate(
            triage_mode=TriageMode.DISABLED,
            agenda_visibility=AgendaVisibility.AFTER_TRIAGE,
            approval_mode=ApprovalMode.AUTOMATIC,
            payment_mode=PaymentMode.NONE,
            min_advance_days=0,
            max_advance_days=60,
        )


def test_valid_combination_passes():
    cfg = BookingConfigurationUpdate(
        triage_mode=TriageMode.REQUIRED,
        agenda_visibility=AgendaVisibility.AFTER_TRIAGE,
        approval_mode=ApprovalMode.MANUAL,
        payment_mode=PaymentMode.BEFORE_CONFIRMATION,
        min_advance_days=1,
        max_advance_days=90,
    )
    assert cfg.triage_mode == TriageMode.REQUIRED
    assert cfg.min_advance_days == 1
    assert cfg.max_advance_days == 90


@pytest.mark.parametrize("days", [0, -5, 999])
def test_max_advance_days_out_of_bounds_rejected(days):
    with pytest.raises(ValidationError):
        BookingConfigurationUpdate(
            triage_mode=TriageMode.DISABLED,
            agenda_visibility=AgendaVisibility.IMMEDIATE,
            approval_mode=ApprovalMode.AUTOMATIC,
            payment_mode=PaymentMode.NONE,
            min_advance_days=0,
            max_advance_days=days,
        )


@pytest.mark.parametrize("days", [-1, 999])
def test_min_advance_days_out_of_bounds_rejected(days):
    with pytest.raises(ValidationError):
        BookingConfigurationUpdate(
            triage_mode=TriageMode.DISABLED,
            agenda_visibility=AgendaVisibility.IMMEDIATE,
            approval_mode=ApprovalMode.AUTOMATIC,
            payment_mode=PaymentMode.NONE,
            min_advance_days=days,
            max_advance_days=60,
        )


def test_min_advance_days_cannot_exceed_max():
    with pytest.raises(ValidationError):
        BookingConfigurationUpdate(
            triage_mode=TriageMode.DISABLED,
            agenda_visibility=AgendaVisibility.IMMEDIATE,
            approval_mode=ApprovalMode.AUTOMATIC,
            payment_mode=PaymentMode.NONE,
            min_advance_days=30,
            max_advance_days=10,
        )
