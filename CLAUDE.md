# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

**ssmd** (Spawn, Scope, Migrate, Destroy) — a Docker-based development environment that manages dynamic, isolated app instances. Each instance gets its own container, database, Redis prefix, subdomain, and optionally a git worktree for branch isolation. A Traefik reverse proxy routes traffic by subdomain. A FastAPI+Vue controller provides a web UI for instance management.

## Architecture

```
VNC Browser (localhost:3000)
       |
  [ Traefik :80/:443 ]
       |
  +---------+---------+---------+---------+
  v2.*      v4.*   selfhosted.*  control.*
  PHP 7.2   PHP 8.3  PHP 8.3    FastAPI
  MySQL     PostgreSQL           + Vue 3
  (static)  (dynamic instances)
```

**Base services** (always running): Traefik, PostgreSQL 16, MySQL 8, Redis, Memcached, MailHog, dnsmasq, VNC Browser, Controller.

**Dynamic instances**: Created on demand via CLI or web UI. Each is a separate Docker Compose project with isolated resources.

## Key Components

| Component | Location | Tech |
|-----------|----------|------|
| CLI entry point | `ssmd` (alias: `generate-config.py`) | Delegates to `lib/` modules |
| Config generation | `lib/config_generator.py` | Jinja2 template rendering, backups, reset |
| Instance management | `lib/instance_manager.py` | Create, destroy, start, stop, list |
| Database operations | `lib/database.py` | Migrations, snapshots, restore |
| Instance registry | `lib/registry.py` → `instances/registry.db` | SQLite (WAL mode), auto-migrates from JSON |
| Jinja2 templates (source of truth) | `templates/*.j2` | All generated files come from here |
| Controller backend | `controller/backend/` | FastAPI (Python 3.11), modular routes |
| Controller frontend | `controller/frontend/` | Vue 3 + Vite SPA |
| Instance configs (generated) | `instances/{name}/` | docker-compose.yml + .env per instance |
| Traefik routing (generated) | `traefik/instance-{name}.yml` | Auto-discovered by Traefik file watcher |
| Container entrypoints | `entrypoints/` | Bash init scripts |
| OrangeScrum V4 | `apps/orangescrum-v4/` | CakePHP 4.6 + PostgreSQL |
| Selfhosted variant | `apps/durango-pg/` | CakePHP 4.6 + PostgreSQL |
| V2 (legacy) | `apps/orangescrum/` | PHP 7.2 + MySQL |
| Git worktrees | `apps/worktrees/{repo}/{branch}/` | Created for branch-specific instances |
| FrankenPHP cloud builder | `cloud-builder/` | Standalone binary builds |

## Common Commands

### Setup
```bash
./setup-venv.sh                                    # Create Python venv
source .venv/bin/activate
./ssmd <domain>                      # Generate all configs
./generate-certs.sh                                # SSL certificates
./build-images.sh all                              # Build Docker images (base, php8.3, php7.2)
docker compose up -d                               # Start base services
```

### Instance Lifecycle
```bash
./ssmd instance create --name <n> --type <v4|selfhosted> --subdomain <sub>
./ssmd instance create --name <n> --type v4 --subdomain <sub> --branch <branch>
./ssmd instance start --name <n>
./ssmd instance stop --name <n>
./ssmd instance destroy --name <n> --drop-db
./ssmd instance db-setup --name <n>  # Migrations + seeds
./ssmd instance db-snapshot --name <n>  # Snapshot DB to snapshots/
./ssmd instance db-restore --name <n> --snapshot <file>  # Restore snapshot
./ssmd instance create --name <n> --type v4 --subdomain <sub> --from-snapshot <file>
./ssmd instance logs --name <n> -f
./ssmd instance shell --name <n>
./ssmd instance list
```

### Reset (destructive)
```bash
./ssmd --reset    # Stops all instances, removes worktrees, clears registry
```

## How Config Generation Works

`ssmd` is the CLI entry point (`generate-config.py` is a backward-compatible alias) that delegates to modules in `lib/`:

- `lib/config_generator.py` — renders Jinja2 templates from `templates/` into their final locations
- `lib/instance_manager.py` — instance create/destroy/start/stop/list/logs/shell
- `lib/database.py` — db-setup (migrations + seeds), db-snapshot, db-restore
- `lib/registry.py` — SQLite-backed instance registry (`instances/registry.db`, WAL mode, atomic transactions). Auto-migrates from legacy `registry.json` on first load.
- `lib/output.py` — terminal colors and formatting

