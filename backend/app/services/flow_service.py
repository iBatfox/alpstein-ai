import uuid
import logging
from dataclasses import dataclass

from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError, ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import FlowNotFoundError, TenantContextError
from app.models.flow import FLOW_STATUS_ACTIVE, Flow

logger = logging.getLogger(__name__)

LEGACY_WEBHOOK_FLOW_KEY = "legacy_default"


@dataclass(frozen=True)
class LegacyWebhookFlow:
    id: uuid.UUID
    tenant_id: uuid.UUID
    business_id: uuid.UUID
    flow_key: str = LEGACY_WEBHOOK_FLOW_KEY
    flow_name: str = "Legacy default webhook flow"
    status: str = FLOW_STATUS_ACTIVE
    is_default: bool = True
    metadata_: dict[str, object] | None = None


class FlowService:
    async def resolve_for_webhook(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        flow_key: str | None,
    ) -> Flow | LegacyWebhookFlow:
        if not await _flows_table_exists(session):
            return _legacy_webhook_flow(
                tenant_id=tenant_id,
                business_id=business_id,
            )

        normalized_key = _normalize_flow_key(flow_key)
        if normalized_key is not None:
            try:
                flow = await self.get_by_flow_key(
                    session,
                    tenant_id=tenant_id,
                    business_id=business_id,
                    flow_key=normalized_key,
                )
            except (DBAPIError, ProgrammingError) as exc:
                if _is_missing_flows_table_error(exc):
                    return _legacy_webhook_flow(
                        tenant_id=tenant_id,
                        business_id=business_id,
                    )
                raise
            if flow is None:
                raise FlowNotFoundError(
                    f"Flow not found for flow_key={normalized_key!r}",
                    flow_key=normalized_key,
                )
            return flow

        try:
            flow = await self.get_default_for_business(
                session,
                tenant_id=tenant_id,
                business_id=business_id,
            )
        except (DBAPIError, ProgrammingError) as exc:
            if _is_missing_flows_table_error(exc):
                return _legacy_webhook_flow(
                    tenant_id=tenant_id,
                    business_id=business_id,
                )
            raise
        if flow is None:
            raise FlowNotFoundError(
                "No default flow configured for business",
                flow_key=None,
            )
        return flow

    async def get_by_flow_key(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        flow_key: str,
    ) -> Flow | None:
        result = await session.execute(
            select(Flow)
            .where(
                Flow.tenant_id == tenant_id,
                Flow.business_id == business_id,
                Flow.flow_key == flow_key,
            )
            .limit(1)
        )
        flow = result.scalar_one_or_none()
        if flow is not None:
            _assert_flow_scope(flow, tenant_id=tenant_id, business_id=business_id)
        return flow

    async def get_default_for_business(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
    ) -> Flow | None:
        result = await session.execute(
            select(Flow)
            .where(
                Flow.tenant_id == tenant_id,
                Flow.business_id == business_id,
                Flow.is_default.is_(True),
                Flow.status == FLOW_STATUS_ACTIVE,
            )
            .limit(1)
        )
        flow = result.scalar_one_or_none()
        if flow is not None:
            _assert_flow_scope(flow, tenant_id=tenant_id, business_id=business_id)
        return flow


def _normalize_flow_key(flow_key: str | None) -> str | None:
    if flow_key is None:
        return None
    stripped = flow_key.strip()
    return stripped if stripped else None


async def _flows_table_exists(session: AsyncSession) -> bool:
    result = await session.execute(
        text(
            """
            select exists (
              select 1
              from information_schema.tables
              where table_schema = current_schema()
                and table_name = 'flows'
            )
            """
        )
    )
    return bool(result.scalar_one())


def _legacy_webhook_flow(
    *,
    tenant_id: uuid.UUID,
    business_id: uuid.UUID,
) -> LegacyWebhookFlow:
    logger.warning("flows table unavailable; using legacy webhook flow fallback")
    return LegacyWebhookFlow(
        id=uuid.uuid5(business_id, LEGACY_WEBHOOK_FLOW_KEY),
        tenant_id=tenant_id,
        business_id=business_id,
        metadata_={"legacy_fallback": True},
    )


def _is_missing_flows_table_error(exc: BaseException) -> bool:
    text_value = str(exc).lower()
    return (
        "relation \"flows\" does not exist" in text_value
        or "undefinedtableerror" in text_value and "flows" in text_value
    )


def _assert_flow_scope(
    flow: Flow | LegacyWebhookFlow,
    *,
    tenant_id: uuid.UUID,
    business_id: uuid.UUID,
) -> None:
    if flow.tenant_id != tenant_id or flow.business_id != business_id:
        raise TenantContextError(
            "Flow is not scoped to the requested tenant and business"
        )
