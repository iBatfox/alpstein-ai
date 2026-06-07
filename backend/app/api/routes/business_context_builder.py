import uuid

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.webhook_auth import require_webhook_token
from app.db.session import get_db_session
from app.models.business_context_builder import (
    BusinessContextBuilderMessage,
    BusinessContextBuilderResult,
    BusinessContextBuilderSession,
)
from app.schemas.business_context_builder import (
    BusinessContextBuilderMessageResponse,
    BusinessContextBuilderResultResponse,
    BusinessContextBuilderSessionResponse,
    CompleteSessionData,
    CompleteSessionRequest,
    CompleteSessionResponse,
    ContextListData,
    ContextListItem,
    ContextListResponse,
    CreateSessionData,
    CreateSessionRequest,
    CreateSessionResponse,
    GetSessionData,
    GetSessionResponse,
    SendMessageData,
    SendMessageRequest,
    SendMessageResponse,
)
from app.services.business_context_builder_service import (
    BusinessContextBuilderService,
    BusinessContextBuilderSessionCompletedError,
    BusinessContextBuilderSessionNotFoundError,
    BusinessContextBuilderValidationError,
)

router = APIRouter(
    prefix="/business-context-builder",
    tags=["business-context-builder"],
    dependencies=[Depends(require_webhook_token)],
)
business_context_builder_service = BusinessContextBuilderService()


@router.post("/sessions")
async def create_session(
    body: CreateSessionRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    builder_session, message = await business_context_builder_service.create_session(
        session,
        tenant_id=body.tenant_id,
        business_id=body.business_id,
        telegram_user_id=body.telegram_user_id,
        customer_id=body.customer_id,
    )
    await session.commit()

    return CreateSessionResponse(
        data=CreateSessionData(
            session=_session_response(builder_session),
            message=_message_response(message),
        )
    ).model_dump(mode="json")


@router.post("/sessions/{session_id}/messages")
async def send_message(
    session_id: uuid.UUID,
    body: SendMessageRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    try:
        (
            builder_session,
            user_message,
            assistant_message,
        ) = await business_context_builder_service.save_user_message(
            session,
            session_id=session_id,
            tenant_id=body.tenant_id,
            business_id=body.business_id,
            content=body.content,
        )
        await session.commit()
    except BusinessContextBuilderSessionNotFoundError:
        await session.rollback()
        return _error(
            404,
            "CONTEXT_BUILDER_SESSION_NOT_FOUND",
            "Business Context Builder session not found",
        )
    except BusinessContextBuilderSessionCompletedError:
        await session.rollback()
        return _error(
            400,
            "CONTEXT_BUILDER_SESSION_COMPLETED",
            "Business Context Builder session is not active",
        )
    except BusinessContextBuilderValidationError as exc:
        await session.rollback()
        return _error(400, "VALIDATION_ERROR", str(exc))

    return SendMessageResponse(
        data=SendMessageData(
            session=_session_response(builder_session),
            user_message=_message_response(user_message),
            assistant_message=_message_response(assistant_message),
        )
    ).model_dump(mode="json")


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: uuid.UUID,
    tenant_id: uuid.UUID = Query(...),
    business_id: uuid.UUID = Query(...),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    try:
        snapshot = await business_context_builder_service.get_session(
            session,
            session_id=session_id,
            tenant_id=tenant_id,
            business_id=business_id,
        )
    except BusinessContextBuilderSessionNotFoundError:
        return _error(
            404,
            "CONTEXT_BUILDER_SESSION_NOT_FOUND",
            "Business Context Builder session not found",
        )

    return GetSessionResponse(
        data=GetSessionData(
            session=_session_response(snapshot.session),
            messages=[_message_response(message) for message in snapshot.messages],
            result=(
                _result_response(snapshot.result)
                if snapshot.result is not None
                else None
            ),
        )
    ).model_dump(mode="json")


@router.post("/sessions/{session_id}/complete")
async def complete_session(
    session_id: uuid.UUID,
    body: CompleteSessionRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    try:
        (
            builder_session,
            result,
        ) = await business_context_builder_service.complete_session(
            session,
            session_id=session_id,
            tenant_id=body.tenant_id,
            business_id=body.business_id,
        )
        await session.commit()
    except BusinessContextBuilderSessionNotFoundError:
        await session.rollback()
        return _error(
            404,
            "CONTEXT_BUILDER_SESSION_NOT_FOUND",
            "Business Context Builder session not found",
        )
    except BusinessContextBuilderSessionCompletedError:
        await session.rollback()
        return _error(
            400,
            "CONTEXT_BUILDER_SESSION_COMPLETED",
            "Business Context Builder session is not active",
        )
    except BusinessContextBuilderValidationError as exc:
        await session.rollback()
        return _error(400, "VALIDATION_ERROR", str(exc))

    return CompleteSessionResponse(
        data=CompleteSessionData(
            session=_session_response(builder_session),
            result=_result_response(result),
        )
    ).model_dump(mode="json")


@router.get("/contexts")
async def list_contexts(
    tenant_id: uuid.UUID = Query(...),
    business_id: uuid.UUID = Query(...),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    results = await business_context_builder_service.list_contexts(
        session,
        tenant_id=tenant_id,
        business_id=business_id,
        limit=limit,
        offset=offset,
    )

    return ContextListResponse(
        data=ContextListData(
            items=[_context_list_item(result) for result in results],
            limit=limit,
            offset=offset,
        )
    ).model_dump(mode="json")


def _session_response(
    session: BusinessContextBuilderSession,
) -> BusinessContextBuilderSessionResponse:
    return BusinessContextBuilderSessionResponse(
        id=session.id,
        tenant_id=session.tenant_id,
        business_id=session.business_id,
        telegram_user_id=session.telegram_user_id,
        customer_id=session.customer_id,
        status=session.status,
        current_step=session.current_step,
        created_at=session.created_at,
        updated_at=session.updated_at,
        completed_at=session.completed_at,
    )


def _message_response(
    message: BusinessContextBuilderMessage,
) -> BusinessContextBuilderMessageResponse:
    return BusinessContextBuilderMessageResponse(
        id=message.id,
        session_id=message.session_id,
        role=message.role,
        content=message.content,
        created_at=message.created_at,
    )


def _result_response(
    result: BusinessContextBuilderResult,
) -> BusinessContextBuilderResultResponse:
    return BusinessContextBuilderResultResponse(
        id=result.id,
        session_id=result.session_id,
        tenant_id=result.tenant_id,
        business_id=result.business_id,
        structured_context=result.structured_context,
        generated_prompt=result.generated_prompt,
        context_file_path=result.context_file_path,
        context_file_url=result.context_file_url,
        created_at=result.created_at,
        updated_at=result.updated_at,
    )


def _context_list_item(result: BusinessContextBuilderResult) -> ContextListItem:
    return ContextListItem(
        id=result.id,
        session_id=result.session_id,
        tenant_id=result.tenant_id,
        business_id=result.business_id,
        generated_prompt=result.generated_prompt,
        context_file_path=result.context_file_path,
        context_file_url=result.context_file_url,
        created_at=result.created_at,
        updated_at=result.updated_at,
    )


def _error(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": {
                "code": code,
                "message": message,
            },
        },
    )
