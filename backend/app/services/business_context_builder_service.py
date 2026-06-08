import uuid
import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.business_context_builder import (
    MESSAGE_ROLE_ASSISTANT,
    MESSAGE_ROLE_USER,
    SESSION_STATUS_COMPLETED,
    SESSION_STATUS_ACTIVE,
    SESSION_STATUS_CANCELLED,
    BusinessContextBuilderMessage,
    BusinessContextBuilderResult,
    BusinessContextBuilderSession,
)
from app.services.business_context_builder_ai_service import (
    BusinessContextBuilderAiService,
    BusinessContextBuilderDraftResult,
)

from app.services.business_context_builder_constants import (
    ALLOWED_STEPS,
    INTERVIEW_STEPS,
    STATIC_QUESTIONS,
    STEP_BUSINESS_DESCRIPTION,
    STEP_COMMUNICATION_STYLE,
    STEP_COMPANY_INFORMATION,
    STEP_COMPLETED,
    STEP_PRODUCTS_SERVICES,
    STEP_SALES_PROCESS,
    STEP_TARGET_CUSTOMERS,
)

ALLOWED_STATUSES = frozenset(
    {
        SESSION_STATUS_ACTIVE,
        SESSION_STATUS_COMPLETED,
        SESSION_STATUS_CANCELLED,
    }
)
TERMINAL_STATUSES = frozenset(
    {
        SESSION_STATUS_COMPLETED,
        SESSION_STATUS_CANCELLED,
    }
)
DEFAULT_CONTEXT_LIMIT = 20
MAX_CONTEXT_LIMIT = 100

logger = logging.getLogger(__name__)


class BusinessContextBuilderSessionNotFoundError(Exception):
    """Raised when no session exists for the requested id."""


class BusinessContextBuilderScopeMismatchError(Exception):
    """Raised when a session exists outside the requested tenant/business scope."""


class BusinessContextBuilderInvalidStatusError(Exception):
    """Raised when persisted session status is outside the allowed lifecycle."""


class BusinessContextBuilderInvalidStatusTransitionError(Exception):
    """Raised when a requested lifecycle transition is not allowed."""


class BusinessContextBuilderSessionClosedError(Exception):
    """Raised when a completed or cancelled session receives a write."""


class BusinessContextBuilderValidationError(Exception):
    """Raised when MVP lifecycle requirements are not satisfied."""


@dataclass(frozen=True)
class BusinessContextBuilderSessionSnapshot:
    session: BusinessContextBuilderSession
    messages: list[BusinessContextBuilderMessage]
    result: BusinessContextBuilderResult | None


