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


class TelegramMiniAppCreateSessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TelegramMiniAppSendMessageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(min_length=1)


class TelegramMiniAppCompleteSessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
