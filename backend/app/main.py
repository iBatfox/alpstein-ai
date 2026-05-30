from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api.routes.health import router as health_router
from app.api.routes.instagram_channel import router as instagram_channel_router
from app.api.routes.meta_webhook import router as meta_webhook_router
from app.api.routes.observability import router as observability_router
from app.api.routes.webhook import router as webhook_router
from app.api.webhook_auth import WebhookAuthError
from app.core.observability_context import configure_observability_logging

configure_observability_logging()

app = FastAPI(title="Alpstein AI Backend")


@app.exception_handler(WebhookAuthError)
async def webhook_auth_error_handler(_request, exc: WebhookAuthError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
            },
        },
    )


app.include_router(health_router, prefix="/api/v1")
app.include_router(webhook_router, prefix="/api/v1")
app.include_router(instagram_channel_router, prefix="/api/v1")
app.include_router(observability_router, prefix="/api/v1")
app.include_router(meta_webhook_router, prefix="/webhooks")
