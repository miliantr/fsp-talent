"""Application settings (12-factor: everything is overridable through env variables)."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    app_name: str = "FSP Talent — верифицированный подбор ИТ-специалистов"
    environment: str = "development"
    api_prefix: str = "/api"

    # SQLite is used for local runs/tests, PostgreSQL in docker-compose.
    database_url: str = f"sqlite:///{(BACKEND_DIR / 'fsp_talent.db').as_posix()}"

    # --- auth ---------------------------------------------------------------
    jwt_secret: str = "change-me-in-production-please-32b+"
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "fsp-talent"
    access_token_ttl_minutes: int = 60 * 12
    email_code_ttl_minutes: int = 30
    # In dev/demo mode the e-mail confirmation code is returned by the API and shown in the UI,
    # so the flow can be demonstrated without a mail server. Must be false in production.
    email_dev_expose_code: bool = True
    smtp_host: str | None = None
    smtp_port: int = 1025
    smtp_from: str = "no-reply@fsp-talent.local"

    # --- testing engine -----------------------------------------------------
    test_length: int = 20
    test_time_limit_minutes: int = 30
    retake_cooldown_days: int = 30          # same target grade
    grade_change_cooldown_days: int = 90    # verified grade may change at most once per 90 days
    max_categories: int = 3                 # verified categories per candidate (one per specialization)

    # --- regular tasks ------------------------------------------------------
    task_offer_interval_days: int = 7       # at most one new addressed task per candidate per period
    task_offer_loop_minutes: int = 60       # background pass offering due tasks (0 — only on demand)

    # --- invitations --------------------------------------------------------
    invitation_ttl_days: int = 14
    invitations_daily_limit: int = 40       # anti-spam guard per employer

    # --- FSP registry -------------------------------------------------------
    fsp_registry_mode: str = "mock"         # mock | http
    fsp_registry_url: str = "http://localhost:8000/api/mock-fsp/v1"

    # --- matching -----------------------------------------------------------
    matching_weights_json: str | None = None  # optional override of default weights (JSON)

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8080"


@lru_cache
def get_settings() -> Settings:
    return Settings()
