from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Loaded from environment variables / .env. Field names map case-insensitively
    to the UPPER_SNAKE keys in .env.example."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://healthcare:healthcare@localhost:5432/healthcare_assistant"

    jwt_secret: str = "change-me-in-real-env"
    jwt_algorithm: str = "HS256"
    otp_ttl_seconds: int = 300

    sarvam_api_key: str = ""
    google_ai_studio_api_key: str = ""
    google_calendar_client_id: str = ""
    google_calendar_client_secret: str = ""
    google_calendar_redirect_uri: str = "http://localhost:8000/auth/google/callback"

    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    env: str = "development"
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
