import uuid
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

STEP_COMPANY_INFORMATION = "company_information"
STEP_BUSINESS_DESCRIPTION = "business_description"
STEP_TARGET_CUSTOMERS = "target_customers"
STEP_PRODUCTS_SERVICES = "products_services"
STEP_SALES_PROCESS = "sales_process"
STEP_COMMUNICATION_STYLE = "communication_style"
STEP_COMPLETED = "completed"

INTERVIEW_STEPS = [
    STEP_COMPANY_INFORMATION,
    STEP_BUSINESS_DESCRIPTION,
    STEP_TARGET_CUSTOMERS,
    STEP_PRODUCTS_SERVICES,
    STEP_SALES_PROCESS,
    STEP_COMMUNICATION_STYLE,
]
ALLOWED_STEPS = frozenset([*INTERVIEW_STEPS, STEP_COMPLETED])
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

STATIC_QUESTIONS = {
    STEP_COMPANY_INFORMATION: (
        "Hello. I will help you create a draft Business Context. "
        "What is the name of your company?"
    ),
    STEP_BUSINESS_DESCRIPTION: "What does your company do?",
    STEP_TARGET_CUSTOMERS: "Who are your target customers?",
    STEP_PRODUCTS_SERVICES: "What are your main products or services?",
    STEP_SALES_PROCESS: "How does your sales or booking process work?",
    STEP_COMMUNICATION_STYLE: "What communication style should the assistant use?",
}


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
        assistant_message = BusinessContextBuilderMessage(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            business_id=business_id,
            session_id=builder_session.id,
            role=MESSAGE_ROLE_ASSISTANT,
            content=self.generate_static_next_question(next_step),
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

        user_messages = await self._list_user_messages(
            session,
            tenant_id=tenant_id,
            business_id=business_id,
            session_id=session_id,
        )
        if not user_messages:
            raise BusinessContextBuilderValidationError(
                "at least one user message is required before completion"
            )

        now = _now()
        builder_session.status = SESSION_STATUS_COMPLETED
        builder_session.current_step = STEP_COMPLETED
        builder_session.completed_at = now
        builder_session.updated_at = now

        result = BusinessContextBuilderResult(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            business_id=business_id,
            session_id=builder_session.id,
            structured_context=_placeholder_structured_context(),
            generated_prompt="Draft placeholder prompt text.",
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


def _placeholder_structured_context() -> dict[str, object]:
    return {
        "company": {
            "name": None,
            "website": None,
            "industry": None,
            "country": None,
            "languages": [],
        },
        "business_description": "",
        "assistant_goals": [],
        "services": [],
        "target_customers": {},
        "common_questions": [],
        "lead_qualification": {},
        "communication_style": {},
        "restrictions": [],
        "handoff_rules": [],
    }


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)
