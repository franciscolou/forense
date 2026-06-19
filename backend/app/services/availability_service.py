"""Availability use-cases.

The provider declares *recurring weekly rules* plus *exception blocks*; concrete
bookable slots are **derived** from those (rules − exceptions − already-booked),
at one-hour granularity, for a rolling horizon. A slot row is only persisted when
a client actually reserves one. This keeps provider input cheap (paint a weekly
grid once) while the booking engine still consumes discrete slots.

Wall-clock convention: rule hours are interpreted in **UTC**. The frontend
formats slot times in UTC too, so a window painted at 09:00 is shown to the
client as 09:00 — internally consistent without per-user timezone handling.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.availability import (
    AvailabilityException,
    AvailabilityRule,
    AvailabilitySlot,
)
from app.models.booking_configuration import (
    DEFAULT_MAX_ADVANCE_DAYS,
    DEFAULT_MIN_ADVANCE_DAYS,
)
from app.repositories.availability import (
    AvailabilityExceptionRepository,
    AvailabilityRepository,
    AvailabilityRuleRepository,
)
from app.repositories.booking_configuration import BookingConfigurationRepository
from app.schemas.availability import ExceptionInput, RuleInput

SLOT_HOURS = 1


@dataclass(frozen=True)
class OpenSlot:
    start_at: datetime
    end_at: datetime


def _as_utc(dt: datetime) -> datetime:
    """Normalise to aware UTC. SQLite returns naive datetimes for stored values,
    so treat naive as UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class AvailabilityService:
    def __init__(
        self,
        session: AsyncSession,
        rules: AvailabilityRuleRepository,
        exceptions: AvailabilityExceptionRepository,
        slots: AvailabilityRepository,
        configs: BookingConfigurationRepository,
    ) -> None:
        self._session = session
        self._rules = rules
        self._exceptions = exceptions
        self._slots = slots
        self._configs = configs

    # -- Schedule (provider) --------------------------------------------
    async def get_schedule(
        self, provider_user_id: int
    ) -> tuple[list[AvailabilityRule], list[AvailabilityException]]:
        rules = await self._rules.list_for_provider(provider_user_id)
        exceptions = await self._exceptions.list_for_provider(
            provider_user_id, upcoming_only=True
        )
        return rules, exceptions

    async def replace_rules(
        self, provider_user_id: int, inputs: list[RuleInput]
    ) -> list[AvailabilityRule]:
        """Replace the entire weekly grid (declarative paint-then-save)."""
        await self._rules.delete_for_provider(provider_user_id)
        for r in inputs:
            self._rules.add(
                AvailabilityRule(
                    provider_user_id=provider_user_id,
                    weekday=r.weekday,
                    start_hour=r.start_hour,
                    end_hour=r.end_hour,
                )
            )
        await self._session.commit()
        return await self._rules.list_for_provider(provider_user_id)

    async def add_exception(
        self, provider_user_id: int, data: ExceptionInput
    ) -> AvailabilityException:
        exception = AvailabilityException(
            provider_user_id=provider_user_id,
            start_at=data.start_at,
            end_at=data.end_at,
            note=data.note,
        )
        self._exceptions.add(exception)
        await self._session.commit()
        await self._session.refresh(exception)
        return exception

    async def delete_exception(self, provider_user_id: int, exception_id: int) -> None:
        exception = await self._exceptions.get(exception_id)
        if exception is None or exception.provider_user_id != provider_user_id:
            raise NotFoundError("Indisponibilidade não encontrada")
        await self._exceptions.delete(exception)
        await self._session.commit()

    async def _advance_window(self, provider_user_id: int) -> tuple[int, int]:
        """Return the provider's (min, max) advance-booking window, in days."""
        config = await self._configs.get_by_user(provider_user_id)
        if config is None:
            return DEFAULT_MIN_ADVANCE_DAYS, DEFAULT_MAX_ADVANCE_DAYS
        return config.min_advance_days, config.max_advance_days

    # -- Derived open slots (public) ------------------------------------
    async def open_slots(
        self, provider_user_id: int, horizon_days: int | None = None
    ) -> list[OpenSlot]:
        """Derive bookable windows within the provider's advance-booking window.

        Slots earlier than the configured ``min_advance_days`` (lead time) are
        excluded, and the horizon defaults to ``max_advance_days`` (how far ahead
        a client may book); callers may override the horizon explicitly.
        """
        min_days, max_days = await self._advance_window(provider_user_id)
        if horizon_days is None:
            horizon_days = max_days
        rules = await self._rules.list_for_provider(provider_user_id)
        if not rules:
            return []
        now = datetime.now(timezone.utc)
        # Earliest bookable instant: respect the minimum lead time.
        earliest = now + timedelta(days=min_days)
        exceptions = [
            (_as_utc(e.start_at), _as_utc(e.end_at))
            for e in await self._exceptions.list_for_provider(provider_user_id)
        ]
        booked = {_as_utc(s) for s in await self._slots.booked_starts(provider_user_id, now)}

        rules_by_weekday: dict[int, list[AvailabilityRule]] = {}
        for rule in rules:
            rules_by_weekday.setdefault(rule.weekday, []).append(rule)

        starts: set[datetime] = set()
        today = now.date()
        for offset in range(horizon_days + 1):
            day = today + timedelta(days=offset)
            for rule in rules_by_weekday.get(day.weekday(), []):
                for hour in range(rule.start_hour, rule.end_hour):
                    start = datetime(
                        day.year, day.month, day.day, hour, tzinfo=timezone.utc
                    )
                    end = start + timedelta(hours=SLOT_HOURS)
                    if start < earliest or start in booked:
                        continue
                    if any(ex_start < end and start < ex_end for ex_start, ex_end in exceptions):
                        continue
                    starts.add(start)

        return [OpenSlot(s, s + timedelta(hours=SLOT_HOURS)) for s in sorted(starts)]

    async def reserve(self, provider_user_id: int, start_at: datetime) -> AvailabilitySlot:
        """Validate that ``start_at`` is a currently-open derived slot and
        materialise it as a booked :class:`AvailabilitySlot`."""
        start = _as_utc(start_at)
        open_starts = {s.start_at for s in await self.open_slots(provider_user_id)}
        if start not in open_starts:
            raise ConflictError("Horário indisponível")
        slot = AvailabilitySlot(
            provider_user_id=provider_user_id,
            start_at=start,
            end_at=start + timedelta(hours=SLOT_HOURS),
            is_booked=True,
        )
        self._slots.add(slot)
        await self._session.flush()
        return slot
