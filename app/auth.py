"""HTTP Basic Auth."""

import logging
import secrets
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.config import settings

logger = logging.getLogger("app.auth")
security = HTTPBasic(auto_error=False)


def _validate_auth_config() -> None:
    """Fail fast at import time if auth is enabled but credentials are unset."""
    if settings.auth_enabled:
        if not settings.auth_username or not settings.auth_password:
            raise RuntimeError(
                "Auth enabled but credentials not configured. "
                "Set AII_AUTH_USERNAME and AII_AUTH_PASSWORD environment variables."
            )


_validate_auth_config()


def authenticate(credentials: Optional[HTTPBasicCredentials] = Depends(security)):
    if not settings.auth_enabled:
        return True
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Basic"},
        )
    correct_username = secrets.compare_digest(credentials.username, settings.auth_username)
    correct_password = secrets.compare_digest(credentials.password, settings.auth_password)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return True
