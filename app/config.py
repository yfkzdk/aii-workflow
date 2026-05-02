"""App configuration via pydantic-settings."""

import os
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    project_root: str = str(Path(__file__).resolve().parent.parent)
    workflows_dir: str = str(Path(__file__).resolve().parent.parent / "workflows")
    artifacts_dir: str = str(Path(__file__).resolve().parent.parent / "artifacts")

    auth_username: str = os.getenv("AII_AUTH_USERNAME", "demo")
    auth_password: str = os.getenv("AII_AUTH_PASSWORD", "demo")
    auth_enabled: bool = os.getenv("AII_AUTH_ENABLED", "false").lower() == "true"

    pipeline_timeout_seconds: int = 600
    caller_timeout_seconds: int = 300
    max_retries: int = 3

    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
    openai_base_url: str = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com/v1")
    openai_model: str = os.getenv("OPENAI_MODEL", "deepseek-chat")

    model_config = {"env_prefix": "AII_"}


settings = Settings()
