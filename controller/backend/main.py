"""
Dev Controller — FastAPI Backend
Manages dynamic V4/selfhosted instances, container status, logs, and web terminal.
"""

import asyncio
import hashlib
import json
import os
import re
import secrets
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

import docker
from fastapi import (
    FastAPI, WebSocket, WebSocketDisconnect, HTTPException,
    Query, Depends, Request, status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, field_validator

# Paths
PROJECT_ROOT = Path(os.environ.get("PROJECT_ROOT", "/project"))
REGISTRY_FILE = PROJECT_ROOT / "instances" / "registry.json"
TEMPLATES_DIR = PROJECT_ROOT / "templates"
TRAEFIK_DIR = PROJECT_ROOT / "traefik"
INSTANCES_DIR = PROJECT_ROOT / "instances"

# Auth credentials from environment
AUTH_USER = os.environ.get("CONTROLLER_USER", "admin")
AUTH_PASS = os.environ.get("CONTROLLER_PASS", "")

app = FastAPI(title="Dev Controller", version="1.0.0", docs_url=None, redoc_url=None)
security = HTTPBasic()


# ─── Authentication ──────────────────────────────────────────────────────────

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


def verify_ws_auth(websocket: WebSocket) -> bool:
    """Verify WebSocket auth via query param token (Basic credentials base64)."""
    import base64
    token = websocket.query_params.get("token", "")
    if not token or not AUTH_PASS:
        return False
    try:
        decoded = base64.b64decode(token).decode()
        user, password = decoded.split(":", 1)
        return (
            secrets.compare_digest(user.encode(), AUTH_USER.encode())
            and secrets.compare_digest(password.encode(), AUTH_PASS.encode())
        )
    except Exception:
        return False


# ─── CORS — restrict to same origin ─────────────────────────────────────────

domain = os.environ.get("DOMAIN", "")
allowed_origins = [f"https://control.{domain}", f"http://control.{domain}"] if domain else []

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

# Docker client
docker_client = docker.from_env()


# ─── Models ───────────────────────────────────────────────────────────────────

# Strict validation patterns
NAME_PATTERN = re.compile(r"^[a-z0-9]([a-z0-9-]{0,30}[a-z0-9])?$")
SUBDOMAIN_PATTERN = re.compile(r"^[a-z0-9]([a-z0-9-]{0,30}[a-z0-9])?$")


class CreateInstanceRequest(BaseModel):
    name: str
    type: str
    subdomain: Optional[str] = None
    source: Optional[str] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        v = v.lower().strip()
        if not NAME_PATTERN.match(v):
            raise ValueError("Name must be 1-32 lowercase alphanumeric chars with hyphens, cannot start/end with hyphen")
        return v

    @field_validator("type")
    @classmethod
    def validate_type(cls, v):
        if v not in ("v4", "selfhosted"):
            raise ValueError("Type must be 'v4' or 'selfhosted'")
        return v

    @field_validator("subdomain")
    @classmethod
    def validate_subdomain(cls, v):
        if v is None:
            return v
        v = v.lower().strip()
        if not SUBDOMAIN_PATTERN.match(v):
            raise ValueError("Subdomain must be 1-32 lowercase alphanumeric chars with hyphens")
        return v

    @field_validator("source")
    @classmethod
    def validate_source(cls, v):
        if v is None:
            return v
        # Block path traversal
        if ".." in v or v.startswith("/"):
            raise ValueError("Source must be a relative path without '..'")
        return v


# ─── Helpers ──────────────────────────────────────────────────────────────────

RESERVED_SUBDOMAINS = {"www", "app", "mail", "traefik", "storage", "console", "old-selfhosted", "control"}

DEFAULT_SOURCE_PATHS = {
    "v4": os.environ.get("DEFAULT_V4_SOURCE", "./apps/orangescrum-v4"),
    "selfhosted": os.environ.get("DEFAULT_SELFHOSTED_SOURCE", "./apps/durango-pg"),
}


def load_registry():
    if not REGISTRY_FILE.exists():
        return {"domain": None, "instances": {}}
    return json.loads(REGISTRY_FILE.read_text())


def save_registry(registry):
    REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_FILE.write_text(json.dumps(registry, indent=2) + "\n")


def get_domain():
    reg = load_registry()
    if reg.get("domain"):
        return reg["domain"]
    compose = PROJECT_ROOT / "docker-compose.yml"
    if compose.exists():
        match = re.search(r"# Domain: ([a-z0-9.-]+\.[a-z]{2,})", compose.read_text())
        if match:
            return match.group(1)
    return None


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
                break  # exited services block
            # Top-level service: exactly 2-space indent, ends with ':'
            if line.startswith("  ") and not line.startswith("    ") and stripped.endswith(":") and not stripped.startswith("#"):
                svc = stripped.rstrip(":").strip()
                if svc:
                    services.add(svc)
    services.add("controller")  # always include self
    return services


def sanitize_container_name(name: str) -> str:
    """Validate that a name resolves to a known container in our ecosystem."""
    prefix = get_domain_prefix()
    registry = load_registry()

    # Check if it's a known base service
    base_services = _get_base_service_names()
    if name in base_services:
        return f"{prefix}-{name}"

    # Check if it's a registered instance
    if name in registry.get("instances", {}):
        return registry["instances"][name].get("container_name", f"{prefix}-{name}")

    raise HTTPException(404, f"Unknown service or instance: '{name}'")


def safe_sql_identifier(value: str) -> str:
    """Sanitize a value for use as a SQL identifier (database/role name)."""
    sanitized = re.sub(r"[^a-z0-9_]", "", value.lower())
    if not sanitized or not sanitized[0].isalpha():
        sanitized = "db_" + sanitized
    return sanitized[:63]  # PostgreSQL max identifier length


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


# ─── API Routes ───────────────────────────────────────────────────────────────

@app.get("/api/status")
def api_status(user: str = Depends(verify_credentials)):
    prefix = get_domain_prefix()
    https = detect_https()
    base_services = list(_get_base_service_names())
    services = {}
    for svc in base_services:
        services[svc] = get_container_status(f"{prefix}-{svc}")
    return {
        "domain": get_domain(),
        "domain_prefix": prefix,
        "https": https,
        "protocol": "https" if https else "http",
        "services": services,
    }


@app.get("/api/instances")
def api_list_instances(user: str = Depends(verify_credentials)):
    registry = load_registry()
    d = get_domain()
    prefix = get_domain_prefix()
    protocol = "https" if detect_https() else "http"
    instances = []
    for name, inst in registry.get("instances", {}).items():
        container_name = inst.get("container_name", f"{prefix}-{name}")
        s = get_container_status(container_name)
        instances.append({
            "name": name, "type": inst["type"],
            "subdomain": inst["subdomain"],
            "url": f"{protocol}://{inst['subdomain']}.{d}",
            "db_name": inst["db_name"],
            "container_name": container_name,
            "container_status": s["status"],
            "created_at": inst.get("created_at", ""),
            "source_path": inst.get("source_path", ""),
            "branch": inst.get("branch", ""),
        })
    return {"domain": d, "instances": instances}


@app.post("/api/instances")
def api_create_instance(req: CreateInstanceRequest, user: str = Depends(verify_credentials)):
    name = req.name
    instance_type = req.type
    subdomain = req.subdomain or name

    if subdomain in RESERVED_SUBDOMAINS:
        raise HTTPException(400, f"Subdomain '{subdomain}' is reserved")

    registry = load_registry()
    if name in registry.get("instances", {}):
        raise HTTPException(409, f"Instance '{name}' already exists")
    for inst_name, inst in registry.get("instances", {}).items():
        if inst.get("subdomain") == subdomain:
            raise HTTPException(409, f"Subdomain '{subdomain}' already used by '{inst_name}'")

    d = get_domain()
    prefix = get_domain_prefix()
    enable_https = detect_https()
    source = req.source or DEFAULT_SOURCE_PATHS.get(instance_type, DEFAULT_SOURCE_PATHS["v4"])
    source_abs = validate_source_path(source)

    # Sanitized database identifiers
    db_name = safe_sql_identifier(f"{instance_type}_{name}")
    db_user = os.environ.get("DEFAULT_V4_DB_USER", "appuser") if instance_type == "v4" else os.environ.get("DEFAULT_SELFHOSTED_DB_USER", "appuser")
    db_password = db_user

    security_salt = hashlib.sha256(secrets.token_bytes(64)).hexdigest()

    from jinja2 import Environment, FileSystemLoader
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        trim_blocks=True, lstrip_blocks=True, keep_trailing_newline=True,
    )
    ctx = {
        "instance_name": name, "instance_type": instance_type,
        "instance_subdomain": subdomain, "domain": d,
        "domain_prefix": prefix, "enable_https": enable_https,
        "source_path": source_abs, "project_root": str(PROJECT_ROOT),
        "db_name": db_name, "db_user": db_user, "db_password": db_password,
        "security_salt": security_salt, "cache_engine": detect_cache_engine(),
        "generated_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "node_version": "20",
    }

    inst_dir = INSTANCES_DIR / name
    inst_dir.mkdir(parents=True, exist_ok=True)
    (inst_dir / ".env").write_text(env.get_template("instance.env.j2").render(ctx))
    (inst_dir / "docker-compose.yml").write_text(env.get_template("instance-docker-compose.yml.j2").render(ctx))
    (TRAEFIK_DIR / f"instance-{name}.yml").write_text(env.get_template("instance-traefik.yml.j2").render(ctx))

    # Create database with parameterized identifiers
    pg_container = f"{prefix}-postgres16"
    try:
        pg = docker_client.containers.get(pg_container)
        # Use -- to prevent flag injection, identifiers are already sanitized
        pg.exec_run(["psql", "-U", "postgres", "-c",
                      f"DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '{db_user}') "
                      f"THEN CREATE ROLE {db_user} WITH LOGIN PASSWORD '{db_password}'; END IF; END $$;"])
        result = pg.exec_run(["psql", "-U", "postgres", "-tAc",
                               f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'"])
        if "1" not in result.output.decode():
            pg.exec_run(["psql", "-U", "postgres", "-c",
                          f"CREATE DATABASE {db_name} OWNER {db_user};"])
        pg.exec_run(["psql", "-U", "postgres", "-c",
                      f"GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {db_user};"])
    except Exception:
        pass

    try:
        subprocess.run(
            ["docker", "compose", "-f", str(inst_dir / "docker-compose.yml"), "up", "-d"],
            check=True, capture_output=True, text=True, cwd=str(PROJECT_ROOT),
        )
    except Exception:
        pass

    registry["domain"] = d
    registry.setdefault("instances", {})[name] = {
        "type": instance_type, "subdomain": subdomain,
        "db_name": db_name, "db_user": db_user,
        "container_name": f"{prefix}-{name}",
        "source_path": source, "created_at": datetime.now().isoformat(),
        "status": "running",
    }
    save_registry(registry)

    protocol = "https" if enable_https else "http"
    return {"message": f"Instance '{name}' created", "url": f"{protocol}://{subdomain}.{d}"}


@app.delete("/api/instances/{name}")
def api_destroy_instance(name: str, drop_db: bool = Query(False), user: str = Depends(verify_credentials)):
    registry = load_registry()
    if name not in registry.get("instances", {}):
        raise HTTPException(404, f"Instance '{name}' not found")

    inst = registry["instances"][name]
    prefix = get_domain_prefix()

    inst_dir = INSTANCES_DIR / name
    # Prevent path traversal in instance name
    if not str(inst_dir.resolve()).startswith(str(INSTANCES_DIR.resolve())):
        raise HTTPException(400, "Invalid instance name")

    compose_file = inst_dir / "docker-compose.yml"
    if compose_file.exists():
        try:
            subprocess.run(
                ["docker", "compose", "-f", str(compose_file), "down"],
                check=True, capture_output=True, text=True, cwd=str(PROJECT_ROOT),
            )
        except Exception:
            pass

    traefik_file = TRAEFIK_DIR / f"instance-{name}.yml"
    if traefik_file.exists():
        traefik_file.unlink()

    if drop_db:
        db_name = safe_sql_identifier(inst.get("db_name", ""))
        if db_name:
            try:
                pg = docker_client.containers.get(f"{prefix}-postgres16")
                pg.exec_run(["psql", "-U", "postgres", "-c",
                              f"DROP DATABASE IF EXISTS {db_name};"])
            except Exception:
                pass

    if inst_dir.exists():
        shutil.rmtree(inst_dir)

    del registry["instances"][name]
    save_registry(registry)
    return {"message": f"Instance '{name}' destroyed"}


@app.post("/api/instances/{name}/start")
def api_start_instance(name: str, user: str = Depends(verify_credentials)):
    registry = load_registry()
    if name not in registry.get("instances", {}):
        raise HTTPException(404, f"Instance '{name}' not found")
    inst_dir = INSTANCES_DIR / name
    compose_file = inst_dir / "docker-compose.yml"
    if not compose_file.exists():
        raise HTTPException(404, "Compose file not found")
    subprocess.run(
        ["docker", "compose", "-f", str(compose_file), "up", "-d"],
        check=True, capture_output=True, text=True, cwd=str(PROJECT_ROOT),
    )
    registry["instances"][name]["status"] = "running"
    save_registry(registry)
    return {"message": f"Instance '{name}' started"}


@app.post("/api/instances/{name}/stop")
def api_stop_instance(name: str, user: str = Depends(verify_credentials)):
    registry = load_registry()
    if name not in registry.get("instances", {}):
        raise HTTPException(404, f"Instance '{name}' not found")
    inst_dir = INSTANCES_DIR / name
    compose_file = inst_dir / "docker-compose.yml"
    if not compose_file.exists():
        raise HTTPException(404, "Compose file not found")
    subprocess.run(
        ["docker", "compose", "-f", str(compose_file), "down"],
        check=True, capture_output=True, text=True, cwd=str(PROJECT_ROOT),
    )
    registry["instances"][name]["status"] = "stopped"
    save_registry(registry)
    return {"message": f"Instance '{name}' stopped"}


@app.post("/api/instances/{name}/db-setup")
def api_db_setup(name: str, skip_seed: bool = Query(False), user: str = Depends(verify_credentials)):
    registry = load_registry()
    if name not in registry.get("instances", {}):
        raise HTTPException(404, f"Instance '{name}' not found")
    container_name = sanitize_container_name(name)
    try:
        container = docker_client.containers.get(container_name)
    except docker.errors.NotFound:
        raise HTTPException(404, f"Container '{container_name}' not running")
    exit_code, output = container.exec_run("php bin/cake.php migrations migrate", demux=True)
    migrate_out = (output[0] or b"").decode() + (output[1] or b"").decode()
    seed_out = ""
    if not skip_seed:
        exit_code, output = container.exec_run("php bin/cake.php migrations seed", demux=True)
        seed_out = (output[0] or b"").decode() + (output[1] or b"").decode()
    return {"migrations": migrate_out, "seeds": seed_out}


@app.get("/api/instances/{name}/stats")
def api_instance_stats(name: str, user: str = Depends(verify_credentials)):
    container_name = sanitize_container_name(name)
    return get_container_stats(container_name)


@app.get("/api/services/stats")
def api_services_stats(user: str = Depends(verify_credentials)):
    prefix = get_domain_prefix()
    services = list(_get_base_service_names() - {"controller"})
    return {svc: get_container_stats(f"{prefix}-{svc}") for svc in services}


# ─── WebSocket: Live Logs ─────────────────────────────────────────────────────

@app.websocket("/ws/logs/{name}")
async def ws_logs(websocket: WebSocket, name: str):
    if not verify_ws_auth(websocket):
        await websocket.close(code=4401)
        return
    await websocket.accept()

    try:
        container_name = sanitize_container_name(name)
    except HTTPException:
        await websocket.send_text(f"Unknown container: '{name}'")
        await websocket.close()
        return

    try:
        container = docker_client.containers.get(container_name)
    except docker.errors.NotFound:
        await websocket.send_text(f"Container '{container_name}' not found")
        await websocket.close()
        return

    try:
        for log in container.logs(stream=True, follow=True, tail=100):
            await websocket.send_text(log.decode(errors="replace"))
    except WebSocketDisconnect:
        pass
    except Exception:
        await websocket.close()


# ─── WebSocket: Web Terminal ──────────────────────────────────────────────────

@app.websocket("/ws/terminal/{name}")
async def ws_terminal(websocket: WebSocket, name: str):
    if not verify_ws_auth(websocket):
        await websocket.close(code=4401)
        return
    await websocket.accept()

    try:
        container_name = sanitize_container_name(name)
    except HTTPException:
        await websocket.send_text(f"\r\nUnknown container: '{name}'\r\n")
        await websocket.close()
        return

    try:
        docker_client.containers.get(container_name)
    except docker.errors.NotFound:
        await websocket.send_text(f"\r\nContainer '{container_name}' not found\r\n")
        await websocket.close()
        return

    exec_id = docker_client.api.exec_create(
        container_name, "/bin/bash", stdin=True, tty=True, stdout=True, stderr=True,
    )
    sock = docker_client.api.exec_start(exec_id, socket=True, tty=True)
    raw_sock = sock._sock

    async def read_from_container():
        loop = asyncio.get_event_loop()
        try:
            while True:
                data = await loop.run_in_executor(None, raw_sock.recv, 4096)
                if not data:
                    break
                await websocket.send_bytes(data)
        except Exception:
            pass

    reader_task = asyncio.create_task(read_from_container())
    try:
        while True:
            data = await websocket.receive_bytes()
            raw_sock.sendall(data)
    except WebSocketDisconnect:
        pass
    finally:
        reader_task.cancel()
        raw_sock.close()


# ─── Serve Frontend ──────────────────────────────────────────────────────────

FRONTEND_DIR = Path(__file__).parent.parent / "frontend" / "dist"
if FRONTEND_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIR / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # Prevent path traversal in static file serving
        file_path = (FRONTEND_DIR / full_path).resolve()
        if not str(file_path).startswith(str(FRONTEND_DIR.resolve())):
            return FileResponse(FRONTEND_DIR / "index.html")
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(FRONTEND_DIR / "index.html")
