"""Application configuration — all values from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    database_url: str = "sqlite+aiosqlite:///data/lms.db"
    log_level: str = "INFO"
    host: str = "0.0.0.0"
    port: int = 8500
    upload_dir: str = "uploads"
    max_upload_mb: int = 50

    model_config = {"env_prefix": "", "case_sensitive": False}


settings = Settings()
