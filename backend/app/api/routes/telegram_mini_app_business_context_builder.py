from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.business_context_builder import (
    _context_list_item,
    _message_response,
    _not_found_error,
    _result_response,
    _scope_mismatch_error,
    _session_response,
)
from app.core.config import settings
from app.db.session import get_db_session
from app.schemas.business_context_builder import (
    CompleteSessionData,
    CompleteSessionResponse,
    ContextListData,
    ContextListResponse,
    CreateSessionData,
    CreateSessionResponse,
    GetSessionData,
    GetSessionResponse,
    SendMessageData,
    SendMessageResponse,
)
from app.schemas.telegram_mini_app import (
    TelegramMiniAppAllowedUserResponse,
    TelegramMiniAppAuthSessionData,
    TelegramMiniAppAuthSessionRequest,
    TelegramMiniAppAuthSessionResponse,
    TelegramMiniAppCompleteSessionRequest,
    TelegramMiniAppCreateSessionRequest,
    TelegramMiniAppSendMessageRequest,
    TelegramMiniAppUserResponse,
    TelegramMiniAppVerifyAccessData,
    TelegramMiniAppVerifyAccessRequest,
    TelegramMiniAppVerifyAccessResponse,
)
from app.services.business_context_builder_service import (
    DEFAULT_CONTEXT_LIMIT,
    MAX_CONTEXT_LIMIT,
    BusinessContextBuilderInvalidStatusError,
    BusinessContextBuilderInvalidStatusTransitionError,
    BusinessContextBuilderScopeMismatchError,
    BusinessContextBuilderService,
    BusinessContextBuilderSessionClosedError,
    BusinessContextBuilderSessionNotFoundError,
    BusinessContextBuilderValidationError,
)
from app.services.telegram_mini_app_auth_service import (
    TelegramMiniAppAuthContext,
    TelegramMiniAppAuthError,
    TelegramMiniAppAuthService,
)
from app.services.telegram_mini_app_access_service import (
    TelegramMiniAppAccessDeniedError,
    TelegramMiniAppAccessDisabledError,
    TelegramMiniAppAccessService,
)

TELEGRAM_INIT_DATA_HEADER = "X-Telegram-Init-Data"

router = APIRouter(
    prefix="/telegram-mini-app/business-context-builder",
    tags=["telegram-mini-app-business-context-builder"],
)
telegram_auth_service = TelegramMiniAppAuthService()
telegram_access_service = TelegramMiniAppAccessService()
business_context_builder_service = BusinessContextBuilderService()


@dataclass(frozen=True)
class BridgeScope:
    tenant_id: uuid.UUID
    business_id: uuid.UUID


@router.post("/auth/session")
async def auth_session(
    body: TelegramMiniAppAuthSessionRequest,
    session: AsyncSession = Depends(get_db_session),
):
    try:
        auth_context = _validate_init_data(body.init_data)
        await _verify_allowed_user(session, auth_context)
    except TelegramMiniAppAuthError as exc:
        return _auth_error(exc)

    user = auth_context.telegram_user
    return TelegramMiniAppAuthSessionResponse(
        data=TelegramMiniAppAuthSessionData(
            user=TelegramMiniAppUserResponse(
                id=user.id,
                first_name=user.first_name,
                last_name=user.last_name,
                username=user.username,
                language_code=user.language_code,
                is_premium=user.is_premium,
            ),
            auth_date=auth_context.auth_date,
        )
    ).model_dump(mode="json")


@router.post("/verify-access")
async def verify_access(
    body: TelegramMiniAppVerifyAccessRequest,
    session: AsyncSession = Depends(get_db_session),
):
    try:
        auth_context = _validate_init_data(body.init_data)
        allowed_user = await _verify_allowed_user(session, auth_context)
    except TelegramMiniAppAuthError as exc:
        return _auth_error(exc)

    return TelegramMiniAppVerifyAccessResponse(
        data=TelegramMiniAppVerifyAccessData(
            allowed=True,
            user=TelegramMiniAppAllowedUserResponse(
                telegram_user_id=allowed_user.telegram_user_id,
                display_name=allowed_user.display_name,
                company_name=allowed_user.company_name,
                status=allowed_user.status,
            ),
            telegram_user=_telegram_user_response(auth_context),
        )
    ).model_dump(mode="json")


