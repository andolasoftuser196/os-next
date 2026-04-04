"""Instance CRUD routes — create, destroy, start, stop, list."""

import hashlib
import os
import secrets
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from jinja2 import Environment, FileSystemLoader

from ..helpers import (
    HOST_PROJECT_ROOT, INSTANCES_DIR, PROJECT_ROOT, RESERVED_SUBDOMAINS,
    TEMPLATES_DIR, TRAEFIK_DIR, DEFAULT_SOURCE_PATHS,
    docker_client, get_domain, get_domain_prefix, detect_https, detect_cache_engine,
    load_registry, save_registry, safe_sql_identifier, validate_source_path,
    get_container_status,
)


def _compose_cmd(compose_file: str, *args: str) -> list[str]:
    return ["docker", "compose", "-f", compose_file, *args]
from ..auth import verify_credentials
from ..models import (
    CreateInstanceRequest, CreateInstanceResponse,
    InstanceListResponse, MessageResponse,
)

router = APIRouter(prefix="/api", tags=["instances"])


@router.get("/instances", response_model=InstanceListResponse, summary="List all instances")
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
            "container_health": s["health"],
            "created_at": inst.get("created_at", ""),
            "source_path": inst.get("source_path", ""),
            "branch": inst.get("branch", ""),
            "worktree_path": inst.get("worktree_path", ""),
            "restricted": inst.get("restricted", False),
        })
    return {"domain": d, "instances": instances}


@router.post("/instances", response_model=CreateInstanceResponse, summary="Create a new instance")
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
    validate_source_path(source)

    # If branch is specified, create a git worktree under apps/worktrees/<repo>/<branch>
    branch = req.branch or None
    worktree_path = None
    if branch:
        repo_name = Path(source).name
        branch_dir = branch.replace("/", "-")
        worktree_dir = PROJECT_ROOT / "apps" / "worktrees" / repo_name
        worktree_dir.mkdir(parents=True, exist_ok=True)
        worktree_path = worktree_dir / branch_dir

        if worktree_path.exists():
            raise HTTPException(409, f"Worktree path '{worktree_path}' already exists")

        source_repo = (PROJECT_ROOT / source).resolve()
        wt_abs = str(worktree_path.resolve())
        subprocess.run(["git", "fetch", "--all"], cwd=str(source_repo), capture_output=True, text=True)
        result = subprocess.run(
            ["git", "worktree", "add", wt_abs, branch],
            cwd=str(source_repo), capture_output=True, text=True,
        )
        if result.returncode != 0:
            result = subprocess.run(
                ["git", "worktree", "add", "-b", branch, wt_abs, "main"],
                cwd=str(source_repo), capture_output=True, text=True,
            )
            if result.returncode != 0:
                raise HTTPException(500, f"Could not create worktree: {result.stderr.strip()}")

        # Git records absolute container paths (/project/...) in worktree metadata.
        # Rewrite them to host paths so `git worktree list` works on the host.
        container_prefix = str(PROJECT_ROOT)
        host_prefix = HOST_PROJECT_ROOT
        if container_prefix != host_prefix:
            # <repo>/.git/worktrees/<name>/gitdir → points to worktree .git
            wt_meta_dir = source_repo / ".git" / "worktrees" / branch_dir
            gitdir_file = wt_meta_dir / "gitdir"
            if gitdir_file.exists():
                gitdir_file.write_text(
                    gitdir_file.read_text().replace(container_prefix, host_prefix)
                )
            # <worktree>/.git → points back to repo .git/worktrees/<name>
            wt_git_file = worktree_path / ".git"
            if wt_git_file.exists():
                wt_git_file.write_text(
                    wt_git_file.read_text().replace(container_prefix, host_prefix)
                )

        # Copy composer.lock so worktree uses `composer install` (fast) not `composer update`
        lock_file = source_repo / "composer.lock"
        if lock_file.exists():
            shutil.copy2(str(lock_file), str(worktree_path / "composer.lock"))

        source = str(worktree_path.relative_to(PROJECT_ROOT))

    source_abs = str((PROJECT_ROOT / source).resolve())

    db_name = safe_sql_identifier(f"{instance_type}_{name}")
    db_user = 'postgres'
    db_password = 'postgres'

    security_salt = hashlib.sha256(secrets.token_bytes(64)).hexdigest()

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        trim_blocks=True, lstrip_blocks=True, keep_trailing_newline=True,
    )
    ctx = {
        "instance_name": name, "instance_type": instance_type,
        "instance_subdomain": subdomain, "domain": d,
        "domain_prefix": prefix, "enable_https": enable_https,
        "source_path": source_abs.replace(str(PROJECT_ROOT), HOST_PROJECT_ROOT),
        "project_root": HOST_PROJECT_ROOT,
        "db_name": db_name, "db_user": db_user, "db_password": db_password,
        "security_salt": security_salt, "cache_engine": detect_cache_engine(),
        "generated_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "node_version": "20",
    }

    # Ensure shared.env exists
    shared_env = INSTANCES_DIR / "shared.env"
    if not shared_env.exists():
        shared_ctx = {
            "cache_engine": detect_cache_engine(),
            "generated_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        shared_env.write_text(env.get_template("shared.env.j2").render(shared_ctx))

    inst_dir = INSTANCES_DIR / name
    inst_dir.mkdir(parents=True, exist_ok=True)
    (inst_dir / ".env").write_text(env.get_template("instance.env.j2").render(ctx))
    (inst_dir / "docker-compose.yml").write_text(env.get_template("instance-docker-compose.yml.j2").render(ctx))
    (TRAEFIK_DIR / f"instance-{name}.yml").write_text(env.get_template("instance-traefik.yml.j2").render(ctx))

    # Create database
    pg_container = f"{prefix}-postgres16"
    try:
        pg = docker_client.containers.get(pg_container)
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
            _compose_cmd(str(inst_dir / "docker-compose.yml"), "up", "-d"),
            check=True, capture_output=True, text=True,
        )
    except Exception:
        pass

    registry["domain"] = d
    inst_record = {
        "type": instance_type, "subdomain": subdomain,
        "db_name": db_name, "db_user": db_user,
        "container_name": f"{prefix}-{name}",
        "source_path": source, "created_at": datetime.now().isoformat(),
        "status": "running", "restricted": req.restricted,
    }
    if branch:
        inst_record["branch"] = branch
        inst_record["worktree_path"] = str(worktree_path.relative_to(PROJECT_ROOT))
    registry.setdefault("instances", {})[name] = inst_record
    save_registry(registry)

    protocol = "https" if enable_https else "http"
    return {"message": f"Instance '{name}' created", "url": f"{protocol}://{subdomain}.{d}"}


