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
    spam_protection_enabled: bool = Field(
        default=False,
        validation_alias="SPAM_PROTECTION_ENABLED",
    )
    spam_production_safe_mode: bool = Field(
        default=True,
        validation_alias="SPAM_PRODUCTION_SAFE_MODE",
    )
    spam_containment_throttle_ttl_seconds: int = Field(
        default=300,
        validation_alias="SPAM_CONTAINMENT_THROTTLE_TTL_SECONDS",
    )
    spam_containment_block_ttl_seconds: int = Field(
        default=900,
        validation_alias="SPAM_CONTAINMENT_BLOCK_TTL_SECONDS",
    )
    spam_rule_payload_repeat_enabled: bool = Field(
        default=True,
        validation_alias="SPAM_RULE_PAYLOAD_REPEAT_ENABLED",
    )
    spam_rule_payload_repeat_threshold: int = Field(
        default=5,
        validation_alias="SPAM_RULE_PAYLOAD_REPEAT_THRESHOLD",
    )
    spam_rule_payload_repeat_window_seconds: int = Field(
        default=300,
        validation_alias="SPAM_RULE_PAYLOAD_REPEAT_WINDOW_SECONDS",
    )
    spam_rule_payload_repeat_action: str = Field(
        default="throttle",
        validation_alias="SPAM_RULE_PAYLOAD_REPEAT_ACTION",
    )
    spam_rule_conversation_burst_enabled: bool = Field(
        default=True,
        validation_alias="SPAM_RULE_CONVERSATION_BURST_ENABLED",
    )
    spam_rule_conversation_burst_threshold: int = Field(
        default=15,
        validation_alias="SPAM_RULE_CONVERSATION_BURST_THRESHOLD",
    )
    spam_rule_conversation_burst_window_seconds: int = Field(
        default=60,
        validation_alias="SPAM_RULE_CONVERSATION_BURST_WINDOW_SECONDS",
    )
    spam_rule_conversation_burst_action: str = Field(
        default="mark_suspicious",
        validation_alias="SPAM_RULE_CONVERSATION_BURST_ACTION",
    )
    spam_rule_adapter_fanout_enabled: bool = Field(
        default=True,
        validation_alias="SPAM_RULE_ADAPTER_FANOUT_ENABLED",
    )
    spam_rule_adapter_fanout_threshold: int = Field(
        default=50,
        validation_alias="SPAM_RULE_ADAPTER_FANOUT_THRESHOLD",
    )
    spam_rule_adapter_fanout_window_seconds: int = Field(
        default=300,
        validation_alias="SPAM_RULE_ADAPTER_FANOUT_WINDOW_SECONDS",
    )
    spam_rule_adapter_fanout_action: str = Field(
        default="mark_suspicious",
        validation_alias="SPAM_RULE_ADAPTER_FANOUT_ACTION",
    )
    spam_rule_retry_abuse_enabled: bool = Field(
        default=True,
        validation_alias="SPAM_RULE_RETRY_ABUSE_ENABLED",
    )
    spam_rule_retry_abuse_threshold: int = Field(
        default=10,
        validation_alias="SPAM_RULE_RETRY_ABUSE_THRESHOLD",
    )
    spam_rule_retry_abuse_window_seconds: int = Field(
        default=600,
        validation_alias="SPAM_RULE_RETRY_ABUSE_WINDOW_SECONDS",
    )
    spam_rule_retry_abuse_action: str = Field(
        default="throttle",
        validation_alias="SPAM_RULE_RETRY_ABUSE_ACTION",
    )
    spam_rule_replay_storm_enabled: bool = Field(
        default=True,
        validation_alias="SPAM_RULE_REPLAY_STORM_ENABLED",
    )
    spam_rule_replay_storm_threshold: int = Field(
        default=20,
        validation_alias="SPAM_RULE_REPLAY_STORM_THRESHOLD",
    )
    spam_rule_replay_storm_window_seconds: int = Field(
        default=300,
        validation_alias="SPAM_RULE_REPLAY_STORM_WINDOW_SECONDS",
    )
    spam_rule_replay_storm_action: str = Field(
        default="temporary_block",
        validation_alias="SPAM_RULE_REPLAY_STORM_ACTION",
    )
    meta_verify_token: str = Field(default="", validation_alias="META_VERIFY_TOKEN")
    whatsapp_phone_number_id: str = Field(
        default="",
        validation_alias="WHATSAPP_PHONE_NUMBER_ID",
    )
    whatsapp_business_account_id: str = Field(
        default="",
        validation_alias="WHATSAPP_BUSINESS_ACCOUNT_ID",
    )
    whatsapp_access_token: str = Field(
        default="",
        validation_alias="WHATSAPP_ACCESS_TOKEN",
    )
    instagram_app_id: str = Field(default="", validation_alias="INSTAGRAM_APP_ID")
    instagram_app_secret: str = Field(
        default="",
        validation_alias="INSTAGRAM_APP_SECRET",
    )
    instagram_access_token: str = Field(
        default="",
        validation_alias="INSTAGRAM_ACCESS_TOKEN",
    )
    instagram_user_id: str = Field(default="", validation_alias="INSTAGRAM_USER_ID")
    instagram_n8n_ingress_enabled: bool = Field(
        default=False,
        validation_alias="ALPSTEIN_INSTAGRAM_N8N_INGRESS_ENABLED",
    )
    instagram_n8n_ingress_webhook_url: str = Field(
        default=(
            "http://n8n:5678/webhook/alpstein/unified-customer-ingress/instagram/incoming"
        ),
        validation_alias="ALPSTEIN_INSTAGRAM_N8N_INGRESS_WEBHOOK_URL",
    )
    instagram_n8n_dispatch_timeout_seconds: float = Field(
        default=10.0,
        validation_alias="ALPSTEIN_INSTAGRAM_N8N_DISPATCH_TIMEOUT_SECONDS",
    )
    instagram_outbound_enabled: bool = Field(
        default=False,
        validation_alias="ALPSTEIN_INSTAGRAM_OUTBOUND_ENABLED",
    )
    orange_park_bitrix_webhook_url: str = Field(
        default="",
        validation_alias="ORANGE_PARK_BITRIX_WEBHOOK_URL",
    )
    orange_park_bitrix_timeout_seconds: float = Field(
        default=10.0,
        validation_alias="ORANGE_PARK_BITRIX_TIMEOUT_SECONDS",
    )
    bcb_ai_enabled: bool = Field(
        default=True,
        validation_alias="BCB_AI_ENABLED",
    )
    bcb_ai_draft_enabled: bool = Field(
        default=False,
        validation_alias="BCB_AI_DRAFT_ENABLED",
    )
    telegram_bot_token: str = Field(
        default="",
        validation_alias="TELEGRAM_BOT_TOKEN",
    )
    telegram_initdata_max_age_seconds: int = Field(
        default=86400,
        validation_alias="TELEGRAM_INITDATA_MAX_AGE_SECONDS",
    )
    bcb_telegram_tenant_id: str = Field(
        default="",
        validation_alias="BCB_TELEGRAM_TENANT_ID",
    )
    bcb_telegram_business_id: str = Field(
        default="",
        validation_alias="BCB_TELEGRAM_BUSINESS_ID",
    )

    model_config = SettingsConfigDict(
        env_prefix="ALPSTEIN_AI_",
        populate_by_name=True,
    )


def langfuse_tracing_active(app_settings: Settings | None = None) -> bool:
    """Tracing is active whenever the required Langfuse credentials exist."""
    cfg = app_settings or settings
    return bool(
        cfg.langfuse_public_key.strip()
        and cfg.langfuse_secret_key.strip()
    )


settings = Settings()
