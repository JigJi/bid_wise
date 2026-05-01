import os
import urllib.parse
from dotenv import load_dotenv
from pathlib import Path

env_path = Path(".") / ".env"
load_dotenv(dotenv_path=env_path)


class Settings:
    POSTGRES_USER: str = os.getenv("POSTGRES_USER")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD")
    POSTGRES_SERVER: str = os.getenv("POSTGRES_SERVER", "localhost")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "bid_wise")

    APP_PORT: int = int(os.getenv("APP_PORT", "8200"))
    APP_ENV: str = os.getenv("APP_ENV", "dev")

    CDP_PORT: int = int(os.getenv("CDP_PORT", "9231"))
    CHROME_PROFILE_DIR: str = os.getenv("CHROME_PROFILE_DIR", "chrome_profile")

    # LLM (OpenRouter — OpenAI-compatible gateway, multi-provider)
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_BASE_URL: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    LLM_MODEL_EXTRACTION: str = os.getenv("LLM_MODEL_EXTRACTION", "anthropic/claude-sonnet-4.5")
    LLM_MODEL_QA: str = os.getenv("LLM_MODEL_QA", "openai/gpt-4o-mini")
    LLM_HTTP_REFERER: str = os.getenv("LLM_HTTP_REFERER", "https://bidwise.local")
    LLM_APP_TITLE: str = os.getenv("LLM_APP_TITLE", "bid_wise")

    encoded_password = urllib.parse.quote_plus(POSTGRES_PASSWORD) if POSTGRES_PASSWORD else ""
    DATABASE_URL = f"postgresql://{POSTGRES_USER}:{encoded_password}@{POSTGRES_SERVER}:{POSTGRES_PORT}/{POSTGRES_DB}"


settings = Settings()