@router.delete("/instances/{name}", response_model=MessageResponse, summary="Destroy an instance")
def api_destroy_instance(name: str, drop_db: bool = Query(False), user: str = Depends(verify_credentials)):
    registry = load_registry()
    if name not in registry.get("instances", {}):
        raise HTTPException(404, f"Instance '{name}' not found")

    inst = registry["instances"][name]
    prefix = get_domain_prefix()

    inst_dir = INSTANCES_DIR / name
    if not str(inst_dir.resolve()).startswith(str(INSTANCES_DIR.resolve())):
        raise HTTPException(400, "Invalid instance name")

    compose_file = inst_dir / "docker-compose.yml"
    if compose_file.exists():
        try:
            subprocess.run(
                _compose_cmd(str(compose_file), "down"),
                check=True, capture_output=True, text=True,
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

    worktree_path = inst.get("worktree_path")
    if worktree_path:
        wt = Path(worktree_path)
        full_wt = PROJECT_ROOT / wt
        base_source = DEFAULT_SOURCE_PATHS.get(inst["type"], DEFAULT_SOURCE_PATHS["v4"])
        source_repo = str((PROJECT_ROOT / base_source).resolve())
        # Worktree metadata uses host paths; pass host path to git worktree remove
        host_wt = str(Path(HOST_PROJECT_ROOT) / wt)
        try:
            subprocess.run(
                ["git", "worktree", "remove", "--force", host_wt],
                cwd=source_repo, check=True, capture_output=True, text=True,
            )
        except Exception:
            if full_wt.exists():
                shutil.rmtree(full_wt, ignore_errors=True)
        # Clean up root-owned files containers may have created
        if full_wt.exists():
            try:
                shutil.rmtree(full_wt)
            except PermissionError:
                subprocess.run(
                    ["docker", "run", "--rm", "-v", f"{full_wt.resolve()}:/cleanup",
                     "alpine", "sh", "-c", "rm -rf /cleanup/*"],
                    capture_output=True, text=True,
                )
                shutil.rmtree(full_wt, ignore_errors=True)
        # Prune stale worktree references
        subprocess.run(["git", "worktree", "prune"], cwd=source_repo, capture_output=True, text=True)

    if inst_dir.exists():
        shutil.rmtree(inst_dir)

    del registry["instances"][name]
    save_registry(registry)
    return {"message": f"Instance '{name}' destroyed"}


@router.post("/instances/{name}/start", response_model=MessageResponse, summary="Start an instance")
def api_start_instance(name: str, user: str = Depends(verify_credentials)):
    registry = load_registry()
    if name not in registry.get("instances", {}):
        raise HTTPException(404, f"Instance '{name}' not found")
    inst_dir = INSTANCES_DIR / name
    compose_file = inst_dir / "docker-compose.yml"
    if not compose_file.exists():
        raise HTTPException(404, "Compose file not found")
    result = subprocess.run(
        _compose_cmd(str(compose_file), "up", "-d"),
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "Unknown error").strip()
        raise HTTPException(500, f"Failed to start instance: {detail}")
    registry["instances"][name]["status"] = "running"
    save_registry(registry)
    return {"message": f"Instance '{name}' started"}


@router.post("/instances/{name}/stop", response_model=MessageResponse, summary="Stop an instance")
def api_stop_instance(name: str, user: str = Depends(verify_credentials)):
    registry = load_registry()
    if name not in registry.get("instances", {}):
        raise HTTPException(404, f"Instance '{name}' not found")
    inst_dir = INSTANCES_DIR / name
    compose_file = inst_dir / "docker-compose.yml"
    if not compose_file.exists():
        raise HTTPException(404, "Compose file not found")
    result = subprocess.run(
        _compose_cmd(str(compose_file), "down"),
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "Unknown error").strip()
        raise HTTPException(500, f"Failed to stop instance: {detail}")
    registry["instances"][name]["status"] = "stopped"
    save_registry(registry)
    return {"message": f"Instance '{name}' stopped"}
