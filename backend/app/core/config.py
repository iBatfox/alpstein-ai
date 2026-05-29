from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_name: str = "alpstein-ai-backend"
    environment: str = "production"
    database_url: str = "postgresql+asyncpg://postgres@localhost/alpstein_ai"
    openai_api_key: str = Field(default="", validation_alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", validation_alias="OPENAI_MODEL")
    ai_request_timeout_seconds: float = Field(
        default=30.0,
        validation_alias="AI_REQUEST_TIMEOUT",
    )
    n8n_backend_api_token: str = Field(
        default="",
        validation_alias="N8N_BACKEND_API_TOKEN",
    )
    langfuse_public_key: str = Field(default="", validation_alias="LANGFUSE_PUBLIC_KEY")
    langfuse_secret_key: str = Field(default="", validation_alias="LANGFUSE_SECRET_KEY")
    langfuse_host: str = Field(
        default="https://cloud.langfuse.com",
        validation_alias="LANGFUSE_HOST",
    )
    langfuse_tracing_enabled: bool = Field(
        default=False,
        validation_alias="LANGFUSE_TRACING_ENABLED",
    )
    delivery_max_retries: int = Field(
        default=3,
        validation_alias="DELIVERY_MAX_RETRIES",
    )
    inbound_provider_retry_max: int = Field(
        default=5,
        validation_alias="INBOUND_PROVIDER_RETRY_MAX",
    )
    delivery_terminal_error_types: str = Field(
        default="chat_not_found,invalid_chat_id",
        validation_alias="DELIVERY_TERMINAL_ERROR_TYPES",
    )
    adapter_monitor_window_hours: int = Field(
        default=24,
        validation_alias="ADAPTER_MONITOR_WINDOW_HOURS",
    )
    adapter_monitor_min_sample: int = Field(
        default=5,
        validation_alias="ADAPTER_MONITOR_MIN_SAMPLE",
    )
    adapter_monitor_degraded_failure_rate: float = Field(
        default=0.50,
        validation_alias="ADAPTER_MONITOR_DEGRADED_FAILURE_RATE",
    )
    adapter_monitor_warning_failure_rate: float = Field(
        default=0.25,
        validation_alias="ADAPTER_MONITOR_WARNING_FAILURE_RATE",
    )
    adapter_monitor_retry_warning: int = Field(
        default=10,
        validation_alias="ADAPTER_MONITOR_RETRY_WARNING",
    )
    adapter_monitor_pending_warning: int = Field(
        default=5,
        validation_alias="ADAPTER_MONITOR_PENDING_WARNING",
    )
    adapter_monitor_pending_stale_min: int = Field(
        default=3,
        validation_alias="ADAPTER_MONITOR_PENDING_STALE_MIN",
    )
    ingress_monitor_failed_warning: int = Field(
        default=3,
        validation_alias="INGRESS_MONITOR_FAILED_WARNING",
    )
    ingress_monitor_failed_degraded: int = Field(
        default=10,
        validation_alias="INGRESS_MONITOR_FAILED_DEGRADED",
    )
    ingress_monitor_inbound_dl_degraded: int = Field(
        default=1,
        validation_alias="INGRESS_MONITOR_INBOUND_DL_DEGRADED",
    )
    ingress_containment_enabled: bool = Field(
        default=False,
        validation_alias="INGRESS_CONTAINMENT_ENABLED",
    )
    rate_limit_enabled: bool = Field(
        default=False,
        validation_alias="RATE_LIMIT_ENABLED",
    )
    rate_limit_window_seconds: int = Field(
        default=60,
        validation_alias="RATE_LIMIT_WINDOW_SECONDS",
    )
    rate_limit_tenant_limit: int = Field(
        default=1000,
        validation_alias="RATE_LIMIT_TENANT_LIMIT",
    )
    rate_limit_business_limit: int = Field(
        default=300,
        validation_alias="RATE_LIMIT_BUSINESS_LIMIT",
    )
    rate_limit_adapter_telegram_limit: int = Field(
        default=120,
        validation_alias="RATE_LIMIT_ADAPTER_TELEGRAM_LIMIT",
    )
    rate_limit_adapter_website_chat_limit: int = Field(
        default=120,
        validation_alias="RATE_LIMIT_ADAPTER_WEBSITE_CHAT_LIMIT",
    )
    rate_limit_conversation_limit: int = Field(
        default=30,
        validation_alias="RATE_LIMIT_CONVERSATION_LIMIT",
    )

    model_config = SettingsConfigDict(
        env_prefix="ALPSTEIN_AI_",
        populate_by_name=True,
    )


LANGFUSE_DEV_ENVIRONMENTS = frozenset({"development", "dev", "local", "test"})


def langfuse_tracing_active(app_settings: Settings | None = None) -> bool:
    """Dev/internal tracing only; requires keys and non-production (or explicit enable)."""
    cfg = app_settings or settings
    if not cfg.langfuse_public_key.strip() or not cfg.langfuse_secret_key.strip():
        return False
    if cfg.langfuse_tracing_enabled:
        return True
    return cfg.environment.lower() in LANGFUSE_DEV_ENVIRONMENTS


settings = Settings()
