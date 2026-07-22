import os
from typing import Optional
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator

load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    DATABASE_URL: str = "mysql://root:password@localhost:3306/hdbhms"
    DATABASE_POOL_MIN: int = 2
    DATABASE_POOL_MAX: int = 10
    DATABASE_QUERY_TIMEOUT: int = 5

    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.6-flash-lite"
    GEMINI_FALLBACK_MODEL: str = "gemini-3.5-flash-lite"
    GEMINI_TEMPERATURE: float = 0.0
    GEMINI_TIMEOUT: float = 120.0  # Timeout cho Gemini API calls (giây)

    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_WORKERS: int = 1

    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: str = "development"

    RATE_LIMIT_ENABLED: bool = True  # Bật/tắt rate limiting
    RATE_LIMIT_REQUESTS: int = 30  # Số request tối đa
    RATE_LIMIT_WINDOW: int = 60  # Trong khoảng thời gian (giây)

    CACHE_TYPE: str = "memory"  # memory | redis
    REDIS_URL: str = ""  # redis://localhost:6379/0

    @model_validator(mode="after")
    def resolve_api_key(self):
        if not self.GEMINI_API_KEY:
            self.GEMINI_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
        return self


settings = Settings()