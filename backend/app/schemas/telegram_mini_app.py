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


class TelegramMiniAppInterviewAnswerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(min_length=1)


class TelegramMiniAppInterviewAnswerItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_index: int
    question: str
    answer: str
    answered_at: str


class TelegramMiniAppInterviewSessionData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alpstein_business_id: str
    current_index: int
    question: str | None = None
    progress_current: int
    progress_total: int
    is_complete: bool
    answers: list[TelegramMiniAppInterviewAnswerItem]


class TelegramMiniAppInterviewSessionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: Literal[True] = True
    data: TelegramMiniAppInterviewSessionData


class TelegramMiniAppInterviewDocumentItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    document_type: str
    created_at: str
    filename: str


class TelegramMiniAppInterviewDocumentsData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[TelegramMiniAppInterviewDocumentItem]


class TelegramMiniAppInterviewDocumentsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: Literal[True] = True
    data: TelegramMiniAppInterviewDocumentsData


class TelegramMiniAppInterviewDocumentData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document: TelegramMiniAppInterviewDocumentItem
    content: str


class TelegramMiniAppInterviewDocumentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: Literal[True] = True
    data: TelegramMiniAppInterviewDocumentData
