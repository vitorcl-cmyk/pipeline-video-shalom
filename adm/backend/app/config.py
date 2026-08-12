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

    # Cadastro de novos usuários da equipe desabilitado por padrão (app em
    # fase de teste, acessível pela internet via túnel) — ligue via .env
    # quando for onboardar alguém novo.
    ALLOW_REGISTRATION: bool = False
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 60

    # Database
    DATABASE_URL: str = "sqlite:///./adm.db"

    # CORS
    CORS_ORIGINS: list[str] = ["*"]

    # Análise de ficha (triagem CPF/CNPJ) — chave gratuita do Portal da
    # Transparência (https://api.portaldatransparencia.gov.br). Sem ela, a
    # consulta de servidor público/sanções é pulada com um aviso.
    PORTAL_TRANSPARENCIA_TOKEN: str = ""


settings = Settings()
