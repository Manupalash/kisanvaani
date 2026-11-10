from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPOSITORY_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    app_name: str = "KisanVaani API"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./kisanvaani.db"
    frontend_origins: str = "http://localhost:3000"
    gnani_api_key: str | None = None
    gnani_stt_url: str = "https://api.vachana.ai/stt/v3"
    gnani_timeout_seconds: float = 45.0
    ffmpeg_binary: str = "ffmpeg"
    assistant_provider: str = "none"
    openai_api_key: str | None = None
    openai_model: str | None = None
    openai_timeout_seconds: float = 60.0
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.8-flash"
    gemini_timeout_seconds: float = 60.0

    model_config = SettingsConfigDict(
        env_file=(str(BACKEND_DIR / ".env"), str(REPOSITORY_DIR / ".env")),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.frontend_origins.split(",") if origin.strip()]


settings = Settings()
