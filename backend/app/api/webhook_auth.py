"""Webhook API token authentication (T10-F1)."""

from __future__ import annotations

import secrets

from fastapi import Header

from app.core.config import settings

WEBHOOK_TOKEN_HEADER = "X-Alpstein-Webhook-Token"


class WebhookAuthError(Exception):
    def __init__(self, *, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(message)


async def require_webhook_token(
    x_alpstein_webhook_token: str | None = Header(
        default=None,
        alias=WEBHOOK_TOKEN_HEADER,
    ),
) -> None:
    expected = settings.n8n_backend_api_token.strip()
    if not expected:
        raise WebhookAuthError(
            status_code=403,
            code="FORBIDDEN",
            message="Webhook authentication is not configured",
        )

    provided = (x_alpstein_webhook_token or "").strip()
    if not provided:
        raise WebhookAuthError(
            status_code=401,
            code="UNAUTHORIZED",
            message="Webhook token is required",
        )

    if not secrets.compare_digest(provided, expected):
        raise WebhookAuthError(
            status_code=401,
            code="UNAUTHORIZED",
            message="Invalid webhook token",
        )
