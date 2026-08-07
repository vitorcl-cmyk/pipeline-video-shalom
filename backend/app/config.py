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
    DATABASE_URL: str = "sqlite:///./app.db"

    # Storage
    UPLOAD_DIR: Path = BASE_DIR / "storage" / "uploads"
    OUTPUT_DIR: Path = BASE_DIR / "storage" / "outputs"
    # Intermediate render files (Ken Burns clips, ambient track). Kept on the
    # same disk as the rest of the app's storage instead of the OS default
    # temp dir: on many servers /tmp is a small RAM-backed tmpfs, which fills
    # up fast when rendering several video clips per job.
    TEMP_DIR: Path = BASE_DIR / "storage" / "tmp"

    # Business rules
    DAILY_VIDEO_LIMIT: int = 10
    MAX_PHOTOS_PER_JOB: int = 20
    MAX_UPLOAD_MB: int = 15

    # FFmpeg
    FFMPEG_BINARY: str = "ffmpeg"
    FFPROBE_BINARY: str = "ffprobe"

    # CORS
    CORS_ORIGINS: list[str] = ["*"]


settings = Settings()
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
settings.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
settings.TEMP_DIR.mkdir(parents=True, exist_ok=True)
