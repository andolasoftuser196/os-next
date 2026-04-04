# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A Docker-based development environment that manages dynamic, isolated app instances. Each instance gets its own container, database, Redis prefix, subdomain, and optionally a git worktree for branch isolation. A Traefik reverse proxy routes traffic by subdomain. A FastAPI+Vue controller provides a web UI for instance management.

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
| Config generator / instance manager | `generate-config.py` (Python, ~1400 lines) | Jinja2 templates → configs |
| Jinja2 templates (source of truth) | `templates/*.j2` | All generated files come from here |
| Controller backend | `controller/backend/main.py` | FastAPI (Python 3.11), Docker SDK |
| Controller frontend | `controller/frontend/` | Vue 3 + Vite SPA |
| Instance configs (generated) | `instances/{name}/` | docker-compose.yml + .env per instance |
| Instance registry | `instances/registry.json` | JSON, tracks all instances |
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
./generate-config.py <domain>                      # Generate all configs
./generate-certs.sh                                # SSL certificates
./build-images.sh all                              # Build Docker images (base, php8.3, php7.2)
docker compose up -d                               # Start base services
```

### Instance Lifecycle
```bash
./generate-config.py instance create --name <n> --type <v4|selfhosted> --subdomain <sub>
./generate-config.py instance create --name <n> --type v4 --subdomain <sub> --branch <branch>
./generate-config.py instance start --name <n>
./generate-config.py instance stop --name <n>
./generate-config.py instance destroy --name <n> --drop-db
./generate-config.py instance db-setup --name <n>  # Migrations + seeds
./generate-config.py instance logs --name <n> -f
./generate-config.py instance shell --name <n>
./generate-config.py instance list
```

### Reset (destructive)
```bash
./generate-config.py --reset    # Stops all instances, removes worktrees, clears registry
```

## How Config Generation Works

`generate-config.py` renders Jinja2 templates from `templates/` into their final locations. The domain determines a unique port offset (hash-based) to avoid conflicts. Instance creation generates per-instance compose files, env files, Traefik routes, and Apache configs, then registers the instance in `instances/registry.json`.

**Template → output mapping matters**: when changing generated files (`.env`, `docker-compose.yml`, Traefik YAML, Dockerfiles, Apache configs, `build-images.sh`, `generate-certs.sh`), edit the corresponding `templates/*.j2` template, not the generated file.

## Controller Architecture

The controller runs inside Docker. It uses the Docker SDK to manage sibling containers (not docker-in-docker). Key paths:
- `PROJECT_ROOT`: container-internal path (`/project`)
- `HOST_PROJECT_ROOT`: real host path, used for Docker volume mounts
- Auth: HTTP Basic from `CONTROLLER_USER`/`CONTROLLER_PASS` env vars
- Frontend is built at image build time and served as static files by FastAPI

## Instance Isolation Model

- **Container**: each instance runs its own Docker Compose project (prefix: domain hash + name)
- **Database**: each V4/selfhosted instance gets its own PostgreSQL database
- **Redis**: shared Redis server, isolated by key prefix per instance
- **Routing**: Traefik file watcher auto-discovers `traefik/instance-{name}.yml` (priority 100 beats V2 wildcard at 10)
- **Code**: branch instances use git worktrees at `apps/worktrees/{repo}/{branch}/`
- Reserved subdomains: `www`, `app`, `mail`, `traefik`, `storage`, `console`, `old-selfhosted`, `control`

## OrangeScrum V4 (CakePHP App)

See `apps/orangescrum-v4/.claude/CLAUDE.md` for detailed V4 guidance. Key rules:
- **Tenant safety**: all queries must be scoped by `company_id` (non-negotiable)
- **Scaffolding**: always use `cake bake` for migrations, models, controllers, commands — never handcraft framework files
- **CakePHP CLI**: run inside the app container as `appuser`, never on the host
- **SQL inspection**: use `psql` in the PostgreSQL container, not `bin/cake`
