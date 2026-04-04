"""Shared helpers — Docker, registry (SQLite-backed), domain detection, sanitization."""

import json
import os
import re
import sqlite3
from pathlib import Path

import docker
from fastapi import HTTPException

# Paths
PROJECT_ROOT = Path(os.environ.get("PROJECT_ROOT", "/project"))
HOST_PROJECT_ROOT = os.environ.get("HOST_PROJECT_ROOT", str(PROJECT_ROOT))
REGISTRY_DB = PROJECT_ROOT / "instances" / "registry.db"
_REGISTRY_JSON = PROJECT_ROOT / "instances" / "registry.json"  # legacy
TEMPLATES_DIR = PROJECT_ROOT / "templates"
TRAEFIK_DIR = PROJECT_ROOT / "traefik"
INSTANCES_DIR = PROJECT_ROOT / "instances"

RESERVED_SUBDOMAINS = {"www", "app", "mail", "traefik", "storage", "console", "old-selfhosted", "control"}

DEFAULT_SOURCE_PATHS = {
    "v4": os.environ.get("DEFAULT_V4_SOURCE", "./apps/orangescrum-v4"),
    "selfhosted": os.environ.get("DEFAULT_SELFHOSTED_SOURCE", "./apps/durango-pg"),
}

# Docker client (singleton)
docker_client = docker.from_env()


# ─── SQLite Registry ────────────────────────────────────────────────────────

def _get_db() -> sqlite3.Connection:
    """Open (and initialize if needed) the registry database."""
    REGISTRY_DB.parent.mkdir(parents=True, exist_ok=True)
    is_new = not REGISTRY_DB.exists()
    db = sqlite3.connect(str(REGISTRY_DB))
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("""
        CREATE TABLE IF NOT EXISTS config (
            key   TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS instances (
            name           TEXT PRIMARY KEY,
            type           TEXT NOT NULL,
            subdomain      TEXT NOT NULL,
            db_name        TEXT NOT NULL,
            db_user        TEXT NOT NULL DEFAULT 'postgres',
            container_name TEXT NOT NULL,
            source_path    TEXT DEFAULT '',
            created_at     TEXT DEFAULT '',
            status         TEXT DEFAULT 'running',
            restricted     INTEGER DEFAULT 0,
            branch         TEXT DEFAULT '',
            worktree_path  TEXT DEFAULT ''
        )
    """)
    db.commit()
    if is_new and _REGISTRY_JSON.exists():
        _migrate_from_json(db)
    return db


def _migrate_from_json(db: sqlite3.Connection):
    """Import data from the legacy registry.json into SQLite."""
    try:
        data = json.loads(_REGISTRY_JSON.read_text())
    except Exception:
        return
    if data.get('domain'):
        db.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
                   ('domain', data['domain']))
    for name, inst in data.get('instances', {}).items():
        db.execute("""
            INSERT OR REPLACE INTO instances
                (name, type, subdomain, db_name, db_user, container_name,
                 source_path, created_at, status, restricted, branch, worktree_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            name, inst['type'], inst['subdomain'], inst['db_name'],
            inst.get('db_user', 'postgres'), inst['container_name'],
            inst.get('source_path', ''), inst.get('created_at', ''),
            inst.get('status', 'running'), int(inst.get('restricted', False)),
            inst.get('branch', ''), inst.get('worktree_path', ''),
        ))
    db.commit()
    _REGISTRY_JSON.rename(_REGISTRY_JSON.with_suffix('.json.bak'))


def _row_to_dict(row: sqlite3.Row) -> tuple[str, dict]:
    d = dict(row)
    name = d.pop('name')
    d['restricted'] = bool(d.get('restricted', 0))
    return name, {k: v for k, v in d.items()
                  if v != '' or k in ('type', 'subdomain', 'db_name', 'db_user', 'container_name', 'status')}


def load_registry() -> dict:
    db = _get_db()
    db.row_factory = sqlite3.Row
    row = db.execute("SELECT value FROM config WHERE key = 'domain'").fetchone()
    domain = row['value'] if row else None
    if not domain:
        compose = PROJECT_ROOT / "docker-compose.yml"
        if compose.exists():
            match = re.search(r"# Domain: ([a-z0-9.-]+\.[a-z]{2,})", compose.read_text())
            if match:
                domain = match.group(1)
    rows = db.execute("SELECT * FROM instances").fetchall()
    instances = {}
    for r in rows:
        name, data = _row_to_dict(r)
        instances[name] = data
    db.close()
    return {"domain": domain, "instances": instances}


def save_registry(registry: dict):
    db = _get_db()
    domain = registry.get("domain")
    instances = registry.get("instances", {})

    db.execute("BEGIN")
    try:
        if domain:
            db.execute("INSERT OR REPLACE INTO config (key, value) VALUES ('domain', ?)", (domain,))
        else:
            db.execute("DELETE FROM config WHERE key = 'domain'")

        existing = {r[0] for r in db.execute("SELECT name FROM instances").fetchall()}
        current = set(instances.keys())

        for gone in existing - current:
            db.execute("DELETE FROM instances WHERE name = ?", (gone,))

        for name, inst in instances.items():
            db.execute("""
                INSERT OR REPLACE INTO instances
                    (name, type, subdomain, db_name, db_user, container_name,
                     source_path, created_at, status, restricted, branch, worktree_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                name, inst['type'], inst['subdomain'], inst['db_name'],
                inst.get('db_user', 'postgres'), inst['container_name'],
                inst.get('source_path', ''), inst.get('created_at', ''),
                inst.get('status', 'running'), int(inst.get('restricted', False)),
                inst.get('branch', ''), inst.get('worktree_path', ''),
            ))

        db.execute("COMMIT")
    except Exception:
        db.execute("ROLLBACK")
        raise
    finally:
        db.close()