@router.post("/sessions")
async def create_session(
    _body: TelegramMiniAppCreateSessionRequest,
    session: AsyncSession = Depends(get_db_session),
    init_data: str | None = Header(default=None, alias=TELEGRAM_INIT_DATA_HEADER),
):
    auth_context, scope_or_error = await _auth_and_scope(session, init_data)
    if isinstance(scope_or_error, JSONResponse):
        return scope_or_error
    scope = scope_or_error

    builder_session, message = await business_context_builder_service.create_session(
        session,
        tenant_id=scope.tenant_id,
        business_id=scope.business_id,
        telegram_user_id=str(auth_context.telegram_user.id),
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
    body: TelegramMiniAppSendMessageRequest,
    session: AsyncSession = Depends(get_db_session),
    init_data: str | None = Header(default=None, alias=TELEGRAM_INIT_DATA_HEADER),
):
    _auth_context, scope_or_error = await _auth_and_scope(session, init_data)
    if isinstance(scope_or_error, JSONResponse):
        return scope_or_error
    scope = scope_or_error

    try:
        (
            builder_session,
            user_message,
            assistant_message,
        ) = await business_context_builder_service.save_user_message(
            session,
            session_id=session_id,
            tenant_id=scope.tenant_id,
            business_id=scope.business_id,
            content=body.content,
        )
        await session.commit()
    except BusinessContextBuilderSessionNotFoundError:
        await session.rollback()
        return _not_found_error()
    except BusinessContextBuilderScopeMismatchError:
        await session.rollback()
        return _scope_mismatch_error()
    except BusinessContextBuilderSessionClosedError:
        await session.rollback()
        return _error(
            400,
            "CONTEXT_BUILDER_SESSION_CLOSED",
            "Business Context Builder session is completed or cancelled",
        )
    except BusinessContextBuilderInvalidStatusError as exc:
        await session.rollback()
        return _error(409, "CONTEXT_BUILDER_INVALID_STATUS", str(exc))
    except BusinessContextBuilderInvalidStatusTransitionError as exc:
        await session.rollback()
        return _error(
            409,
            "CONTEXT_BUILDER_INVALID_STATUS_TRANSITION",
            str(exc),
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
    session: AsyncSession = Depends(get_db_session),
    init_data: str | None = Header(default=None, alias=TELEGRAM_INIT_DATA_HEADER),
):
    _auth_context, scope_or_error = await _auth_and_scope(session, init_data)
    if isinstance(scope_or_error, JSONResponse):
        return scope_or_error
    scope = scope_or_error

    try:
        snapshot = await business_context_builder_service.get_session(
            session,
            session_id=session_id,
            tenant_id=scope.tenant_id,
            business_id=scope.business_id,
        )
    except BusinessContextBuilderSessionNotFoundError:
        return _not_found_error()
    except BusinessContextBuilderScopeMismatchError:
        return _scope_mismatch_error()
    except BusinessContextBuilderInvalidStatusError as exc:
        return _error(409, "CONTEXT_BUILDER_INVALID_STATUS", str(exc))
    except BusinessContextBuilderValidationError as exc:
        return _error(400, "VALIDATION_ERROR", str(exc))

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
    _body: TelegramMiniAppCompleteSessionRequest,
    session: AsyncSession = Depends(get_db_session),
    init_data: str | None = Header(default=None, alias=TELEGRAM_INIT_DATA_HEADER),
):
    _auth_context, scope_or_error = await _auth_and_scope(session, init_data)
    if isinstance(scope_or_error, JSONResponse):
        return scope_or_error
    scope = scope_or_error

    try:
        builder_session, result = await business_context_builder_service.complete_session(
            session,
            session_id=session_id,
            tenant_id=scope.tenant_id,
            business_id=scope.business_id,
        )
        await session.commit()
    except BusinessContextBuilderSessionNotFoundError:
        await session.rollback()
        return _not_found_error()
    except BusinessContextBuilderScopeMismatchError:
        await session.rollback()
        return _scope_mismatch_error()
    except BusinessContextBuilderInvalidStatusError as exc:
        await session.rollback()
        return _error(409, "CONTEXT_BUILDER_INVALID_STATUS", str(exc))
    except BusinessContextBuilderInvalidStatusTransitionError as exc:
        await session.rollback()
        return _error(
            409,
            "CONTEXT_BUILDER_INVALID_STATUS_TRANSITION",
            str(exc),
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
    limit: int = Query(default=DEFAULT_CONTEXT_LIMIT, ge=1, le=MAX_CONTEXT_LIMIT),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
    init_data: str | None = Header(default=None, alias=TELEGRAM_INIT_DATA_HEADER),
):
    _auth_context, scope_or_error = await _auth_and_scope(session, init_data)
    if isinstance(scope_or_error, JSONResponse):
        return scope_or_error
    scope = scope_or_error

    try:
        results = await business_context_builder_service.list_contexts(
            session,
            tenant_id=scope.tenant_id,
            business_id=scope.business_id,
            limit=limit,
            offset=offset,
        )
    except BusinessContextBuilderValidationError as exc:
        return _error(400, "VALIDATION_ERROR", str(exc))

    return ContextListResponse(
        data=ContextListData(
            items=[_context_list_item(result) for result in results],
            limit=limit,
            offset=offset,
        )
    ).model_dump(mode="json")


