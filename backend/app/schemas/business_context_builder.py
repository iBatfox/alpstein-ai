from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CreateSessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: UUID
    business_id: UUID
    telegram_user_id: str | None = None
    customer_id: UUID | None = None


class SendMessageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: UUID
    business_id: UUID
    content: str = Field(min_length=1)


class CompleteSessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: UUID
    business_id: UUID


class BusinessContextBuilderSessionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    tenant_id: UUID
    business_id: UUID
    telegram_user_id: str | None = None
    customer_id: UUID | None = None
    status: str
    current_step: str | None = None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None


class BusinessContextBuilderMessageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    session_id: UUID
    role: str
    content: str
    created_at: datetime


class BusinessContextBuilderResultResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    session_id: UUID
    tenant_id: UUID
    business_id: UUID
    structured_context: dict[str, Any]
    generated_prompt: str
    context_file_path: str | None = None
    context_file_url: str | None = None
    created_at: datetime
    updated_at: datetime


class ContextListItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    session_id: UUID
    tenant_id: UUID
    business_id: UUID
    generated_prompt: str
    context_file_path: str | None = None
    context_file_url: str | None = None
    created_at: datetime
    updated_at: datetime


class CreateSessionData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session: BusinessContextBuilderSessionResponse
    message: BusinessContextBuilderMessageResponse


class SendMessageData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session: BusinessContextBuilderSessionResponse
    user_message: BusinessContextBuilderMessageResponse
    assistant_message: BusinessContextBuilderMessageResponse


class GetSessionData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session: BusinessContextBuilderSessionResponse
    messages: list[BusinessContextBuilderMessageResponse]
    result: BusinessContextBuilderResultResponse | None = None


class CompleteSessionData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session: BusinessContextBuilderSessionResponse
    result: BusinessContextBuilderResultResponse


class ContextListData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ContextListItem]
    limit: int
    offset: int


class CreateSessionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: Literal[True] = True
    data: CreateSessionData


class SendMessageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: Literal[True] = True
    data: SendMessageData


class GetSessionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: Literal[True] = True
    data: GetSessionData


class CompleteSessionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: Literal[True] = True
    data: CompleteSessionData


class ContextListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: Literal[True] = True
    data: ContextListData
