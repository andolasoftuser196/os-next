"""Shared fixtures and helpers for integration tests."""

import os
import time
from pathlib import Path

import pytest
import requests

PROJECT_ROOT = Path(__file__).parent.parent
API_URL = os.environ.get("API_URL", "http://127.0.0.1:8900")


def _read_env(key: str) -> str:
    env_file = PROJECT_ROOT / ".env"
    for line in env_file.read_text().splitlines():
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1].strip()
    return ""


@pytest.fixture(scope="session")
def api():
    """Authenticated requests.Session pointing at the Controller API."""
    user = _read_env("CONTROLLER_USER") or "admin"
    password = _read_env("CONTROLLER_PASS")
    assert password, "CONTROLLER_PASS not found in .env"

    s = requests.Session()
    s.auth = (user, password)
    s.headers["Content-Type"] = "application/json"

    r = s.get(f"{API_URL}/api/status")
    assert r.status_code == 200, f"Controller API not reachable: {r.status_code}"

    return s
