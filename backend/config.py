"""
Configuration module for LMS Course Builder backend.
Loads settings from environment variables and provides app-wide configuration.
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-super-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # API Keys
    CLAUDE_API_KEY: str = os.getenv("CLAUDE_API_KEY", "sk-default-key")
    ELEVENLABS_API_KEY: str = os.getenv("ELEVENLABS_API_KEY", "")
    DEEPGRAM_API_KEY: str = os.getenv("DEEPGRAM_API_KEY", "")

    # Database
    DB_URL: str = "sqlite:///./lms.db"
    SQLALCHEMY_ECHO: bool = False

    # Upload
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB

    # App Info
    APP_VERSION: str = "2.0.0"
    APP_NAME: str = "LMS Course Builder"

    # CORS
    CORS_ORIGINS: list = ["*"]

    # Security Settings
    MAX_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_DURATION_MINUTES: int = 15
    MFA_TOTP_ISSUER: str = "LMS Course Builder"

    # Rate limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    class Config:
        env_file = ".env"
        case_sensitive = False


# Create settings instance
settings = Settings()

# Guard: refuse to start with the default insecure SECRET_KEY
_INSECURE_DEFAULTS = {"your-super-secret-key-change-in-production", "secret", "changeme"}
if settings.SECRET_KEY in _INSECURE_DEFAULTS:
    raise RuntimeError(
        "SECRET_KEY is set to an insecure default value. "
        "Set a strong SECRET_KEY in your .env file before starting the server."
    )

# Create upload directory if it doesn't exist
Path(settings.UPLOAD_DIR).mkdir(exist_ok=True)
