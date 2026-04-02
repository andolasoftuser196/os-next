"""
OrangeScrum Controller — FastAPI Backend
Manages dynamic V4/selfhosted instances, container status, logs, and web terminal.
"""

import asyncio
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

import docker
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

# Paths — controller runs from project root or uses env var
PROJECT_ROOT = Path(os.environ.get("PROJECT_ROOT", "/project"))
REGISTRY_FILE = PROJECT_ROOT / "instances" / "registry.json"
TEMPLATES_DIR = PROJECT_ROOT / "templates"
TRAEFIK_DIR = PROJECT_ROOT / "traefik"
INSTANCES_DIR = PROJECT_ROOT / "instances"

app = FastAPI(title="OrangeScrum Controller", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Docker client
docker_client = docker.from_env()


# ─── Models ───────────────────────────────────────────────────────────────────

class CreateInstanceRequest(BaseModel):
    name: str
    type: str  # "v4" or "selfhosted"
    subdomain: Optional[str] = None
    source: Optional[str] = None


# ─── Helpers ──────────────────────────────────────────────────────────────────

RESERVED_SUBDOMAINS = {"www", "app", "mail", "traefik", "storage", "console", "old-selfhosted", "control"}

DEFAULT_SOURCE_PATHS = {
    "v4": "./apps/orangescrum-v4",
    "selfhosted": "./apps/durango-pg",
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
    # Detect from docker-compose.yml
    compose = PROJECT_ROOT / "docker-compose.yml"
    if compose.exists():
        import re
        match = re.search(r"Host\(`v4\.([a-z0-9.-]+\.[a-z]{2,})`\)", compose.read_text())
        if match:
            return match.group(1)
        match = re.search(r"# Domain: ([a-z0-9.-]+\.[a-z]{2,})", compose.read_text())
        if match:
            return match.group(1)
    return None


def get_domain_prefix():
    domain = get_domain()
    if domain:
        return domain.replace(".", "-").replace("_", "-")
    return "unknown"


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


def get_container_status(container_name):
    """Get container status from Docker."""
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
    except Exception as e:
        return {"status": f"error: {e}", "health": "", "started_at": "", "image": ""}


def get_container_stats(container_name):
    """Get CPU/memory stats for a container."""
    try:
        container = docker_client.containers.get(container_name)
        stats = container.stats(stream=False)

        # CPU
        cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - stats["precpu_stats"]["cpu_usage"]["total_usage"]
        system_delta = stats["cpu_stats"]["system_cpu_usage"] - stats["precpu_stats"]["system_cpu_usage"]
        num_cpus = stats["cpu_stats"].get("online_cpus", 1)
        cpu_percent = (cpu_delta / system_delta) * num_cpus * 100.0 if system_delta > 0 else 0.0

        # Memory
        mem_usage = stats["memory_stats"].get("usage", 0)
        mem_limit = stats["memory_stats"].get("limit", 1)
        mem_percent = (mem_usage / mem_limit) * 100.0

        return {
            "cpu_percent": round(cpu_percent, 2),
            "mem_usage_mb": round(mem_usage / 1024 / 1024, 1),
            "mem_limit_mb": round(mem_limit / 1024 / 1024, 1),
            "mem_percent": round(mem_percent, 2),
        }
    except Exception:
        return {"cpu_percent": 0, "mem_usage_mb": 0, "mem_limit_mb": 0, "mem_percent": 0}


# ─── API Routes ───────────────────────────────────────────────────────────────

@app.get("/api/status")
def api_status():
    """Overall system status."""
    domain = get_domain()
    prefix = get_domain_prefix()
    https = detect_https()
    protocol = "https" if https else "http"

    # Base services status
    base_services = ["traefik", "postgres16", "mysql", "redis-durango",
                     "memcached-orangescrum", "orangescrum", "mailhog", "dns", "browser"]
    services = {}
    for svc in base_services:
        container_name = f"{prefix}-{svc}"
        services[svc] = get_container_status(container_name)

    return {
        "domain": domain,
        "domain_prefix": prefix,
        "https": https,
        "protocol": protocol,
        "services": services,
    }


@app.get("/api/instances")
def api_list_instances():
    """List all dynamic instances."""
    registry = load_registry()
    domain = get_domain()
    prefix = get_domain_prefix()
    https = detect_https()
    protocol = "https" if https else "http"

    instances = []
    for name, inst in registry.get("instances", {}).items():
        container_name = inst.get("container_name", f"{prefix}-{name}")
        status = get_container_status(container_name)
        instances.append({
            "name": name,
            "type": inst["type"],
            "subdomain": inst["subdomain"],
            "url": f"{protocol}://{inst['subdomain']}.{domain}",
            "db_name": inst["db_name"],
            "container_name": container_name,
            "container_status": status["status"],
            "created_at": inst.get("created_at", ""),
            "source_path": inst.get("source_path", ""),
        })

    return {"domain": domain, "instances": instances}


@app.post("/api/instances")
def api_create_instance(req: CreateInstanceRequest):
    """Create a new dynamic instance."""
    import hashlib
    import re

    name = req.name.lower().strip()
    instance_type = req.type
    subdomain = (req.subdomain or name).lower().strip()
    source = req.source

    # Validate
    if not re.match(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$", name):
        raise HTTPException(400, "Name must be lowercase alphanumeric with hyphens")

    if subdomain in RESERVED_SUBDOMAINS:
        raise HTTPException(400, f"Subdomain '{subdomain}' is reserved")

    if instance_type not in ("v4", "selfhosted"):
        raise HTTPException(400, "Type must be 'v4' or 'selfhosted'")

    registry = load_registry()
    if name in registry.get("instances", {}):
        raise HTTPException(409, f"Instance '{name}' already exists")

    for inst_name, inst in registry.get("instances", {}).items():
        if inst.get("subdomain") == subdomain:
            raise HTTPException(409, f"Subdomain '{subdomain}' already used by '{inst_name}'")

    domain = get_domain()
    prefix = get_domain_prefix()
    enable_https = detect_https()

    if not source:
        source = DEFAULT_SOURCE_PATHS.get(instance_type, DEFAULT_SOURCE_PATHS["v4"])
    source_abs = str((PROJECT_ROOT / source).resolve())

    if not Path(source_abs).exists():
        raise HTTPException(400, f"Source path '{source}' does not exist")

    # Database
    db_name = f"{instance_type}_{name}".replace("-", "_")
    db_user = "orangescrum" if instance_type == "v4" else "durango"
    db_password = db_user

    # Security salt
    import secrets
    security_salt = hashlib.sha256(secrets.token_bytes(64)).hexdigest()

    # Render templates
    from jinja2 import Environment, FileSystemLoader
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        trim_blocks=True, lstrip_blocks=True, keep_trailing_newline=True,
    )

    ctx = {
        "instance_name": name, "instance_type": instance_type,
        "instance_subdomain": subdomain, "domain": domain,
        "domain_prefix": prefix, "enable_https": enable_https,
        "source_path": source_abs, "project_root": str(PROJECT_ROOT),
        "db_name": db_name, "db_user": db_user, "db_password": db_password,
        "security_salt": security_salt, "cache_engine": detect_cache_engine(),
        "generated_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "node_version": "20",
    }

    # Create instance dir
    inst_dir = INSTANCES_DIR / name
    inst_dir.mkdir(parents=True, exist_ok=True)

    # Generate files
    (inst_dir / ".env").write_text(env.get_template("instance.env.j2").render(ctx))
    (inst_dir / "docker-compose.yml").write_text(env.get_template("instance-docker-compose.yml.j2").render(ctx))
    (TRAEFIK_DIR / f"instance-{name}.yml").write_text(env.get_template("instance-traefik.yml.j2").render(ctx))

    # Create database
    pg_container = f"{prefix}-postgres16"
    try:
        pg = docker_client.containers.get(pg_container)
        pg.exec_run(f"psql -U postgres -c \"DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '{db_user}') THEN CREATE ROLE {db_user} WITH LOGIN PASSWORD '{db_password}'; END IF; END $$;\"")
        result = pg.exec_run(f"psql -U postgres -tAc \"SELECT 1 FROM pg_database WHERE datname = '{db_name}'\"")
        if "1" not in result.output.decode():
            pg.exec_run(f"psql -U postgres -c \"CREATE DATABASE {db_name} OWNER {db_user};\"")
        pg.exec_run(f"psql -U postgres -c \"GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {db_user};\"")
    except Exception as e:
        pass  # DB will be created on db-setup

    # Start instance
    try:
        subprocess.run(
            ["docker", "compose", "-f", str(inst_dir / "docker-compose.yml"), "up", "-d"],
            check=True, capture_output=True, text=True, cwd=str(PROJECT_ROOT),
        )
    except Exception:
        pass

    # Update registry
    registry["domain"] = domain
    registry.setdefault("instances", {})[name] = {
        "type": instance_type, "subdomain": subdomain,
        "db_name": db_name, "db_user": db_user,
        "container_name": f"{prefix}-{name}",
        "source_path": source, "created_at": datetime.now().isoformat(),
        "status": "running",
    }
    save_registry(registry)

    protocol = "https" if enable_https else "http"
    return {"message": f"Instance '{name}' created", "url": f"{protocol}://{subdomain}.{domain}"}


@app.delete("/api/instances/{name}")
def api_destroy_instance(name: str, drop_db: bool = Query(False)):
    """Destroy an instance."""
    registry = load_registry()
    if name not in registry.get("instances", {}):
        raise HTTPException(404, f"Instance '{name}' not found")

    inst = registry["instances"][name]
    prefix = get_domain_prefix()

    # Stop container
    inst_dir = INSTANCES_DIR / name
    compose_file = inst_dir / "docker-compose.yml"
    if compose_file.exists():
        try:
            subprocess.run(
                ["docker", "compose", "-f", str(compose_file), "down"],
                check=True, capture_output=True, text=True, cwd=str(PROJECT_ROOT),
            )
        except Exception:
            pass

    # Remove traefik config
    traefik_file = TRAEFIK_DIR / f"instance-{name}.yml"
    if traefik_file.exists():
        traefik_file.unlink()

    # Drop database
    if drop_db:
        db_name = inst.get("db_name", "")
        if db_name:
            try:
                pg = docker_client.containers.get(f"{prefix}-postgres16")
                pg.exec_run(f"psql -U postgres -c \"DROP DATABASE IF EXISTS {db_name};\"")
            except Exception:
                pass

    # Remove instance dir
    if inst_dir.exists():
        import shutil
        shutil.rmtree(inst_dir)

    del registry["instances"][name]
    save_registry(registry)

    return {"message": f"Instance '{name}' destroyed"}


@app.post("/api/instances/{name}/start")
def api_start_instance(name: str):
    """Start a stopped instance."""
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
def api_stop_instance(name: str):
    """Stop a running instance."""
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
def api_db_setup(name: str, skip_seed: bool = Query(False)):
    """Run migrations and seeds."""
    registry = load_registry()
    if name not in registry.get("instances", {}):
        raise HTTPException(404, f"Instance '{name}' not found")

    prefix = get_domain_prefix()
    container_name = f"{prefix}-{name}"

    try:
        container = docker_client.containers.get(container_name)
    except docker.errors.NotFound:
        raise HTTPException(404, f"Container '{container_name}' not running")

    # Migrations
    exit_code, output = container.exec_run("php bin/cake.php migrations migrate", demux=True)
    migrate_out = (output[0] or b"").decode() + (output[1] or b"").decode()

    seed_out = ""
    if not skip_seed:
        exit_code, output = container.exec_run("php bin/cake.php migrations seed", demux=True)
        seed_out = (output[0] or b"").decode() + (output[1] or b"").decode()

    return {"migrations": migrate_out, "seeds": seed_out}


@app.get("/api/instances/{name}/stats")
def api_instance_stats(name: str):
    """Get resource usage for an instance."""
    registry = load_registry()
    if name not in registry.get("instances", {}):
        raise HTTPException(404, f"Instance '{name}' not found")

    prefix = get_domain_prefix()
    container_name = f"{prefix}-{name}"
    return get_container_stats(container_name)


@app.get("/api/services/stats")
def api_services_stats():
    """Get resource usage for all base services."""
    prefix = get_domain_prefix()
    services = ["traefik", "postgres16", "mysql", "redis-durango",
                "memcached-orangescrum", "orangescrum", "mailhog", "dns", "browser"]
    result = {}
    for svc in services:
        result[svc] = get_container_stats(f"{prefix}-{svc}")
    return result


# ─── WebSocket: Live Logs ─────────────────────────────────────────────────────

@app.websocket("/ws/logs/{name}")
async def ws_logs(websocket: WebSocket, name: str):
    """Stream container logs via WebSocket."""
    await websocket.accept()
    prefix = get_domain_prefix()
    container_name = f"{prefix}-{name}"

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
    except Exception as e:
        await websocket.send_text(f"Error: {e}")
        await websocket.close()


# ─── WebSocket: Web Terminal ──────────────────────────────────────────────────

@app.websocket("/ws/terminal/{name}")
async def ws_terminal(websocket: WebSocket, name: str):
    """Interactive shell via WebSocket (exec into container)."""
    await websocket.accept()
    prefix = get_domain_prefix()
    container_name = f"{prefix}-{name}"

    try:
        container = docker_client.containers.get(container_name)
    except docker.errors.NotFound:
        await websocket.send_text(f"\r\nContainer '{container_name}' not found\r\n")
        await websocket.close()
        return

    # Create exec instance with PTY
    exec_id = docker_client.api.exec_create(
        container_name, "/bin/bash", stdin=True, tty=True, stdout=True, stderr=True,
    )
    sock = docker_client.api.exec_start(exec_id, socket=True, tty=True)
    # Get the underlying socket
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
        """Serve Vue SPA — all non-API routes go to index.html."""
        file_path = FRONTEND_DIR / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(FRONTEND_DIR / "index.html")
