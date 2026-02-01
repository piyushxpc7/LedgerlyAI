from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Literal


class Settings(BaseSettings):
    # Database - defaults to SQLite for local dev, use PostgreSQL in production
    database_url: str = "sqlite:///./ledgerly.db"
    
    # Redis - optional for local dev
    redis_url: str = "redis://localhost:6379/0"
    
    # JWT
    jwt_secret: str = "change-this-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days
    
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
    
    # Frontend URL for CORS
    frontend_url: str = "http://localhost:3000"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
