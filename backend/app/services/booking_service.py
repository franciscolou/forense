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
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.models.availability import AvailabilitySlot
from app.models.booking import Booking, BookingStatus, PaymentState
from app.models.booking_configuration import LawyerSelectionMode, TriageMode
from app.models.triage import TriageAnswer, TriageResponse
from app.models.user import User, UserRole
from app.repositories.availability import AvailabilityRepository
from app.repositories.booking import BookingRepository
from app.repositories.firm import FirmRepository
from app.repositories.triage import TriageQuestionRepository
from app.repositories.user import UserRepository
from app.schemas.availability import SlotRead
from app.services.availability_service import AvailabilityService
from app.schemas.booking import (
    BookingInitiate,
    BookingRead,
    ConfigSnapshot,
    LawyerOption,
    PartyRead,
    PublicFlowRead,
    StepDescriptor,
    TriageSubmit,
)
from app.schemas.triage import TriageQuestionRead, TriageResponseRead
from app.services.booking.flow import BookingFlowEngine, describe_flow
from app.services.booking.steps import (
    ACTION_APPROVE,
    ACTION_SELECT_LAWYER,
    ACTION_SELECT_SLOT,
    ACTION_SUBMIT_PAYMENT,
    ACTION_SUBMIT_TRIAGE,
    Actor,
)

# Lawyer-selection modes where the firm is responsible for picking the lawyer, so
# a responsible lawyer must be assigned before the booking can be completed.
_FIRM_ASSIGNS_MODES = {LawyerSelectionMode.FIRM_CHOOSES, LawyerSelectionMode.HYBRID}

