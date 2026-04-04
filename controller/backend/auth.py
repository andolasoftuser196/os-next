"""Authentication — HTTP Basic for API routes, token-based for WebSockets."""

import os
import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

AUTH_USER = os.environ.get("CONTROLLER_USER", "admin")
AUTH_PASS = os.environ.get("CONTROLLER_PASS", "")

security = HTTPBasic()


def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    """HTTP Basic Auth — required for all API endpoints."""
    if not AUTH_PASS:
        raise HTTPException(
            status_code=503,
            detail="Controller password not configured. Set CONTROLLER_PASS environment variable.",
        )
    correct_user = secrets.compare_digest(credentials.username.encode(), AUTH_USER.encode())
    correct_pass = secrets.compare_digest(credentials.password.encode(), AUTH_PASS.encode())
    if not (correct_user and correct_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username