async def _auth_and_scope(
    session: AsyncSession,
    init_data: str | None,
) -> tuple[TelegramMiniAppAuthContext, BridgeScope] | tuple[None, JSONResponse]:
    try:
        auth_context = _validate_init_data(init_data)
        await _verify_allowed_user(session, auth_context)
        scope = _resolve_scope()
    except TelegramMiniAppAuthError as exc:
        return None, _auth_error(exc)
    return auth_context, scope


def _validate_init_data(init_data: str | None) -> TelegramMiniAppAuthContext:
    return telegram_auth_service.validate_init_data(
        init_data,
        bot_token=settings.telegram_bot_token,
        max_age_seconds=settings.telegram_initdata_max_age_seconds,
    )


async def _verify_allowed_user(
    session: AsyncSession,
    auth_context: TelegramMiniAppAuthContext,
):
    try:
        return await telegram_access_service.verify_allowed_user(
            session,
            telegram_user_id=auth_context.telegram_user.id,
        )
    except (TelegramMiniAppAccessDeniedError, TelegramMiniAppAccessDisabledError) as exc:
        raise TelegramMiniAppAuthError(
            "TELEGRAM_USER_NOT_ALLOWED",
            "Access is not enabled for your account yet. Please contact Alpstein AI.",
            status_code=403,
        ) from exc


def _resolve_scope() -> BridgeScope:
    tenant_id = _parse_config_uuid(
        settings.bcb_telegram_tenant_id,
        code="BCB_TELEGRAM_TENANT_ID_NOT_CONFIGURED",
        field_name="BCB_TELEGRAM_TENANT_ID",
    )
    business_id = _parse_config_uuid(
        settings.bcb_telegram_business_id,
        code="BCB_TELEGRAM_BUSINESS_ID_NOT_CONFIGURED",
        field_name="BCB_TELEGRAM_BUSINESS_ID",
    )
    return BridgeScope(tenant_id=tenant_id, business_id=business_id)


def _parse_config_uuid(value: str, *, code: str, field_name: str) -> uuid.UUID:
    clean_value = value.strip()
    if not clean_value:
        raise TelegramMiniAppAuthError(
            code,
            f"{field_name} is not configured",
            status_code=503,
        )
    try:
        return uuid.UUID(clean_value)
    except ValueError as exc:
        raise TelegramMiniAppAuthError(
            code,
            f"{field_name} must be a UUID",
            status_code=503,
        ) from exc


def _auth_error(exc: TelegramMiniAppAuthError) -> JSONResponse:
    return _error(exc.status_code, exc.code, exc.message)


def _telegram_user_response(
    auth_context: TelegramMiniAppAuthContext,
) -> TelegramMiniAppUserResponse:
    user = auth_context.telegram_user
    return TelegramMiniAppUserResponse(
        id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        username=user.username,
        language_code=user.language_code,
        is_premium=user.is_premium,
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