class BusinessContextBuilderService:
    def __init__(
        self,
        ai_service: BusinessContextBuilderAiService | None = None,
    ) -> None:
        self._ai_service = ai_service or BusinessContextBuilderAiService()

    async def create_session(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        telegram_user_id: str | None = None,
        customer_id: uuid.UUID | None = None,
    ) -> tuple[BusinessContextBuilderSession, BusinessContextBuilderMessage]:
        now = _now()
        builder_session = BusinessContextBuilderSession(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            business_id=business_id,
            telegram_user_id=telegram_user_id,
            customer_id=customer_id,
            status=SESSION_STATUS_ACTIVE,
            current_step=STEP_COMPANY_INFORMATION,
            created_at=now,
            updated_at=now,
        )
        session.add(builder_session)
        await session.flush()

        first_message = BusinessContextBuilderMessage(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            business_id=business_id,
            session_id=builder_session.id,
            role=MESSAGE_ROLE_ASSISTANT,
            content=self.generate_static_next_question(STEP_COMPANY_INFORMATION),
            created_at=_now(),
        )
        session.add(first_message)
        await session.flush()
        return builder_session, first_message

    async def save_user_message(
        self,
        session: AsyncSession,
        *,
        session_id: uuid.UUID,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        content: str,
    ) -> tuple[
        BusinessContextBuilderSession,
        BusinessContextBuilderMessage,
        BusinessContextBuilderMessage,
    ]:
        clean_content = content.strip()
        if not clean_content:
            raise BusinessContextBuilderValidationError("content must not be empty")

        builder_session = await self._get_active_session(
            session,
            tenant_id=tenant_id,
            business_id=business_id,
            session_id=session_id,
        )

        user_message = BusinessContextBuilderMessage(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            business_id=business_id,
            session_id=builder_session.id,
            role=MESSAGE_ROLE_USER,
            content=clean_content,
            created_at=_now(),
        )
        session.add(user_message)

        next_step = _next_step(builder_session.current_step)
        _validate_step(next_step)
        builder_session.current_step = next_step
        builder_session.updated_at = _now()

        prior_messages = await self._list_messages(
            session,
            tenant_id=tenant_id,
            business_id=business_id,
            session_id=builder_session.id,
        )
        conversation_messages = [*prior_messages, user_message]
        fallback_question = self.generate_static_next_question(next_step)
        assistant_content = await self._ai_service.generate_next_question(
            session_id=builder_session.id,
            tenant_id=tenant_id,
            business_id=business_id,
            next_step=next_step,
            messages=conversation_messages,
            fallback_question=fallback_question,
        )

        assistant_message = BusinessContextBuilderMessage(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            business_id=business_id,
            session_id=builder_session.id,
            role=MESSAGE_ROLE_ASSISTANT,
            content=assistant_content,
            created_at=_now(),
        )
        session.add(assistant_message)
        await session.flush()
        return builder_session, user_message, assistant_message

    def generate_static_next_question(self, current_step: str | None) -> str:
        if current_step in STATIC_QUESTIONS:
            return STATIC_QUESTIONS[current_step]
        return (
            "Thank you. You can continue adding details or complete the draft context."
        )

    async def get_session(
        self,
        session: AsyncSession,
        *,
        session_id: uuid.UUID,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
    ) -> BusinessContextBuilderSessionSnapshot:
        builder_session = await self._get_scoped_session(
            session,
            tenant_id=tenant_id,
            business_id=business_id,
            session_id=session_id,
        )
        messages = await self._list_messages(
            session,
            tenant_id=tenant_id,
            business_id=business_id,
            session_id=session_id,
        )
        result = await self._get_result(
            session,
            tenant_id=tenant_id,
            business_id=business_id,
            session_id=session_id,
        )
        return BusinessContextBuilderSessionSnapshot(
            session=builder_session,
            messages=messages,
            result=result,
        )

    async def complete_session(
        self,
        session: AsyncSession,
        *,
        session_id: uuid.UUID,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
    ) -> tuple[BusinessContextBuilderSession, BusinessContextBuilderResult]:
        builder_session = await self._get_scoped_session(
            session,
            tenant_id=tenant_id,
            business_id=business_id,
            session_id=session_id,
        )
        self._validate_status(builder_session.status)
        if builder_session.status in TERMINAL_STATUSES:
            raise BusinessContextBuilderInvalidStatusTransitionError(
                f"cannot complete session with status {builder_session.status}"
            )
        if builder_session.status != SESSION_STATUS_ACTIVE:
            raise BusinessContextBuilderInvalidStatusTransitionError(
                f"cannot complete session with status {builder_session.status}"
            )
        existing_result = await self._get_result(
            session,
            tenant_id=tenant_id,
            business_id=business_id,
            session_id=session_id,
        )
        if existing_result is not None:
            raise BusinessContextBuilderInvalidStatusTransitionError(
                "cannot complete a session that already has a result"
            )

        messages = await self._list_messages(
            session,
            tenant_id=tenant_id,
            business_id=business_id,
            session_id=session_id,
        )
        if not any(message.role == MESSAGE_ROLE_USER for message in messages):
            raise BusinessContextBuilderValidationError(
                "at least one user message is required before completion"
            )

        now = _now()
        fallback_result = _fallback_draft_result(messages)
        try:
            draft_result = await self._ai_service.generate_draft_result(
                session_id=builder_session.id,
                tenant_id=tenant_id,
                business_id=business_id,
                current_step=builder_session.current_step,
                messages=messages,
                fallback_result=fallback_result,
            )
        except Exception as exc:
            logger.info(
                "bcb_ai_draft_result_fallback_after_error",
                extra={
                    "feature": "business_context_builder",
                    "operation": "draft_result",
                    "session_id": str(builder_session.id),
                    "tenant_id": str(tenant_id),
                    "business_id": str(business_id),
                    "fallback_used": True,
                    "error": str(exc),
                },
            )
            draft_result = fallback_result
        builder_session.status = SESSION_STATUS_COMPLETED
        builder_session.current_step = STEP_COMPLETED
        builder_session.completed_at = now
        builder_session.updated_at = now

        result = BusinessContextBuilderResult(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            business_id=business_id,
            session_id=builder_session.id,
            structured_context=draft_result.structured_context,
            generated_prompt=draft_result.generated_prompt,
            context_file_path=None,
            context_file_url=None,
            created_at=now,
            updated_at=now,
        )
        session.add(result)
        await session.flush()
        return builder_session, result

    async def list_contexts(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        limit: int = DEFAULT_CONTEXT_LIMIT,
        offset: int = 0,
    ) -> list[BusinessContextBuilderResult]:
        if limit < 1 or limit > MAX_CONTEXT_LIMIT:
            raise BusinessContextBuilderValidationError(
                f"limit must be between 1 and {MAX_CONTEXT_LIMIT}"
            )
        if offset < 0:
            raise BusinessContextBuilderValidationError(
                "offset must be greater than or equal to 0"
            )
        result = await session.execute(
            select(BusinessContextBuilderResult)
            .where(
                BusinessContextBuilderResult.tenant_id == tenant_id,
                BusinessContextBuilderResult.business_id == business_id,
            )
            .order_by(desc(BusinessContextBuilderResult.created_at))
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def _get_active_session(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        session_id: uuid.UUID,
    ) -> BusinessContextBuilderSession:
        builder_session = await self._get_scoped_session(
            session,
            tenant_id=tenant_id,
            business_id=business_id,
            session_id=session_id,
        )
        self._validate_status(builder_session.status)
        if builder_session.status in TERMINAL_STATUSES:
            raise BusinessContextBuilderSessionClosedError(
                f"cannot modify session with status {builder_session.status}"
            )
        if builder_session.status != SESSION_STATUS_ACTIVE:
            raise BusinessContextBuilderInvalidStatusTransitionError(
                f"cannot modify session with status {builder_session.status}"
            )
        return builder_session

    async def _get_scoped_session(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        session_id: uuid.UUID,
    ) -> BusinessContextBuilderSession:
        scoped_result = await session.execute(
            select(BusinessContextBuilderSession)
            .where(
                BusinessContextBuilderSession.id == session_id,
                BusinessContextBuilderSession.tenant_id == tenant_id,
                BusinessContextBuilderSession.business_id == business_id,
            )
            .limit(1)
        )
        builder_session = scoped_result.scalar_one_or_none()
        if builder_session is not None:
            self._validate_status(builder_session.status)
            _validate_step(builder_session.current_step)
            return builder_session

        unscoped_result = await session.execute(
            select(BusinessContextBuilderSession)
            .where(BusinessContextBuilderSession.id == session_id)
            .limit(1)
        )
        if unscoped_result.scalar_one_or_none() is None:
            raise BusinessContextBuilderSessionNotFoundError()
        raise BusinessContextBuilderScopeMismatchError()

    async def _list_messages(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        session_id: uuid.UUID,
    ) -> list[BusinessContextBuilderMessage]:
        result = await session.execute(
            select(BusinessContextBuilderMessage)
            .where(
                BusinessContextBuilderMessage.tenant_id == tenant_id,
                BusinessContextBuilderMessage.business_id == business_id,
                BusinessContextBuilderMessage.session_id == session_id,
            )
            .order_by(BusinessContextBuilderMessage.created_at)
        )
        return list(result.scalars().all())

    async def _list_user_messages(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        session_id: uuid.UUID,
    ) -> list[BusinessContextBuilderMessage]:
        result = await session.execute(
            select(BusinessContextBuilderMessage)
            .where(
                BusinessContextBuilderMessage.tenant_id == tenant_id,
                BusinessContextBuilderMessage.business_id == business_id,
                BusinessContextBuilderMessage.session_id == session_id,
                BusinessContextBuilderMessage.role == MESSAGE_ROLE_USER,
            )
            .order_by(BusinessContextBuilderMessage.created_at)
        )
        return list(result.scalars().all())

    async def _get_result(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        session_id: uuid.UUID,
    ) -> BusinessContextBuilderResult | None:
        result = await session.execute(
            select(BusinessContextBuilderResult)
            .where(
                BusinessContextBuilderResult.tenant_id == tenant_id,
                BusinessContextBuilderResult.business_id == business_id,
                BusinessContextBuilderResult.session_id == session_id,
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    def _validate_status(self, status: str) -> None:
        if status not in ALLOWED_STATUSES:
            raise BusinessContextBuilderInvalidStatusError(
                f"invalid session status: {status}"
            )


def _next_step(current_step: str | None) -> str:
    if current_step not in INTERVIEW_STEPS:
        return STEP_BUSINESS_DESCRIPTION
    current_index = INTERVIEW_STEPS.index(current_step)
    next_index = min(current_index + 1, len(INTERVIEW_STEPS) - 1)
    return INTERVIEW_STEPS[next_index]


def _validate_step(current_step: str | None) -> None:
    if current_step is not None and current_step not in ALLOWED_STEPS:
        raise BusinessContextBuilderValidationError(
            f"invalid session current_step: {current_step}"
        )


def _fallback_draft_result(
    messages: list[BusinessContextBuilderMessage],
) -> BusinessContextBuilderDraftResult:
    user_answers = [
        message.content.strip()
        for message in messages
        if message.role == MESSAGE_ROLE_USER and message.content.strip()
    ]
    assistant_questions = [
        message.content.strip()
        for message in messages
        if message.role == MESSAGE_ROLE_ASSISTANT and message.content.strip()
    ]
    missing_sections = [
        "company_overview",
        "business_description",
        "target_customers",
        "products_services",
        "sales_process",
        "communication_style",
        "known_constraints",
    ]
    structured_context: dict[str, object] = {
        "company_overview": "Unknown or not provided.",
        "business_description": user_answers[0] if user_answers else "Unknown or not provided.",
        "target_customers": "Unknown or not provided.",
        "products_services": "Unknown or not provided.",
        "sales_process": "Unknown or not provided.",
        "communication_style": "Unknown or not provided.",
        "known_constraints": [],
        "missing_information": missing_sections,
        "draft_quality_confidence": {
            "level": "low",
            "reason": "Fallback draft generated without AI interpretation.",
        },
        "source_summary": {
            "user_message_count": len(user_answers),
            "assistant_message_count": len(assistant_questions),
            "fallback_used": True,
        },
    }
    generated_prompt = (
        "Draft fallback business context generated from the interview transcript. "
        "Review is required before any production assistant use. "
        f"Provided user answers: {' | '.join(user_answers) if user_answers else 'none'}"
    )
    return BusinessContextBuilderDraftResult(
        structured_context=structured_context,
        generated_prompt=generated_prompt,
        fallback_used=True,
    )


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)
