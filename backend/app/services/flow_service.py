import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import FlowNotFoundError, TenantContextError
from app.models.flow import FLOW_STATUS_ACTIVE, Flow


class FlowService:
    async def resolve_for_webhook(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        flow_key: str | None,
    ) -> Flow:
        normalized_key = _normalize_flow_key(flow_key)
        if normalized_key is not None:
            flow = await self.get_by_flow_key(
                session,
                tenant_id=tenant_id,
                business_id=business_id,
                flow_key=normalized_key,
            )
            if flow is None:
                raise FlowNotFoundError(
                    f"Flow not found for flow_key={normalized_key!r}",
                    flow_key=normalized_key,
                )
            return flow

        flow = await self.get_default_for_business(
            session,
            tenant_id=tenant_id,
            business_id=business_id,
        )
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


def _assert_flow_scope(
    flow: Flow,
    *,
    tenant_id: uuid.UUID,
    business_id: uuid.UUID,
) -> None:
    if flow.tenant_id != tenant_id or flow.business_id != business_id:
        raise TenantContextError(
            "Flow is not scoped to the requested tenant and business"
        )
