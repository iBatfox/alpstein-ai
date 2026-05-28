"""Observability APIs for message traces (E2.5) and delivery visibility (E2.6)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.webhook_auth import require_webhook_token
from app.db.session import get_db_session
from app.schemas.delivery_event import (
    DeliveryEventListResponse,
    DeliveryEventListSuccessEnvelope,
    DeliveryEventSuccessEnvelope,
    DeliveryStatusReportRequest,
)
from app.schemas.delivery_event_mapper import delivery_event_to_response
from app.schemas.message_trace import (
    MessageTraceListResponse,
    MessageTraceListSuccessEnvelope,
    MessageTraceSuccessEnvelope,
)
from app.schemas.message_trace_mapper import message_trace_to_response
from app.schemas.replay_event import (
    ReplayEventListResponse,
    ReplayEventListSuccessEnvelope,
)
from app.schemas.replay_event_mapper import replay_event_to_response
from app.services.delivery_visibility_service import DeliveryVisibilityService
from app.services.message_trace_service import MessageTraceService
from app.services.replay_event_service import ReplayEventService

router = APIRouter(prefix="/observability", tags=["observability"])
message_trace_service = MessageTraceService()
delivery_visibility_service = DeliveryVisibilityService()
replay_event_service = ReplayEventService()


def _parse_uuid(value: str, *, field_name: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a valid UUID") from exc


def _validation_error(message: str) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={
            "success": False,
            "error": {"code": "VALIDATION_ERROR", "message": message},
        },
    )


def _not_found(message: str = "Message trace not found") -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={
            "success": False,
            "error": {"code": "NOT_FOUND", "message": message},
        },
    )


@router.get(
    "/traces/{trace_id}",
    dependencies=[Depends(require_webhook_token)],
)
async def get_message_trace(
    trace_id: str,
    tenant_id: str = Query(..., min_length=1),
    business_id: str = Query(..., min_length=1),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    try:
        parsed_trace_id = _parse_uuid(trace_id, field_name="trace_id")
        parsed_tenant_id = _parse_uuid(tenant_id, field_name="tenant_id")
        parsed_business_id = _parse_uuid(business_id, field_name="business_id")
    except ValueError as exc:
        return _validation_error(str(exc))

    trace = await message_trace_service.get_trace_by_id(
        session,
        tenant_id=parsed_tenant_id,
        business_id=parsed_business_id,
        trace_id=parsed_trace_id,
    )
    if trace is None:
        return _not_found()

    return MessageTraceSuccessEnvelope(
        data=message_trace_to_response(trace),
    ).model_dump(mode="json")


@router.get(
    "/traces",
    dependencies=[Depends(require_webhook_token)],
)
async def lookup_message_trace(
    tenant_id: str = Query(..., min_length=1),
    business_id: str = Query(..., min_length=1),
    inbound_message_id: str | None = Query(default=None),
    external_message_id: str | None = Query(default=None),
    conversation_id: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    if bool(inbound_message_id) == bool(external_message_id):
        return _validation_error(
            "Exactly one of inbound_message_id or external_message_id is required"
        )

    try:
        parsed_tenant_id = _parse_uuid(tenant_id, field_name="tenant_id")
        parsed_business_id = _parse_uuid(business_id, field_name="business_id")
        parsed_conversation_id = (
            _parse_uuid(conversation_id, field_name="conversation_id")
            if conversation_id
            else None
        )
    except ValueError as exc:
        return _validation_error(str(exc))

    trace = None
    if inbound_message_id is not None:
        try:
            parsed_inbound_id = _parse_uuid(
                inbound_message_id,
                field_name="inbound_message_id",
            )
        except ValueError as exc:
            return _validation_error(str(exc))
        trace = await message_trace_service.find_by_inbound_message_id(
            session,
            tenant_id=parsed_tenant_id,
            business_id=parsed_business_id,
            inbound_message_id=parsed_inbound_id,
        )
    elif external_message_id is not None:
        trace = await message_trace_service.find_by_external_message_id(
            session,
            tenant_id=parsed_tenant_id,
            business_id=parsed_business_id,
            external_message_id=external_message_id,
            conversation_id=parsed_conversation_id,
        )

    if trace is None:
        return _not_found()

    return MessageTraceSuccessEnvelope(
        data=message_trace_to_response(trace),
    ).model_dump(mode="json")


@router.get(
    "/conversations/{conversation_id}/traces",
    dependencies=[Depends(require_webhook_token)],
)
async def list_conversation_traces(
    conversation_id: str,
    tenant_id: str = Query(..., min_length=1),
    business_id: str = Query(..., min_length=1),
    status: str | None = Query(default=None),
    channel: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    try:
        parsed_conversation_id = _parse_uuid(conversation_id, field_name="conversation_id")
        parsed_tenant_id = _parse_uuid(tenant_id, field_name="tenant_id")
        parsed_business_id = _parse_uuid(business_id, field_name="business_id")
    except ValueError as exc:
        return _validation_error(str(exc))

    traces = await message_trace_service.list_traces_for_conversation(
        session,
        tenant_id=parsed_tenant_id,
        business_id=parsed_business_id,
        conversation_id=parsed_conversation_id,
        status=status,
        channel=channel,
        limit=limit,
        offset=offset,
    )

    return MessageTraceListSuccessEnvelope(
        data=MessageTraceListResponse(
            items=[message_trace_to_response(trace) for trace in traces],
            limit=limit,
            offset=offset,
        ),
    ).model_dump(mode="json")


@router.get(
    "/deliveries/{delivery_id}",
    dependencies=[Depends(require_webhook_token)],
)
async def get_delivery_event(
    delivery_id: str,
    tenant_id: str = Query(..., min_length=1),
    business_id: str = Query(..., min_length=1),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    try:
        parsed_delivery_id = _parse_uuid(delivery_id, field_name="delivery_id")
        parsed_tenant_id = _parse_uuid(tenant_id, field_name="tenant_id")
        parsed_business_id = _parse_uuid(business_id, field_name="business_id")
    except ValueError as exc:
        return _validation_error(str(exc))

    event = await delivery_visibility_service.get_by_id(
        session,
        tenant_id=parsed_tenant_id,
        business_id=parsed_business_id,
        delivery_id=parsed_delivery_id,
    )
    if event is None:
        return _not_found("Delivery event not found")

    return DeliveryEventSuccessEnvelope(
        data=delivery_event_to_response(event),
    ).model_dump(mode="json")


@router.get(
    "/conversations/{conversation_id}/deliveries",
    dependencies=[Depends(require_webhook_token)],
)
async def list_conversation_deliveries(
    conversation_id: str,
    tenant_id: str = Query(..., min_length=1),
    business_id: str = Query(..., min_length=1),
    status: str | None = Query(default=None),
    channel: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    try:
        parsed_conversation_id = _parse_uuid(
            conversation_id,
            field_name="conversation_id",
        )
        parsed_tenant_id = _parse_uuid(tenant_id, field_name="tenant_id")
        parsed_business_id = _parse_uuid(business_id, field_name="business_id")
    except ValueError as exc:
        return _validation_error(str(exc))

    events = await delivery_visibility_service.list_for_conversation(
        session,
        tenant_id=parsed_tenant_id,
        business_id=parsed_business_id,
        conversation_id=parsed_conversation_id,
        status=status,
        channel=channel,
        limit=limit,
        offset=offset,
    )

    return DeliveryEventListSuccessEnvelope(
        data=DeliveryEventListResponse(
            items=[delivery_event_to_response(event) for event in events],
            limit=limit,
            offset=offset,
        ),
    ).model_dump(mode="json")


@router.patch(
    "/deliveries/{delivery_id}",
    dependencies=[Depends(require_webhook_token)],
)
async def report_delivery_status(
    delivery_id: str,
    body: DeliveryStatusReportRequest,
    tenant_id: str = Query(..., min_length=1),
    business_id: str = Query(..., min_length=1),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    try:
        parsed_delivery_id = _parse_uuid(delivery_id, field_name="delivery_id")
        parsed_tenant_id = _parse_uuid(tenant_id, field_name="tenant_id")
        parsed_business_id = _parse_uuid(business_id, field_name="business_id")
    except ValueError as exc:
        return _validation_error(str(exc))

    try:
        event = await delivery_visibility_service.report_status(
            session,
            tenant_id=parsed_tenant_id,
            business_id=parsed_business_id,
            delivery_id=parsed_delivery_id,
            status=body.status,
            provider_message_id=body.provider_message_id,
            provider_status=body.provider_status,
            error_type=body.error_type,
            error_message=body.error_message,
        )
    except ValueError as exc:
        return _validation_error(str(exc))

    if event is None:
        return _not_found("Delivery event not found")

    await session.commit()

    return DeliveryEventSuccessEnvelope(
        data=delivery_event_to_response(event),
    ).model_dump(mode="json")


@router.get(
    "/replays",
    dependencies=[Depends(require_webhook_token)],
)
async def list_replay_events(
    tenant_id: str = Query(..., min_length=1),
    business_id: str = Query(..., min_length=1),
    trace_id: str | None = Query(default=None),
    delivery_id: str | None = Query(default=None),
    conversation_id: str | None = Query(default=None),
    idempotency_key: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    try:
        parsed_tenant_id = _parse_uuid(tenant_id, field_name="tenant_id")
        parsed_business_id = _parse_uuid(business_id, field_name="business_id")
        parsed_trace_id = (
            _parse_uuid(trace_id, field_name="trace_id") if trace_id else None
        )
        parsed_delivery_id = (
            _parse_uuid(delivery_id, field_name="delivery_id") if delivery_id else None
        )
        parsed_conversation_id = (
            _parse_uuid(conversation_id, field_name="conversation_id")
            if conversation_id
            else None
        )
    except ValueError as exc:
        return _validation_error(str(exc))

    events = await replay_event_service.list_events(
        session,
        tenant_id=parsed_tenant_id,
        business_id=parsed_business_id,
        trace_id=parsed_trace_id,
        delivery_id=parsed_delivery_id,
        conversation_id=parsed_conversation_id,
        idempotency_key=idempotency_key,
        event_type=event_type,
        limit=limit,
        offset=offset,
    )

    return ReplayEventListSuccessEnvelope(
        data=ReplayEventListResponse(
            items=[replay_event_to_response(event) for event in events],
            limit=limit,
            offset=offset,
        ),
    ).model_dump(mode="json")
