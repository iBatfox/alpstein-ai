from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TelegramMiniAppAuthSessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    init_data: str = Field(min_length=1)


class TelegramMiniAppUserResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    language_code: str | None = None
    is_premium: bool | None = None


class TelegramMiniAppAuthSessionData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    authenticated: Literal[True] = True
    user: TelegramMiniAppUserResponse
    auth_date: int


class TelegramMiniAppAuthSessionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: Literal[True] = True
    data: TelegramMiniAppAuthSessionData


class TelegramMiniAppVerifyAccessRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    init_data: str | None = None


class TelegramMiniAppAllowedUserResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    telegram_user_id: int
    display_name: str
    company_name: str
    alpstein_business_id: str | None = None
    status: str


class TelegramMiniAppBusinessIntegrationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    alpstein_business_id: str
    channel_type: str
    display_name: str
    status: str
    external_channel_id: str | None = None
    provider: str | None = None
    workflow_name: str | None = None
    workflow_id: str | None = None
    backend_route: str | None = None
    notes: str | None = None


class TelegramMiniAppVerifyAccessData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    allowed: Literal[True] = True
    user: TelegramMiniAppAllowedUserResponse
    company_name: str
    alpstein_business_id: str | None = None
    integrations: list[TelegramMiniAppBusinessIntegrationResponse]
    telegram_user: TelegramMiniAppUserResponse


class TelegramMiniAppVerifyAccessResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: Literal[True] = True
    data: TelegramMiniAppVerifyAccessData


class TelegramMiniAppCreateSessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TelegramMiniAppSendMessageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(min_length=1)


class TelegramMiniAppCompleteSessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