# Closed states: no further actions (including lawyer assignment) are allowed.
_TERMINAL_STATUSES = {
    BookingStatus.REJECTED,
    BookingStatus.CANCELLED,
    BookingStatus.COMPLETED,
}
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
        firms: FirmRepository,
        config_service: BookingConfigurationService,
        engine: BookingFlowEngine,
    ) -> None:
        self._session = session
        self._bookings = bookings
        self._availability = availability
        self._availability_service = availability_service
        self._questions = questions
        self._users = users
        self._firms = firms
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
            lawyers=await self._firm_member_options(provider),
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
            lawyer_selection_mode=config.lawyer_selection_mode,
        )
        self._engine.start(booking)
        self._bookings.add(booking)
        await self._session.commit()
        return await self._read(booking.id)

    # -- Client step actions --------------------------------------------
    async def select_lawyer(
        self, client: User, booking_id: int, lawyer_user_id: int | None
    ) -> BookingRead:
        booking = await self._get_owned(booking_id, client, Actor.CLIENT)
        if lawyer_user_id is None:
            # Deferring to the firm is only allowed in HYBRID mode.
            if booking.lawyer_selection_mode != LawyerSelectionMode.HYBRID:
                raise ValidationError("É obrigatório escolher um advogado")
        else:
            members = await self._firm_member_user_ids(booking.provider_user_id)
            if lawyer_user_id not in members:
                raise ValidationError("Advogado não pertence a este escritório")
            booking.lawyer_user_id = lawyer_user_id
        self._engine.advance(booking, ACTION_SELECT_LAWYER)
        await self._session.commit()
        await self._refresh_lawyer(booking)
        return await self._read(booking.id)

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
        # Materialise the chosen derived window against whoever owns the schedule
        # (the chosen lawyer if any, otherwise the provider). The service
        # validates the time is actually available (within rules, not blocked,
        # not taken).
        slot = await self._availability_service.reserve(booking.scheduling_user_id, start_at)
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

    async def assign_lawyer(
        self, provider: User, booking_id: int, lawyer_user_id: int
    ) -> BookingRead:
        """Firm assigns the responsible lawyer. The lawyer must be a member and,
        when the booking already has a time, must be free at that time — in which
        case the slot is moved from the firm's calendar onto the lawyer's."""
        booking = await self._get_owned(booking_id, provider, Actor.PROVIDER)
        if booking.status in _TERMINAL_STATUSES:
            raise ConflictError(
                "Não é possível atribuir advogado a um agendamento encerrado"
            )
        members = await self._firm_member_user_ids(booking.provider_user_id)
        if lawyer_user_id not in members:
            raise ValidationError("Advogado não pertence a este escritório")
        if lawyer_user_id == booking.lawyer_user_id:
            return await self._read(booking.id)

        if booking.scheduled_at is not None:
            # Reserve the lawyer's slot first (raises if they're not free), then
            # release the previously-held slot so a failed assignment changes
            # nothing.
            start_at = booking.scheduled_at
            new_slot = await self._availability_service.reserve(lawyer_user_id, start_at)
            await self._release_slot(booking)
            new_slot.booking = booking
            booking.slot_id = new_slot.id
            booking.scheduled_at = new_slot.start_at
        booking.lawyer_user_id = lawyer_user_id
        await self._session.commit()
        await self._refresh_lawyer(booking)
        return await self._read(booking.id)

    async def complete(self, provider: User, booking_id: int) -> BookingRead:
        booking = await self._get_owned(booking_id, provider, Actor.PROVIDER)
        # When the firm is responsible for choosing the lawyer, one must be
        # assigned before the appointment can be marked done.
        if (
            booking.lawyer_selection_mode in _FIRM_ASSIGNS_MODES
            and booking.lawyer_user_id is None
        ):
            raise ValidationError("Atribua um advogado responsável antes de concluir")
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

    async def list_my_lawyers(self, provider: User) -> list[LawyerOption]:
        """Member lawyers a firm can assign to a booking (empty for non-firms)."""
        return await self._firm_member_options(provider)

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

    async def _refresh_lawyer(self, booking: Booking) -> None:
        """Reload the ``lawyer`` relationship after changing ``lawyer_user_id``.

        With ``expire_on_commit=False`` the already-loaded (now stale) relationship
        would otherwise survive the re-query — same identity-map caveat as the
        questionnaire reload in ``BookingConfigurationService``."""
        await self._session.refresh(booking, attribute_names=["lawyer"])

    async def _firm_member_user_ids(self, firm_user_id: int) -> set[int]:
        firm = await self._firms.get_by_user_id(firm_user_id)
        if firm is None:
            return set()
        return {lawyer.user_id for lawyer in firm.lawyers}

    async def _firm_member_options(self, provider: User) -> list[LawyerOption]:
        """The firm's member lawyers as selectable options; empty for non-firms."""
        if provider.role != UserRole.FIRM:
            return []
        firm = await self._firms.get_by_user_id(provider.id)
        if firm is None:
            return []
        return [
            LawyerOption(
                user_id=lawyer.user_id,
                full_name=lawyer.user.full_name,
                photo_url=lawyer.photo_url,
            )
            for lawyer in firm.lawyers
        ]

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
    def _client_party(client: User) -> PartyRead:
        """Build the client party with contact details from their profile, so the
        provider can see who booked."""
        profile = client.client  # eager-loaded; None for non-client users
        return PartyRead(
            id=client.id,
            full_name=client.full_name,
            email=client.email,
            phone=profile.phone if profile else None,
            city=profile.city if profile else None,
            state=profile.state if profile else None,
        )

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
            provider=PartyRead(
                id=booking.provider.id,
                full_name=booking.provider.full_name,
                email=booking.provider.email,
            ),
            client=self._client_party(booking.client),
            lawyer=(
                PartyRead(
                    id=booking.lawyer.id,
                    full_name=booking.lawyer.full_name,
                    email=booking.lawyer.email,
                )
                if booking.lawyer
                else None
            ),
            lawyer_user_id=booking.lawyer_user_id,
            scheduling_user_id=booking.scheduling_user_id,
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
