from pydantic_settings import BaseSettings
from pydantic import field_validator
from functools import lru_cache
from typing import Literal


class Settings(BaseSettings):
    # Environment: set to "production" for strict checks
    environment: str = "development"

    # Database - required in production (PostgreSQL). No default in prod.
    database_url: str = "sqlite:///./ledgerly.db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # JWT - must be strong in production (min 32 chars)
    jwt_secret: str = "change-this-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days

    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""
    # Explicit redirect URI in production (e.g. https://api.example.com/auth/google)
    google_oauth_redirect_uri: str = ""

    # Backend base URL for OAuth and links (e.g. https://api.example.com). Empty = derived from request.
    api_base_url: str = ""

    # CORS - comma-separated origins (e.g. https://app.example.com). In prod, no localhost.
    cors_origins: str = ""

    # LLM Configuration
    llm_provider: Literal["mistral", "anthropic"] = "mistral"
    mistral_api_key: str = ""
    anthropic_api_key: str = ""

    # Mistral model settings
    mistral_model: str = "mistral-large-latest"
    mistral_embedding_model: str = "mistral-embed"

    # Anthropic model settings
    anthropic_model: str = "claude-3-sonnet-20240229"

    # Storage
    storage_path: str = "./storage"
    max_upload_size_mb: int = 50
    allowed_file_types: list[str] = ["pdf", "csv", "xlsx", "xls"]

    # Frontend URL for CORS and OAuth redirects (used when cors_origins not set)
    frontend_url: str = "http://localhost:3000"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    @field_validator("environment", mode="before")
    @classmethod
    def normalize_env(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip().lower()
        return "development"

    def is_production(self) -> bool:
        return self.environment == "production"

    def get_cors_origins_list(self) -> list[str]:
        """CORS allow list: cors_origins if set, else [frontend_url]."""
        if self.cors_origins:
            return [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        return [self.frontend_url]

    def validate_production(self) -> None:
        """Raise if production config is unsafe."""
        if not self.is_production():
            return
        if not self.database_url or self.database_url.startswith("sqlite"):
            raise ValueError("Production requires DATABASE_URL (PostgreSQL).")
        if not self.jwt_secret or self.jwt_secret == "change-this-in-production" or len(self.jwt_secret) < 32:
            raise ValueError("Production requires JWT_SECRET with at least 32 characters.")
        if not self.get_cors_origins_list():
            raise ValueError("Production requires CORS_ORIGINS or FRONTEND_URL.")
        for origin in self.get_cors_origins_list():
            if "localhost" in origin or "127.0.0.1" in origin:
                raise ValueError("Production CORS must not include localhost. Set CORS_ORIGINS to your frontend URL.")
        return None


@lru_cache()
def get_settings() -> Settings:
    return Settings()
