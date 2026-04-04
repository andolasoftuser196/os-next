"""Instance registry — SQLite-backed, with auto-migration from JSON."""

import json
import re
import sqlite3
import sys
from pathlib import Path

from .output import Colors, print_colored

RESERVED_SUBDOMAINS = {'www', 'app', 'mail', 'traefik', 'storage', 'console', 'old-selfhosted', 'control'}
DEFAULT_SOURCE_PATHS = {
    'v4': './apps/orangescrum-v4',
    'selfhosted': './apps/durango-pg',
}

REGISTRY_DB = Path('instances/registry.db')
_REGISTRY_JSON = Path('instances/registry.json')  # legacy, for migration

_INSTANCE_COLUMNS = [
    'name', 'type', 'subdomain', 'db_name', 'db_user', 'container_name',
    'source_path', 'created_at', 'status', 'restricted', 'branch', 'worktree_path',
]


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

    # One-time migration from legacy JSON
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
            name,
            inst['type'],
            inst['subdomain'],
            inst['db_name'],
            inst.get('db_user', 'postgres'),
            inst['container_name'],
            inst.get('source_path', ''),
            inst.get('created_at', ''),
            inst.get('status', 'running'),
            int(inst.get('restricted', False)),
            inst.get('branch', ''),
            inst.get('worktree_path', ''),
        ))

    db.commit()
    # Keep the old file as backup
    _REGISTRY_JSON.rename(_REGISTRY_JSON.with_suffix('.json.bak'))


def _row_to_dict(row: sqlite3.Row) -> dict:
    """Convert an instance row to the dict format callers expect."""
    d = dict(row)
    name = d.pop('name')
    d['restricted'] = bool(d.get('restricted', 0))
    # Strip empty-string keys to match old JSON behaviour (absent = missing)
    return name, {k: v for k, v in d.items() if v != '' or k in ('type', 'subdomain', 'db_name', 'db_user', 'container_name', 'status')}


# ─── Public API (same interface as the old JSON version) ─────────────────────

def load_registry() -> dict:
    """Load full registry as a dict: {domain, instances: {name: {...}}}."""
    db = _get_db()
    db.row_factory = sqlite3.Row

    row = db.execute("SELECT value FROM config WHERE key = 'domain'").fetchone()
    domain = row['value'] if row else detect_current_domain()

    rows = db.execute("SELECT * FROM instances").fetchall()
    instances = {}
    for r in rows:
        name, data = _row_to_dict(r)
        instances[name] = data

    db.close()
    return {'domain': domain, 'instances': instances}


def save_registry(registry: dict):
    """Persist a full registry dict back to SQLite (atomic)."""
    db = _get_db()

    domain = registry.get('domain')
    instances = registry.get('instances', {})

    db.execute("BEGIN")
    try:
        # Config
        if domain:
            db.execute("INSERT OR REPLACE INTO config (key, value) VALUES ('domain', ?)", (domain,))
        else:
            db.execute("DELETE FROM config WHERE key = 'domain'")

        # Sync instances: delete removed, upsert current
        existing = {r[0] for r in db.execute("SELECT name FROM instances").fetchall()}
        current = set(instances.keys())

        # Delete removed
        for gone in existing - current:
            db.execute("DELETE FROM instances WHERE name = ?", (gone,))

        # Upsert current
        for name, inst in instances.items():
            db.execute("""
                INSERT OR REPLACE INTO instances
                    (name, type, subdomain, db_name, db_user, container_name,
                     source_path, created_at, status, restricted, branch, worktree_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                name,
                inst['type'],
                inst['subdomain'],
                inst['db_name'],
                inst.get('db_user', 'postgres'),
                inst['container_name'],
                inst.get('source_path', ''),
                inst.get('created_at', ''),
                inst.get('status', 'running'),
                int(inst.get('restricted', False)),
                inst.get('branch', ''),
                inst.get('worktree_path', ''),
            ))

        db.execute("COMMIT")
    except Exception:
        db.execute("ROLLBACK")
        raise
    finally:
        db.close()


def reset_registry():
    """Clear all data (used by --reset). Deletes the DB file entirely."""
    if REGISTRY_DB.exists():
        REGISTRY_DB.unlink()
    # Also remove WAL/SHM files
    for suffix in ('.db-wal', '.db-shm'):
        p = REGISTRY_DB.with_name(REGISTRY_DB.name + suffix.replace('.db', ''))
        if p.exists():
            p.unlink()


# ─── Domain detection (unchanged) ───────────────────────────────────────────

def detect_current_domain():
    """Detect current domain from existing docker-compose.yml"""
    compose_file = Path('docker-compose.yml')
    if not compose_file.exists():
        return None
    try:
        content = compose_file.read_text()
        match = re.search(r'# Domain: ([a-z0-9.-]+\.[a-z]{2,})', content)
        if match:
            return match.group(1)
        match = re.search(r'Host\(`v4\.([a-z0-9.-]+\.[a-z]{2,})`\)', content)
        if match:
            return match.group(1)
    except Exception:
        pass
    return None


def get_project_context():
    """Load project context from registry (SQLite) or generated .env file"""
    reg = load_registry()
    domain = reg.get('domain') or detect_current_domain()
    if not domain:
        print_colored("Error: No domain configured. Run './generate-config.py <domain>' first.", Colors.RED)
        sys.exit(1)

    env_file = Path('.env')
    env_vars = {}
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                env_vars[k.strip()] = v.strip()

    domain_prefix = domain.replace('.', '-').replace('_', '-')

    enable_https = False
    dynamic_yml = Path('traefik/dynamic.yml')
    if dynamic_yml.exists():
        content = dynamic_yml.read_text()
        enable_https = 'websecure' in content

    cache_engine = 'redis'
    compose_file = Path('docker-compose.yml')
    if compose_file.exists():
        content = compose_file.read_text()
        if 'redis-durango' in content:
            cache_engine = 'redis'
        elif 'memcached-durango' in content:
            cache_engine = 'memcached'

    return {
        'domain': domain,
        'domain_prefix': domain_prefix,
        'enable_https': enable_https,
        'cache_engine': cache_engine,
        'project_root': str(Path.cwd()),
        'env_vars': env_vars,
    }
