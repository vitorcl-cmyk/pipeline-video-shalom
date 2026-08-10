"""Application configuration, loaded from environment variables / .env."""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Security / JWT
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # Database
    DATABASE_URL: str = "sqlite:///./adm.db"

    # CORS
    CORS_ORIGINS: list[str] = ["*"]


settings = Settings()
