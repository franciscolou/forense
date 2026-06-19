"""Booking use-cases — the client-facing flow plus provider actions.

Each public method is a thin orchestration: it authorises the caller, performs
its specific persistence side effect, then asks the :class:`BookingFlowEngine`
to validate and progress the state machine. The engine owns *all* flow logic;
this service owns persistence and authorization. There is intentionally no
per-flow branching here.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    AuthorizationError,
    NotFoundError,
    ValidationError,
)
from app.models.availability import AvailabilitySlot
from app.models.booking import Booking, BookingStatus, PaymentState
from app.models.booking_configuration import TriageMode
from app.models.triage import TriageAnswer, TriageResponse
from app.models.user import User, UserRole
from app.repositories.availability import AvailabilityRepository
from app.repositories.booking import BookingRepository
from app.repositories.triage import TriageQuestionRepository
from app.repositories.user import UserRepository
from app.schemas.availability import SlotRead
from app.services.availability_service import AvailabilityService
from app.schemas.booking import (
    BookingInitiate,
    BookingRead,
    ConfigSnapshot,
    PartyRead,
    PublicFlowRead,
    StepDescriptor,
    TriageSubmit,
)
from app.schemas.triage import TriageQuestionRead, TriageResponseRead
from app.services.booking.flow import BookingFlowEngine, describe_flow
from app.services.booking.steps import (
    ACTION_APPROVE,
    ACTION_SELECT_SLOT,
    ACTION_SUBMIT_PAYMENT,
    ACTION_SUBMIT_TRIAGE,
    Actor,
)
from app.services.booking_configuration_service import BookingConfigurationService

_PROVIDER_ROLES = {UserRole.LAWYER, UserRole.FIRM}


class BookingService:
    def __init__(
        self,
        session: AsyncSession,
        bookings: BookingRepository,
        availability: AvailabilityRepository,
        availability_service: AvailabilityService,
        questions: TriageQuestionRepository,
        users: UserRepository,
        config_service: BookingConfigurationService,
        engine: BookingFlowEngine,
    ) -> None:
        self._session = session
        self._bookings = bookings
        self._availability = availability
        self._availability_service = availability_service
        self._questions = questions
        self._users = users
        self._configs = config_service
        self._engine = engine

    # -- Public flow (client view) --------------------------------------
    async def get_public_flow(self, provider_user_id: int) -> PublicFlowRead:
        provider = await self._require_provider_user(provider_user_id)
        config = await self._configs.get_or_create(provider_user_id)
        steps = describe_flow(config)
        active_questions = [q for q in config.questions if q.is_active]
        return PublicFlowRead(
            provider_user_id=provider.id,
            provider_name=provider.full_name,
            config=ConfigSnapshot.model_validate(config, from_attributes=True),
            steps=[StepDescriptor(**s) for s in steps],
            questions=[TriageQuestionRead.model_validate(q) for q in active_questions],
        )

    # -- Initiation ------------------------------------------------------
    async def initiate(self, client: User, data: BookingInitiate) -> BookingRead:
        if client.role != UserRole.CLIENT:
            raise AuthorizationError("Apenas clientes podem solicitar atendimento")
        if data.provider_user_id == client.id:
            raise ValidationError("Não é possível agendar consigo mesmo")
        await self._require_provider_user(data.provider_user_id)
        config = await self._configs.get_or_create(data.provider_user_id)

        booking = Booking(
            provider_user_id=data.provider_user_id,
            client_user_id=client.id,
            notes=data.notes,
            # Snapshot the configuration so later config changes don't affect
            # this in-flight booking.
            triage_mode=config.triage_mode,
            agenda_visibility=config.agenda_visibility,
            approval_mode=config.approval_mode,
            payment_mode=config.payment_mode,
        )
        self._engine.start(booking)
        self._bookings.add(booking)
        await self._session.commit()
        return await self._read(booking.id)

    # -- Client step actions --------------------------------------------
    async def submit_triage(self, client: User, booking_id: int, data: TriageSubmit) -> BookingRead:
        booking = await self._get_owned(booking_id, client, Actor.CLIENT)
        active = [q for q in (await self._provider_questions(booking)) if q.is_active]
        by_id = {q.id: q for q in active}

        answered: set[int] = set()
        for ans in data.answers:
            question = by_id.get(ans.question_id)
            if question is None:
                continue  # ignore answers to unknown/inactive questions
            if self._is_blank(ans.value):
                continue
            answered.add(question.id)

        # Required-question enforcement applies only when triage is mandatory.
        # When triage is OPTIONAL the whole step may be skipped (empty/partial).
        if booking.triage_mode == TriageMode.REQUIRED:
            missing = [q for q in active if q.required and q.id not in answered]
            if missing:
                raise ValidationError(
                    "Responda as perguntas obrigatórias: "
                    + ", ".join(q.text for q in missing)
                )

        response = TriageResponse(
            booking_id=booking.id,
            answers=[
                TriageAnswer(
                    question_id=ans.question_id,
                    value=ans.value,
                    question_text=by_id[ans.question_id].text,
                )
                for ans in data.answers
                if ans.question_id in by_id and not self._is_blank(ans.value)
            ],
        )
        booking.triage_response = response
        self._engine.advance(booking, ACTION_SUBMIT_TRIAGE)
        await self._session.commit()
        return await self._read(booking.id)

    async def select_slot(
        self, client: User, booking_id: int, start_at: datetime
    ) -> BookingRead:
        booking = await self._get_owned(booking_id, client, Actor.CLIENT)
        # Materialise the chosen derived window; the service validates that the
        # time is actually available (within rules, not blocked, not taken).
        slot = await self._availability_service.reserve(booking.provider_user_id, start_at)
        slot.booking = booking
        booking.slot_id = slot.id
        booking.scheduled_at = slot.start_at
        self._engine.advance(booking, ACTION_SELECT_SLOT)
        await self._session.commit()
        return await self._read(booking.id)

    async def submit_payment(self, client: User, booking_id: int) -> BookingRead:
        booking = await self._get_owned(booking_id, client, Actor.CLIENT)
        booking.payment_state = PaymentState.PAID
        self._engine.advance(booking, ACTION_SUBMIT_PAYMENT)
        await self._session.commit()
        return await self._read(booking.id)

    # -- Provider actions -----------------------------------------------
    async def approve(self, provider: User, booking_id: int) -> BookingRead:
        booking = await self._get_owned(booking_id, provider, Actor.PROVIDER)
        self._engine.advance(booking, ACTION_APPROVE)
        await self._session.commit()
        return await self._read(booking.id)

    async def reject(self, provider: User, booking_id: int, reason: str | None) -> BookingRead:
        booking = await self._get_owned(booking_id, provider, Actor.PROVIDER)
        self._engine.transition(booking, "reject", by=Actor.PROVIDER)
        booking.resolution_reason = reason
        await self._release_slot(booking)
        await self._session.commit()
        return await self._read(booking.id)

    async def complete(self, provider: User, booking_id: int) -> BookingRead:
        booking = await self._get_owned(booking_id, provider, Actor.PROVIDER)
        self._engine.transition(booking, "complete", by=Actor.PROVIDER)
        await self._session.commit()
        return await self._read(booking.id)

    # -- Either party ----------------------------------------------------
    async def cancel(self, user: User, booking_id: int, reason: str | None) -> BookingRead:
        booking = await self._bookings.get_with_relations(booking_id)
        if booking is None:
            raise NotFoundError("Agendamento não encontrado")
        actor = self._actor_for(booking, user)
        self._engine.transition(booking, "cancel", by=actor)
        booking.resolution_reason = reason
        await self._release_slot(booking)
        await self._session.commit()
        return await self._read(booking.id)

    async def list_my_bookings(self, user: User) -> list[BookingRead]:
        if user.role == UserRole.CLIENT:
            bookings = await self._bookings.list_for_client(user.id)
        else:
            bookings = await self._bookings.list_for_provider(user.id)
        return [self._serialize(b) for b in bookings]

    async def get_booking(self, user: User, booking_id: int) -> BookingRead:
        booking = await self._bookings.get_with_relations(booking_id)
        if booking is None:
            raise NotFoundError("Agendamento não encontrado")
        self._actor_for(booking, user)  # authorises (raises if neither party)
        return self._serialize(booking)

    # -- Helpers ---------------------------------------------------------
    async def _require_provider_user(self, user_id: int) -> User:
        user = await self._users.get(user_id)
        if user is None or user.role not in _PROVIDER_ROLES:
            raise NotFoundError("Profissional/escritório não encontrado")
        return user

    async def _provider_questions(self, booking: Booking):
        config = await self._configs.get_or_create(booking.provider_user_id)
        return config.questions

    async def _get_owned(self, booking_id: int, user: User, expected: Actor) -> Booking:
        booking = await self._bookings.get_with_relations(booking_id)
        if booking is None:
            raise NotFoundError("Agendamento não encontrado")
        actor = self._actor_for(booking, user)
        if actor != expected:
            raise AuthorizationError("Ação não permitida para este usuário")
        return booking

    def _actor_for(self, booking: Booking, user: User) -> Actor:
        if user.id == booking.client_user_id:
            return Actor.CLIENT
        if user.id == booking.provider_user_id:
            return Actor.PROVIDER
        raise AuthorizationError("Você não participa deste agendamento")

    async def _release_slot(self, booking: Booking) -> None:
        """Free a reserved slot. Since open availability is derived from the
        recurring rules, dropping the materialised slot row automatically
        reopens that time."""
        if booking.slot_id is None:
            return
        slot = await self._availability.get(booking.slot_id)
        booking.slot_id = None
        booking.scheduled_at = None
        if slot is not None:
            slot.booking = None
            await self._availability.delete(slot)

    @staticmethod
    def _is_blank(value) -> bool:
        return value is None or value == "" or value == []

    async def _read(self, booking_id: int) -> BookingRead:
        booking = await self._bookings.get_with_relations(booking_id)
        assert booking is not None
        return self._serialize(booking)

    def _serialize(self, booking: Booking) -> BookingRead:
        step = self._engine.current_step(booking)
        pending = StepDescriptor(**step.describe()) if step else None
        return BookingRead(
            id=booking.id,
            status=booking.status,
            current_step=booking.current_step,
            pending_action=pending,
            config=ConfigSnapshot.model_validate(booking, from_attributes=True),
            provider=PartyRead(id=booking.provider.id, full_name=booking.provider.full_name),
            client=PartyRead(id=booking.client.id, full_name=booking.client.full_name),
            slot=SlotRead.model_validate(booking.slot) if booking.slot else None,
            scheduled_at=booking.scheduled_at,
            payment_state=booking.payment_state,
            notes=booking.notes,
            resolution_reason=booking.resolution_reason,
            triage_response=(
                TriageResponseRead.model_validate(booking.triage_response)
                if booking.triage_response
                else None
            ),
            created_at=booking.created_at,
        )
