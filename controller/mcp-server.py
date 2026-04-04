#!/usr/bin/env python3
"""
MCP Server for OrangeScrum Dev Controller.
Exposes instance management tools for Claude Code.

Auto-discovers config from project .env and registry.
Requires: pip install mcp httpx
"""

import json
import os
from pathlib import Path

import httpx
from mcp.server.fastmcp import FastMCP

# ─── Auto-discovery ──────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).parent.parent


def _load_env():
    """Parse .env file for key=value pairs."""
    env_file = PROJECT_ROOT / ".env"
    if not env_file.exists():
        return {}
    result = {}
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            result[k.strip()] = v.strip()
    return result


_env = _load_env()
CONTROLLER_USER = os.environ.get("CONTROLLER_USER", _env.get("CONTROLLER_USER", "admin"))
CONTROLLER_PASS = os.environ.get("CONTROLLER_PASS", _env.get("CONTROLLER_PASS", ""))
CONTROLLER_URL = os.environ.get("CONTROLLER_URL", "http://localhost:8900")


# ─── HTTP Client ─────────────────────────────────────────────────────────────

def _client() -> httpx.Client:
    return httpx.Client(
        base_url=CONTROLLER_URL,
        auth=(CONTROLLER_USER, CONTROLLER_PASS),
        timeout=60.0,
    )


def _get(path: str, **params) -> str:
    with _client() as c:
        r = c.get(path, params=params)
        r.raise_for_status()
        return r.text


def _post(path: str, **kwargs) -> str:
    with _client() as c:
        r = c.post(path, **kwargs)
        r.raise_for_status()
        return r.text


def _delete(path: str, **params) -> str:
    with _client() as c:
        r = c.delete(path, params=params)
        r.raise_for_status()
        return r.text


def _check_restricted(name: str, operation: str) -> str | None:
    """Check if instance is restricted. Returns error message if blocked, None if allowed."""
    with _client() as c:
        r = c.get("/api/instances")
        r.raise_for_status()
        data = r.json()
    for inst in data.get("instances", []):
        if inst["name"] == name and inst.get("restricted", False):
            return f"Instance '{name}' is restricted. {operation} is blocked to protect sensitive data (API keys, tokens). Use the web UI or CLI directly."
    return None


# ─── MCP Server ──────────────────────────────────────────────────────────────

mcp = FastMCP(
    "dev-controller",
    description="Manage OrangeScrum dev instances — create, destroy, start, stop, migrate, snapshot, and monitor containers.",
)


@mcp.tool()
def get_status() -> str:
    """Get system status: domain, protocol, and health of all base services (Traefik, PostgreSQL, Redis, MySQL, etc.)."""
    return _get("/api/status")


@mcp.tool()
def list_instances() -> str:
    """List all instances with their status, URL, branch, database, and restricted flag. Restricted instances have real API keys and should not be accessed for data operations."""
    return _get("/api/instances")


@mcp.tool()
def create_instance(
    name: str,
    type: str,
    subdomain: str = "",
    branch: str = "",
    from_snapshot: str = "",
    restricted: bool = False,
) -> str:
    """Create a new V4 or selfhosted instance with its own container, database, and subdomain.

    Args:
        name: Instance name (lowercase, alphanumeric with hyphens, e.g. 'v4-feature')
        type: 'v4' or 'selfhosted'
        subdomain: Subdomain for routing (default: same as name)
        branch: Git branch — creates a worktree so this instance runs its own branch
        from_snapshot: Path to a .sql.gz snapshot to restore instead of empty DB (e.g. 'snapshots/v4_main_20260404.sql.gz')
        restricted: Mark as restricted (IP-whitelisted, hidden from MCP data operations)
    """
    body = {"name": name, "type": type, "restricted": restricted}
    if subdomain:
        body["subdomain"] = subdomain
    if branch:
        body["branch"] = branch
    if from_snapshot:
        body["from_snapshot"] = from_snapshot
    return _post("/api/instances", json=body)


@mcp.tool()
def destroy_instance(name: str, drop_db: bool = False) -> str:
    """Destroy an instance — removes container, config, and optionally its database.

    Args:
        name: Instance name
        drop_db: Also drop the PostgreSQL database
    """
    return _delete(f"/api/instances/{name}", drop_db=drop_db)


@mcp.tool()
def start_instance(name: str) -> str:
    """Start a stopped instance.

    Args:
        name: Instance name
    """
    return _post(f"/api/instances/{name}/start")


@mcp.tool()
def stop_instance(name: str) -> str:
    """Stop a running instance.

    Args:
        name: Instance name
    """
    return _post(f"/api/instances/{name}/stop")


@mcp.tool()
def db_setup(name: str, skip_seed: bool = False) -> str:
    """Run CakePHP database migrations and seeds for an instance. Blocked for restricted instances.

    Args:
        name: Instance name
        skip_seed: Skip database seeding (run migrations only)
    """
    err = _check_restricted(name, "db_setup")
    if err:
        return err
    return _post(f"/api/instances/{name}/db-setup", params={"skip_seed": skip_seed})


@mcp.tool()
def db_snapshot(name: str) -> str:
    """Create a pg_dump snapshot of an instance's database. Saved to snapshots/ as .sql.gz. Blocked for restricted instances.

    Args:
        name: Instance name
    """
    err = _check_restricted(name, "db_snapshot")
    if err:
        return err
    return _post(f"/api/instances/{name}/db-snapshot")


@mcp.tool()
def db_restore(name: str, snapshot: str) -> str:
    """Restore a database snapshot into an instance. Blocked for restricted instances.

    Args:
        name: Instance name
        snapshot: Snapshot file path (e.g. 'snapshots/v4_main_20260404_120000.sql.gz')
    """
    err = _check_restricted(name, "db_restore")
    if err:
        return err
    return _post(f"/api/instances/{name}/db-restore", params={"snapshot": snapshot})


@mcp.tool()
def list_snapshots() -> str:
    """List all available database snapshots with name, path, size, and creation date."""
    return _get("/api/snapshots")


@mcp.tool()
def instance_logs(name: str, tail: int = 100) -> str:
    """Get the last N lines of an instance's container logs. Blocked for restricted instances.

    Args:
        name: Instance name
        tail: Number of log lines to return (default 100, max 5000)
    """
    err = _check_restricted(name, "instance_logs")
    if err:
        return err
    return _get(f"/api/instances/{name}/logs", tail=tail)


if __name__ == "__main__":
    mcp.run()
