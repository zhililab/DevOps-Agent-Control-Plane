from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="APP_",
        extra="ignore",
    )

    app_name: str = Field(default="Personal Agent Assistant API", validation_alias="APP_NAME")
    environment: str = Field(default="local", validation_alias="APP_ENVIRONMENT")
    debug: bool = Field(default=False, validation_alias="APP_DEBUG")
    api_prefix: str = Field(default="/api", validation_alias="APP_API_PREFIX")
    database_url: str = Field(
        default="sqlite:///./personal_agent.db",
        validation_alias="DATABASE_URL",
    )
    rate_limit_enabled: bool = Field(default=True, validation_alias="APP_RATE_LIMIT_ENABLED")
    rate_limit_max_requests: int = Field(default=120, validation_alias="APP_RATE_LIMIT_MAX_REQUESTS")
    rate_limit_window_seconds: int = Field(default=60, validation_alias="APP_RATE_LIMIT_WINDOW_SECONDS")
    cors_allowed_origins: str = Field(default="*", validation_alias="APP_CORS_ALLOWED_ORIGINS")
    default_subscription_tier: str = Field(default="pro", validation_alias="APP_DEFAULT_SUBSCRIPTION_TIER")
    entitlement_secret: str = Field(default="", validation_alias="APP_ENTITLEMENT_SECRET")
    entitlement_required: bool = Field(default=False, validation_alias="APP_ENTITLEMENT_REQUIRED")
    allow_legacy_subscription_tier_fallback: bool = Field(
        default=False,
        validation_alias="APP_ALLOW_LEGACY_SUBSCRIPTION_TIER_FALLBACK",
    )
    enable_public_entitlement_bootstrap: bool = Field(
        default=False,
        validation_alias="APP_ENABLE_PUBLIC_ENTITLEMENT_BOOTSTRAP",
    )
    public_entitlement_bootstrap_ttl_seconds: int = Field(
        default=3600 * 24 * 30,
        validation_alias="APP_PUBLIC_ENTITLEMENT_BOOTSTRAP_TTL_SECONDS",
    )

    @property
    def is_production(self) -> bool:
        return self.environment.strip().lower() == "production"

    @property
    def effective_entitlement_required(self) -> bool:
        return self.entitlement_required or self.is_production

    @property
    def effective_allow_legacy_subscription_tier_fallback(self) -> bool:
        if self.is_production:
            return False
        return self.allow_legacy_subscription_tier_fallback

    @property
    def effective_cors_allowed_origins(self) -> list[str]:
        configured = [item.strip() for item in self.cors_allowed_origins.split(",") if item.strip()]
        return configured or ["*"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
