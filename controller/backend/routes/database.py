"""Database routes — migrations, snapshots, restore."""

import gzip
import io
import tarfile
from datetime import datetime

import docker
from fastapi import APIRouter, Depends, HTTPException, Query

from ..helpers import (
    PROJECT_ROOT, docker_client,
    get_domain_prefix, load_registry,
    safe_sql_identifier, sanitize_container_name,
)
from ..auth import verify_credentials
from ..models import (
    DbSetupResponse, DbSnapshotResponse,
    MessageResponse, SnapshotListResponse,
)

router = APIRouter(prefix="/api", tags=["database"])


@router.post("/instances/{name}/db-setup", response_model=DbSetupResponse, summary="Run migrations and seeds")
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


@router.post("/instances/{name}/db-snapshot", response_model=DbSnapshotResponse, summary="Snapshot database")
def api_db_snapshot(name: str, user: str = Depends(verify_credentials)):
    registry = load_registry()
    if name not in registry.get("instances", {}):
        raise HTTPException(404, f"Instance '{name}' not found")
    inst = registry["instances"][name]
    db_name = safe_sql_identifier(inst.get("db_name", ""))
    db_user = inst.get("db_user", "postgres")
    prefix = get_domain_prefix()
    pg_container = f"{prefix}-postgres16"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = PROJECT_ROOT / "snapshots" / f"{db_name}_{timestamp}.sql.gz"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    try:
        pg = docker_client.containers.get(pg_container)
        exit_code, output = pg.exec_run(
            f"pg_dump -U {db_user} --no-owner --no-acl {db_name}", demux=True
        )
        if exit_code != 0:
            raise HTTPException(500, f"pg_dump failed: {(output[1] or b'').decode()}")
        with open(output_file, "wb") as f:
            f.write(gzip.compress(output[0]))
        return {
            "message": "Snapshot created",
            "file": f"snapshots/{output_file.name}",
            "size_kb": output_file.stat().st_size // 1024,
        }
    except docker.errors.NotFound:
        raise HTTPException(404, "PostgreSQL container not found")


@router.post("/instances/{name}/db-restore", response_model=MessageResponse, summary="Restore database from snapshot")
def api_db_restore(name: str, snapshot: str = Query(...), user: str = Depends(verify_credentials)):
    registry = load_registry()
    if name not in registry.get("instances", {}):
        raise HTTPException(404, f"Instance '{name}' not found")
    snapshot_path = PROJECT_ROOT / snapshot
    if not snapshot_path.exists() or not str(snapshot_path.resolve()).startswith(str(PROJECT_ROOT.resolve())):
        raise HTTPException(400, "Invalid snapshot path")
    inst = registry["instances"][name]
    db_name = safe_sql_identifier(inst.get("db_name", ""))
    db_user = inst.get("db_user", "postgres")
    prefix = get_domain_prefix()
    pg_container = f"{prefix}-postgres16"
    try:
        pg = docker_client.containers.get(pg_container)
        with open(snapshot_path, "rb") as f:
            sql_data = gzip.decompress(f.read())
        # Use put_archive to send SQL into the container, then run psql -f
        tar_stream = io.BytesIO()
        with tarfile.open(fileobj=tar_stream, mode="w") as tar:
            info = tarfile.TarInfo(name="restore.sql")
            info.size = len(sql_data)
            tar.addfile(info, io.BytesIO(sql_data))
        tar_stream.seek(0)
        pg.put_archive("/tmp", tar_stream.read())
        exit_code, output = pg.exec_run(
            f"psql -U {db_user} -d {db_name} -f /tmp/restore.sql", demux=True
        )
        pg.exec_run("rm -f /tmp/restore.sql")
        if exit_code != 0:
            stderr = (output[1] or b"").decode()[:500]
            raise HTTPException(500, f"Restore failed: {stderr}")
        return {"message": "Database restored successfully"}
    except docker.errors.NotFound:
        raise HTTPException(404, "PostgreSQL container not found")


@router.get("/snapshots", response_model=SnapshotListResponse, summary="List database snapshots")
def api_list_snapshots(user: str = Depends(verify_credentials)):
    snapshots_dir = PROJECT_ROOT / "snapshots"
    if not snapshots_dir.exists():
        return {"snapshots": []}
    files = sorted(snapshots_dir.glob("*.sql.gz"), key=lambda p: p.stat().st_mtime, reverse=True)
    return {"snapshots": [
        {"name": f.name, "path": f"snapshots/{f.name}", "size_kb": f.stat().st_size // 1024,
         "created": datetime.fromtimestamp(f.stat().st_mtime).isoformat()}
        for f in files
    ]}
