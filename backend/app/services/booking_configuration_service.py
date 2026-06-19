"""Use-cases for managing a provider's booking configuration & questionnaire."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.booking_configuration import (
    DEFAULT_MAX_ADVANCE_DAYS,
    DEFAULT_MIN_ADVANCE_DAYS,
    AgendaVisibility,
    ApprovalMode,
    BookingConfiguration,
    PaymentMode,
    TriageMode,
)
from app.models.triage import TriageQuestion
from app.repositories.booking_configuration import BookingConfigurationRepository
from app.repositories.triage import TriageQuestionRepository
from app.schemas.booking_configuration import BookingConfigurationUpdate
from app.schemas.triage import TriageQuestionInput


def default_configuration(user_id: int) -> BookingConfiguration:
    """An unpersisted, Doctoralia-like default used when a provider has not
    configured anything yet (triage off, agenda immediate, auto-approval)."""
    return BookingConfiguration(
        user_id=user_id,
        triage_mode=TriageMode.DISABLED,
        agenda_visibility=AgendaVisibility.IMMEDIATE,
        approval_mode=ApprovalMode.AUTOMATIC,
        payment_mode=PaymentMode.NONE,
        min_advance_days=DEFAULT_MIN_ADVANCE_DAYS,
        max_advance_days=DEFAULT_MAX_ADVANCE_DAYS,
    )


class BookingConfigurationService:
    def __init__(
        self,
        session: AsyncSession,
        configs: BookingConfigurationRepository,
        questions: TriageQuestionRepository,
    ) -> None:
        self._session = session
        self._configs = configs
        self._questions = questions

    async def get_or_create(self, user_id: int) -> BookingConfiguration:
        config = await self._configs.get_by_user(user_id)
        if config is None:
            config = default_configuration(user_id)
            self._configs.add(config)
            await self._session.commit()
            await self._session.refresh(config)
        return config

    async def _reload_questions(self, config: BookingConfiguration) -> BookingConfiguration:
        """Refresh the ``questions`` collection after a mutation.

        A plain re-query would return the same identity-mapped instance with its
        already-loaded (now stale) collection, so we refresh the relationship
        explicitly to reflect added/removed questions in the response.
        """
        await self._session.refresh(config, attribute_names=["questions"])
        return config

    async def update(
        self, user_id: int, data: BookingConfigurationUpdate
    ) -> BookingConfiguration:
        config = await self.get_or_create(user_id)
        config.triage_mode = data.triage_mode
        config.agenda_visibility = data.agenda_visibility
        config.approval_mode = data.approval_mode
        config.payment_mode = data.payment_mode
        config.min_advance_days = data.min_advance_days
        config.max_advance_days = data.max_advance_days
        await self._session.commit()
        return await self._reload_questions(config)

    # -- Questionnaire CRUD ---------------------------------------------
    async def add_question(self, user_id: int, data: TriageQuestionInput) -> BookingConfiguration:
        config = await self.get_or_create(user_id)
        self._questions.add(
            TriageQuestion(
                configuration_id=config.id,
                text=data.text,
                qtype=data.qtype,
                options=data.options,
                order=data.order,
                required=data.required,
                is_active=data.is_active,
            )
        )
        await self._session.commit()
        return await self._reload_questions(config)

    async def update_question(
        self, user_id: int, question_id: int, data: TriageQuestionInput
    ) -> BookingConfiguration:
        config = await self.get_or_create(user_id)
        question = await self._questions.get(question_id)
        if question is None or question.configuration_id != config.id:
            raise NotFoundError("Pergunta não encontrada")
        question.text = data.text
        question.qtype = data.qtype
        question.options = data.options
        question.order = data.order
        question.required = data.required
        question.is_active = data.is_active
        await self._session.commit()
        return await self._reload_questions(config)

    async def delete_question(self, user_id: int, question_id: int) -> BookingConfiguration:
        config = await self.get_or_create(user_id)
        question = await self._questions.get(question_id)
        if question is None or question.configuration_id != config.id:
            raise NotFoundError("Pergunta não encontrada")
        await self._questions.delete(question)
        await self._session.commit()
        return await self._reload_questions(config)
