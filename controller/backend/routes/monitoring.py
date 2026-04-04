"""Monitoring routes — status, stats, logs."""

import docker
from fastapi import APIRouter, Depends, HTTPException, Query

from ..helpers import (
    _get_base_service_names, docker_client,
    get_domain, get_domain_prefix, detect_https,
    get_container_status, get_container_stats,
    sanitize_container_name,
)
from ..auth import verify_credentials
from ..models import (
    ContainerStatsResponse, LogsResponse, StatusResponse,
)

router = APIRouter(prefix="/api", tags=["monitoring"])


@router.get("/status", response_model=StatusResponse, summary="System status")
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


@router.get("/instances/{name}/logs", response_model=LogsResponse, summary="Get recent container logs")
def api_instance_logs(name: str, tail: int = Query(100, ge=1, le=5000), user: str = Depends(verify_credentials)):
    """Returns the last N lines of container logs (non-streaming). Use the WebSocket endpoint for live streaming."""
    container_name = sanitize_container_name(name)
    try:
        container = docker_client.containers.get(container_name)
    except docker.errors.NotFound:
        raise HTTPException(404, f"Container '{container_name}' not running")
    logs = container.logs(tail=tail, timestamps=True).decode(errors="replace")
    return {"lines": logs.splitlines(), "container_name": container_name, "tail": tail}


@router.get("/instances/{name}/stats", response_model=ContainerStatsResponse, summary="Instance resource usage")
def api_instance_stats(name: str, user: str = Depends(verify_credentials)):
    container_name = sanitize_container_name(name)
    return get_container_stats(container_name)


@router.get("/services/stats", summary="Base services resource usage")
def api_services_stats(user: str = Depends(verify_credentials)):
    prefix = get_domain_prefix()
    services = list(_get_base_service_names() - {"controller"})
    return {svc: get_container_stats(f"{prefix}-{svc}") for svc in services}
