import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "GuardianShield Backend"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"

    # Server binding
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS
    CORS_ORIGINS: List[str] = ["*"]

    # AI & Gemini
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = "gemini-2.5-flash"  # or gemini-2.0-flash / gemini-1.5-flash

    # Telemetry & Call Settings
    DEFAULT_TELEMETRY_INTERVAL_SEC: float = 5.0
    SESSION_EXPIRATION_HOURS: int = 24

    # Fast-Path Critical Keywords (Indian Voice Scam Context)
    CRITICAL_KEYWORDS: List[str] = [
        "otp",
        "pin",
        "password",
        "cvv",
        "transfer money",
        "send money",
        "wire money",
        "upi pin",
        "bank account",
        "arrest",
        "police",
        "cbi",
        "customs",
        "narcotics",
        "digital arrest",
        "court",
        "urgent transfer",
        "do not disconnect",
        "dont disconnect",
        "don't tell anyone",
        "keep this secret",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