The domain determines a unique port offset (hash-based) to avoid conflicts. Instance creation generates per-instance compose files, env files, Traefik routes, and Apache configs, then registers the instance in the SQLite registry.

**Template → output mapping matters**: when changing generated files (`.env`, `docker-compose.yml`, Traefik YAML, Dockerfiles, Apache configs, `build-images.sh`, `generate-certs.sh`), edit the corresponding `templates/*.j2` template, not the generated file.

## Controller Architecture

The controller runs inside Docker. It uses the Docker SDK to manage sibling containers (not docker-in-docker). The backend is modular:

- `controller/backend/main.py` — FastAPI app setup, CORS, router wiring, frontend serving
- `controller/backend/auth.py` — HTTP Basic auth dependency
- `controller/backend/models.py` — Pydantic request/response models
- `controller/backend/helpers.py` — Docker client, SQLite registry, domain detection, sanitization
- `controller/backend/routes/instances.py` — CRUD, start/stop
- `controller/backend/routes/database.py` — db-setup, snapshot, restore
- `controller/backend/routes/monitoring.py` — status, stats, logs
- `controller/backend/routes/websockets.py` — live log streaming, web terminal

Key paths and design:

- `PROJECT_ROOT`: container-internal path (`/project`)
- `HOST_PROJECT_ROOT`: real host path, used for Docker volume mounts and git worktree metadata rewriting
- Controller runs as non-root `appuser` with Docker socket access via `docker_host` group
- Auth: HTTP Basic from `CONTROLLER_USER`/`CONTROLLER_PASS` env vars
- Frontend is built at image build time and served as static files by FastAPI
- When creating worktrees, git metadata is rewritten from container paths (`/project/...`) to host paths so `git worktree list` works correctly on the host

## Instance Isolation Model

- **Container**: each instance runs its own Docker Compose project (prefix: domain hash + name)
- **Database**: each V4/selfhosted instance gets its own PostgreSQL database
- **Redis**: shared Redis server, isolated by key prefix per instance
- **Routing**: Traefik file watcher auto-discovers `traefik/instance-{name}.yml` (priority 100 beats V2 wildcard at 10)
- **Code**: branch instances use git worktrees at `apps/worktrees/{repo}/{branch-dir}/` (only created when `--branch` is explicitly provided; without it, instances share the source repo directly)
- **Dependencies**: auto `composer install` on first boot if vendor/ missing; `composer.lock` is copied from source repo into worktrees to avoid slow `composer update`; shared download cache at `.composer-cache/` (mounted at `/home/appuser/.cache/composer`)
- **Logs/tmp**: instance `logs/` and `tmp/` use Docker-managed volumes (not written into the source/worktree directory)
- **Config bootstrap**: entrypoint copies `app_local.example.php` → `app_local.php` if missing (handles fresh worktrees where composer post-install hooks created the wrong config)
- **Health**: instance containers have curl-based healthchecks; controller UI shows health badges
- **Env layers**: `instances/shared.env` (project-wide) + `instances/{name}/.env` (unique) + optional `instances/{name}/overrides.env`
- **DB snapshots**: `snapshots/*.sql.gz` — pg_dump/restore for fast instance provisioning
- Reserved subdomains: `www`, `app`, `mail`, `traefik`, `storage`, `console`, `old-selfhosted`, `control`

## Testing

```bash
source .venv/bin/activate
python -m pytest tests/ -v                                    # Full suite (requires base services running)
python -m pytest tests/test_controller_api.py::TestBranchIsolation -v  # Branch isolation only
```

Tests cover: system health, instance CRUD lifecycle, branch worktree isolation (create, code isolation, registry, cleanup), and edge cases. Tests run against the live controller API (`http://127.0.0.1:8900`).

## OrangeScrum V4 (CakePHP App)

See `apps/orangescrum-v4/.claude/CLAUDE.md` for detailed V4 guidance. Key rules:
- **Tenant safety**: all queries must be scoped by `company_id` (non-negotiable)
- **Scaffolding**: always use `cake bake` for migrations, models, controllers, commands — never handcraft framework files
- **CakePHP CLI**: run inside the app container as `appuser`, never on the host
- **SQL inspection**: use `psql` in the PostgreSQL container, not `bin/cake`
