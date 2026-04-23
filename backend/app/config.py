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
    default_subscription_tier: str = Field(default="pro", validation_alias="APP_DEFAULT_SUBSCRIPTION_TIER")
    entitlement_secret: str = Field(default="", validation_alias="APP_ENTITLEMENT_SECRET")
    entitlement_required: bool = Field(default=False, validation_alias="APP_ENTITLEMENT_REQUIRED")


@lru_cache
def get_settings() -> Settings:
    return Settings()
