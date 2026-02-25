from pydantic_settings import BaseSettings
from typing import List, Union
import json

class Settings(BaseSettings):
    PROJECT_NAME: str = "Arabic Enterprise Finance IDP Platform"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "4a76c560dc27879636d15d9d5a92f568f4ef1bfdddf73e337292a3964922328" # Default for dev
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 7 days
    
    # DB (defaults for local runs; override with .env for Docker)
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "idp_db"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: str = "5432"

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: str = "6379"

    # Ollama / LLM
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    LLM_MODEL: str = "llama3:8b"

    # OCR
    PADDLEOCR_LANG: str = "en,ar"
    PADDLEOCR_USE_GPU: bool = False

    # File uploads (relative to backend/ or absolute)
    UPLOAD_DIR: str = "uploads"

    model_config = {
        "env_file": (".env", "../.env"),  # backend/.env or project root .env
        "case_sensitive": True,
        "extra": "ignore"
    }

settings = Settings()
