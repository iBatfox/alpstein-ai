"""Durable per-inbound-turn processing traces (E2.4)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message_trace import (
    TRACE_STATUS_ACCEPTED,
    TRACE_STATUS_COMPLETED,
    TRACE_STATUS_FAILED,
    TRACE_STATUS_PROCESSING,
    TRACE_STATUS_SKIPPED_DUPLICATE,
    MessageTrace,
)

ERROR_MESSAGE_MAX_LENGTH = 500
TRACE_LIST_DEFAULT_LIMIT = 20
TRACE_LIST_MAX_LIMIT = 100


class MessageTraceService:
    async def get_trace_by_id(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        trace_id: uuid.UUID,
    ) -> MessageTrace | None:
        result = await session.execute(
            select(MessageTrace).where(
                MessageTrace.id == trace_id,
                MessageTrace.tenant_id == tenant_id,
                MessageTrace.business_id == business_id,
            )
        )
        return result.scalar_one_or_none()

    async def find_by_inbound_message_id(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        inbound_message_id: uuid.UUID,
    ) -> MessageTrace | None:
        result = await session.execute(
            select(MessageTrace).where(
                MessageTrace.tenant_id == tenant_id,
                MessageTrace.business_id == business_id,
                MessageTrace.inbound_message_id == inbound_message_id,
            )
        )
        return result.scalar_one_or_none()

    async def find_by_external_message_id(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        external_message_id: str,
        conversation_id: uuid.UUID | None = None,
    ) -> MessageTrace | None:
        normalized = external_message_id.strip()
        if not normalized:
            return None

        conditions = [
            MessageTrace.tenant_id == tenant_id,
            MessageTrace.business_id == business_id,
            MessageTrace.external_message_id == normalized,
        ]
        if conversation_id is not None:
            conditions.append(MessageTrace.conversation_id == conversation_id)

        result = await session.execute(
            select(MessageTrace).where(*conditions).order_by(desc(MessageTrace.created_at)).limit(1)
        )
        return result.scalar_one_or_none()

    async def list_traces_for_conversation(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        conversation_id: uuid.UUID,
        status: str | None = None,
        channel: str | None = None,
        limit: int = TRACE_LIST_DEFAULT_LIMIT,
        offset: int = 0,
    ) -> list[MessageTrace]:
        bounded_limit = min(max(limit, 1), TRACE_LIST_MAX_LIMIT)
        bounded_offset = max(offset, 0)

        conditions = [
            MessageTrace.tenant_id == tenant_id,
            MessageTrace.business_id == business_id,
            MessageTrace.conversation_id == conversation_id,
        ]
        if status is not None:
            conditions.append(MessageTrace.status == status)
        if channel is not None:
            conditions.append(MessageTrace.channel == channel)

        result = await session.execute(
            select(MessageTrace)
            .where(*conditions)
            .order_by(desc(MessageTrace.created_at))
            .limit(bounded_limit)
            .offset(bounded_offset)
        )
        return list(result.scalars().all())

    async def get_or_create_for_inbound(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        flow_id: uuid.UUID,
        conversation_id: uuid.UUID,
        inbound_message_id: uuid.UUID,
        channel: str,
        flow_key: str | None = None,
        external_conversation_id: str | None = None,
        external_message_id: str | None = None,
        idempotency_key: str | None = None,
        trace_metadata: dict[str, Any] | None = None,
        external_trace_id: str | None = None,
    ) -> MessageTrace:
        existing = await self.find_by_inbound_message_id(
            session,
            tenant_id=tenant_id,
            business_id=business_id,
            inbound_message_id=inbound_message_id,
        )
        if existing is not None:
            return existing

        trace = MessageTrace(
            tenant_id=tenant_id,
            business_id=business_id,
            flow_id=flow_id,
            conversation_id=conversation_id,
            inbound_message_id=inbound_message_id,
            channel=channel,
            status=TRACE_STATUS_ACCEPTED,
            flow_key=flow_key,
            external_conversation_id=external_conversation_id,
            external_message_id=external_message_id,
            idempotency_key=idempotency_key,
            external_trace_id=external_trace_id,
            metadata_=trace_metadata,
        )
        session.add(trace)

        try:
            async with session.begin_nested():
                await session.flush()
        except IntegrityError:
            existing = await self.find_by_inbound_message_id(
                session,
                tenant_id=tenant_id,
                business_id=business_id,
                inbound_message_id=inbound_message_id,
            )
            if existing is None:
                raise
            return existing

        return trace

    async def record_inbound_turn(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        flow_id: uuid.UUID,
        conversation_id: uuid.UUID,
        inbound_message_id: uuid.UUID,
        channel: str,
        is_duplicate: bool,
        flow_key: str | None = None,
        external_conversation_id: str | None = None,
        external_message_id: str | None = None,
        idempotency_key: str | None = None,
        trace_metadata: dict[str, Any] | None = None,
        external_trace_id: str | None = None,
    ) -> MessageTrace | None:
        """Create trace for new inbound; on duplicate retry update existing only."""
        if is_duplicate:
            existing = await self.find_by_inbound_message_id(
                session,
                tenant_id=tenant_id,
                business_id=business_id,
                inbound_message_id=inbound_message_id,
            )
            if existing is None:
                # Meta-first Instagram persist may leave message without a trace;
                # create one so re-ingress can link outbound and complete safely.
                return await self.get_or_create_for_inbound(
                    session,
                    tenant_id=tenant_id,
                    business_id=business_id,
                    flow_id=flow_id,
                    conversation_id=conversation_id,
                    inbound_message_id=inbound_message_id,
                    channel=channel,
                    flow_key=flow_key,
                    external_conversation_id=external_conversation_id,
                    external_message_id=external_message_id,
                    idempotency_key=idempotency_key,
                    trace_metadata=trace_metadata,
                    external_trace_id=external_trace_id,
                )
            return await self.record_duplicate_retry(session, existing)

        trace = await self.get_or_create_for_inbound(
            session,
            tenant_id=tenant_id,
            business_id=business_id,
            flow_id=flow_id,
            conversation_id=conversation_id,
            inbound_message_id=inbound_message_id,
            channel=channel,
            flow_key=flow_key,
            external_conversation_id=external_conversation_id,
            external_message_id=external_message_id,
            idempotency_key=idempotency_key,
            trace_metadata=trace_metadata,
            external_trace_id=external_trace_id,
        )
        return trace

    async def mark_processing(
        self,
        session: AsyncSession,
        trace: MessageTrace,
    ) -> MessageTrace:
        if trace.status == TRACE_STATUS_COMPLETED:
            return trace
        trace.status = TRACE_STATUS_PROCESSING
        await session.flush()
        return trace

    async def mark_completed(
        self,
        session: AsyncSession,
        trace: MessageTrace | None,
        *,
        outbound_message_id: uuid.UUID | None = None,
        external_trace_id: str | None = None,
        langfuse_trace_id: str | None = None,
        trace_metadata: dict[str, Any] | None = None,
    ) -> MessageTrace | None:
        if trace is None:
            return None
        trace.status = TRACE_STATUS_COMPLETED
        if outbound_message_id is not None:
            trace.outbound_message_id = outbound_message_id
        if external_trace_id is not None:
            trace.external_trace_id = external_trace_id
        if langfuse_trace_id is not None:
            trace.langfuse_trace_id = langfuse_trace_id
        if trace_metadata:
            trace.metadata_ = _merge_metadata(trace.metadata_, trace_metadata)
        await session.flush()
        return trace

    async def mark_skipped_duplicate(
        self,
        session: AsyncSession,
        trace: MessageTrace,
    ) -> MessageTrace:
        """Backward-compatible alias for duplicate retry handling."""
        return await self.record_duplicate_retry(session, trace)

    async def record_duplicate_retry(
        self,
        session: AsyncSession,
        trace: MessageTrace,
    ) -> MessageTrace:
        """Duplicate inbound retry — never downgrade active or completed processing."""
        if trace.status in (
            TRACE_STATUS_COMPLETED,
            TRACE_STATUS_PROCESSING,
            TRACE_STATUS_ACCEPTED,
        ):
            return trace
        if trace.status == TRACE_STATUS_SKIPPED_DUPLICATE:
            return trace
        trace.status = TRACE_STATUS_SKIPPED_DUPLICATE
        await session.flush()
        return trace

    async def mark_failed(
        self,
        session: AsyncSession,
        trace: MessageTrace,
        *,
        error_type: str,
        error_message: str,
        trace_metadata: dict[str, Any] | None = None,
    ) -> MessageTrace:
        trace.status = TRACE_STATUS_FAILED
        trace.error_type = _truncate_error_field(error_type, 100)
        trace.error_message = _truncate_error_field(error_message, ERROR_MESSAGE_MAX_LENGTH)
        if trace_metadata:
            trace.metadata_ = _merge_metadata(trace.metadata_, trace_metadata)
        await session.flush()
        return trace


def build_trace_metadata(
    *,
    correlation_id: uuid.UUID | None = None,
    n8n_execution_id: str | None = None,
    prompt_run_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if correlation_id is not None:
        payload["correlation_id"] = str(correlation_id)
    if n8n_execution_id:
        payload["n8n_execution_id"] = n8n_execution_id
    if prompt_run_id is not None:
        payload["prompt_run_id"] = str(prompt_run_id)
    return payload


def _merge_metadata(
    existing: dict[str, Any] | None,
    updates: dict[str, Any],
) -> dict[str, Any]:
    merged = dict(existing or {})
    merged.update(updates)
    return merged


def _truncate_error_field(value: str, max_length: int) -> str:
    normalized = value.strip()
    if len(normalized) <= max_length:
        return normalized
    return normalized[: max_length - 3] + "..."
