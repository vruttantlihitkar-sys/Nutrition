from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")


class Settings(BaseSettings):
    app_name: str = "NutriWise API"
    app_env: str = "development"
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    lmstudio_url: str = "http://localhost:1234/v1/chat/completions"
    lmstudio_model: str = "openchat-3.6-8b-20240522"
    default_use_lmstudio: bool = True
    frontend_origin: str = "http://localhost:5173"
    frontend_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000"
    dataset_path: str = "Anuvaad_INDB_2024.11.xlsx"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        populate_by_name=True,
        extra="ignore",
    )


settings = Settings()


def get_allowed_origins() -> list[str]:
    origins = {
        settings.frontend_origin.strip(),
        *[origin.strip() for origin in settings.frontend_origins.split(",") if origin.strip()],
    }
    return sorted(origins)
