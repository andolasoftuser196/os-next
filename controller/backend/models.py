"""Pydantic request/response models for the Dev Controller API."""

import re
from typing import Optional

from pydantic import BaseModel, field_validator

# Strict validation patterns
NAME_PATTERN = re.compile(r"^[a-z0-9]([a-z0-9-]{0,30}[a-z0-9])?$")
SUBDOMAIN_PATTERN = re.compile(r"^[a-z0-9]([a-z0-9-]{0,30}[a-z0-9])?$")
BRANCH_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_./-]{0,100}[a-zA-Z0-9]$|^[a-zA-Z0-9]$")


# ─── Request Models ─────────────────────────────────────────────────────────

class CreateInstanceRequest(BaseModel):
    name: str
    type: str
    subdomain: Optional[str] = None
    source: Optional[str] = None
    branch: Optional[str] = None
    from_snapshot: Optional[str] = None
    restricted: bool = False

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
        if ".." in v or v.startswith("/"):
            raise ValueError("Source must be a relative path without '..'")
        return v

    @field_validator("branch")
    @classmethod
    def validate_branch(cls, v):
        if v is None:
            return v
        if ".." in v or not BRANCH_PATTERN.match(v):
            raise ValueError("Invalid branch name")
        return v

    @field_validator("from_snapshot")
    @classmethod
    def validate_from_snapshot(cls, v):
        if v is None:
            return v
        if ".." in v or not v.startswith("snapshots/") or not v.endswith(".sql.gz"):
            raise ValueError("Snapshot must be a path like snapshots/<name>.sql.gz")
        return v


# ─── Response Models ─────────────────────────────────────────────────────────

class ContainerStatusInfo(BaseModel):
    status: str
    health: str
    started_at: str
    image: str

class StatusResponse(BaseModel):
    domain: Optional[str]
    domain_prefix: str
    https: bool
    protocol: str
    services: dict[str, ContainerStatusInfo]

class InstanceInfo(BaseModel):
    name: str
    type: str
    subdomain: str
    url: str
    db_name: str
    container_name: str
    container_status: str
    container_health: str
    created_at: str
    source_path: str
    branch: str
    worktree_path: str
    restricted: bool

class InstanceListResponse(BaseModel):
    domain: Optional[str]
    instances: list[InstanceInfo]

class MessageResponse(BaseModel):
    message: str

class CreateInstanceResponse(BaseModel):
    message: str
    url: str

class DbSetupResponse(BaseModel):
    migrations: str
    seeds: str

class DbSnapshotResponse(BaseModel):
    message: str
    file: str
    size_kb: int

class SnapshotInfo(BaseModel):
    name: str
    path: str
    size_kb: int
    created: str

class SnapshotListResponse(BaseModel):
    snapshots: list[SnapshotInfo]

class ContainerStatsResponse(BaseModel):
    cpu_percent: float
    mem_usage_mb: float
    mem_limit_mb: float
    mem_percent: float

class LogsResponse(BaseModel):
    lines: list[str]
    container_name: str
    tail: int
