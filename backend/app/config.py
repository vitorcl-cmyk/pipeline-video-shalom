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

    # Marca d'agua aplicada nos videos gerados (PNG com transparencia)
    WATERMARK_PATH: Path = BASE_DIR / "app" / "assets" / "watermark.png"
    WATERMARK_ENABLED: bool = True

    # CORS
    CORS_ORIGINS: list[str] = ["*"]

    # Area de admin (login/atividade). Definida via .env -- nunca commitar
    # a senha real no repositorio.
    ADMIN_PASSWORD: str = "change-me-in-production"
    ADMIN_TOKEN_EXPIRE_MINUTES: int = 60 * 4
    ADMIN_ONLINE_WINDOW_MINUTES: int = 5  # janela p/ considerar usuario "ativo agora"


settings = Settings()
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
settings.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
settings.TEMP_DIR.mkdir(parents=True, exist_ok=True)
