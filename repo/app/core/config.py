"""Application configuration scaffold based on environment variables."""

from functools import lru_cache
import os

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized runtime settings loaded from environment variables."""

    # App
    app_name: str = Field(
        default="offline-retail-middle-platform-api", alias="APP_NAME"
    )
    app_env: str = Field(default="development", alias="APP_ENV")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    app_debug: bool = Field(default=False, alias="APP_DEBUG")
    app_log_level: str = Field(default="INFO", alias="APP_LOG_LEVEL")

    # Security
    jwt_secret_key: str = Field(default="change-me", alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_access_token_expire_hours: int = Field(
        default=8, alias="JWT_ACCESS_TOKEN_EXPIRE_HOURS"
    )
    field_encryption_key: str = Field(
        default="0123456789abcdef0123456789abcdef", alias="FIELD_ENCRYPTION_KEY"
    )
    secret_key: str = Field(default="change-me", alias="SECRET_KEY")
    access_token_expire_minutes: int = Field(
        default=60, alias="ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    password_min_length: int = Field(default=8, alias="PASSWORD_MIN_LENGTH")
    login_max_attempts: int = Field(default=5, alias="LOGIN_MAX_ATTEMPTS")
    login_lock_minutes: int = Field(default=15, alias="LOGIN_LOCK_MINUTES")

    # Database
    postgres_host: str = Field(default="db", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    postgres_db: str = Field(default="retail_platform", alias="POSTGRES_DB")
    postgres_user: str = Field(default="retail_user", alias="POSTGRES_USER")
    postgres_password: str = Field(default="retail_password", alias="POSTGRES_PASSWORD")
    database_url_env: str | None = Field(default=None, alias="DATABASE_URL")
    sqlalchemy_echo: bool = Field(default=False, alias="SQLALCHEMY_ECHO")

    # Domain constraints (scaffold-level constants)
    order_auto_void_minutes: int = Field(default=30, alias="ORDER_AUTO_VOID_MINUTES")
    return_window_days: int = Field(default=7, alias="RETURN_WINDOW_DAYS")
    attachment_max_mb: int = Field(default=20, alias="ATTACHMENT_MAX_MB")
    notification_throttle_minutes: int = Field(
        default=10, alias="NOTIFICATION_THROTTLE_MINUTES"
    )

    # File storage
    storage_root: str = Field(default="./data/storage", alias="STORAGE_ROOT")
    allowed_attachment_types: str = Field(
        default="pdf,jpg,jpeg,png", alias="ALLOWED_ATTACHMENT_TYPES"
    )

    # Feature/value processing
    feature_hot_ttl_seconds: int = Field(default=3600, alias="FEATURE_HOT_TTL_SECONDS")
    feature_cold_ttl_seconds: int = Field(
        default=2592000, alias="FEATURE_COLD_TTL_SECONDS"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        populate_by_name=True,
        extra="ignore",
    )

    @property
    def upload_dir(self) -> str:
        """Construct full path for file uploads."""
        return os.path.join(self.storage_root, "uploads")

    @property
    def database_url(self) -> str:
        """Build SQLAlchemy database URL."""
        if self.database_url_env:
            return self.database_url_env
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()


settings = get_settings()