# ─── Domain / HTTPS / Cache detection ───────────────────────────────────────

def get_domain():
    reg = load_registry()
    return reg.get("domain")


def get_domain_prefix():
    d = get_domain()
    return d.replace(".", "-").replace("_", "-") if d else "unknown"


def detect_https():
    dynamic_yml = TRAEFIK_DIR / "dynamic.yml"
    if dynamic_yml.exists():
        return "websecure" in dynamic_yml.read_text()
    return True


def detect_cache_engine():
    compose = PROJECT_ROOT / "docker-compose.yml"
    if compose.exists():
        content = compose.read_text()
        if "redis-durango" in content:
            return "redis"
        if "memcached-durango" in content:
            return "memcached"
    return "redis"


# ─── Container helpers ──────────────────────────────────────────────────────

def _get_base_service_names() -> set:
    """Read service names from docker-compose.yml dynamically."""
    compose = PROJECT_ROOT / "docker-compose.yml"
    if not compose.exists():
        return set()
    services = set()
    in_services = False
    for line in compose.read_text().splitlines():
        stripped = line.strip()
        if stripped == "services:":
            in_services = True
            continue
        if in_services:
            if line and not line[0].isspace():
                break
            if line.startswith("  ") and not line.startswith("    ") and stripped.endswith(":") and not stripped.startswith("#"):
                svc = stripped.rstrip(":").strip()
                if svc:
                    services.add(svc)
    services.add("controller")
    return services


def sanitize_container_name(name: str) -> str:
    """Validate that a name resolves to a known container in our ecosystem."""
    prefix = get_domain_prefix()
    registry = load_registry()

    base_services = _get_base_service_names()
    if name in base_services:
        return f"{prefix}-{name}"

    if name in registry.get("instances", {}):
        return registry["instances"][name].get("container_name", f"{prefix}-{name}")

    raise HTTPException(404, f"Unknown service or instance: '{name}'")


def safe_sql_identifier(value: str) -> str:
    """Sanitize a value for use as a SQL identifier (database/role name)."""
    sanitized = re.sub(r"[^a-z0-9_]", "", value.lower())
    if not sanitized or not sanitized[0].isalpha():
        sanitized = "db_" + sanitized
    return sanitized[:63]


def get_container_status(container_name):
    try:
        container = docker_client.containers.get(container_name)
        return {
            "status": container.status,
            "health": container.attrs.get("State", {}).get("Health", {}).get("Status", ""),
            "started_at": container.attrs.get("State", {}).get("StartedAt", ""),
            "image": container.image.tags[0] if container.image.tags else "",
        }
    except docker.errors.NotFound:
        return {"status": "not_found", "health": "", "started_at": "", "image": ""}
    except Exception:
        return {"status": "error", "health": "", "started_at": "", "image": ""}


def get_container_stats(container_name):
    try:
        container = docker_client.containers.get(container_name)
        stats = container.stats(stream=False)
        cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - stats["precpu_stats"]["cpu_usage"]["total_usage"]
        system_delta = stats["cpu_stats"]["system_cpu_usage"] - stats["precpu_stats"]["system_cpu_usage"]
        num_cpus = stats["cpu_stats"].get("online_cpus", 1)
        cpu_percent = (cpu_delta / system_delta) * num_cpus * 100.0 if system_delta > 0 else 0.0
        mem_usage = stats["memory_stats"].get("usage", 0)
        mem_limit = stats["memory_stats"].get("limit", 1)
        return {
            "cpu_percent": round(cpu_percent, 2),
            "mem_usage_mb": round(mem_usage / 1024 / 1024, 1),
            "mem_limit_mb": round(mem_limit / 1024 / 1024, 1),
            "mem_percent": round((mem_usage / mem_limit) * 100.0, 2),
        }
    except Exception:
        return {"cpu_percent": 0, "mem_usage_mb": 0, "mem_limit_mb": 0, "mem_percent": 0}


def validate_source_path(source: str) -> str:
    """Resolve and validate source path stays within project root."""
    resolved = (PROJECT_ROOT / source).resolve()
    if not str(resolved).startswith(str(PROJECT_ROOT.resolve())):
        raise HTTPException(400, "Source path must be within the project directory")
    if not resolved.exists():
        raise HTTPException(400, f"Source path '{source}' does not exist")
    return str(resolved)
