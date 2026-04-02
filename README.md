# Dev Environment — Dynamic Multi-App Docker Setup

Docker-based developer environment with dynamic instance management. Run multiple app versions and branches simultaneously, each with its own subdomain, database, and container.

## Architecture

```
                    VNC Browser (http://localhost:3000)
                           |
                      [ Traefik :80/:443 ]
                           |
        +------------------+------------------+------------------+
        |                  |                  |                  |
   app.domain         v4.domain        selfhosted.domain   control.domain
   www.domain         next.domain      sh-client1.domain
   *.domain           fix-123.domain
        |                  |                  |                  |
   [ V2 Static ]    [ Dynamic Instances ]                [ Controller ]
   PHP 7.2+MySQL    PHP 8.3+Node+PostgreSQL              FastAPI+Vue
                    (one per branch/feature)
```

**Base services** (always running): Traefik, PostgreSQL 16, MySQL 8, Redis, Memcached, MailHog, DNS, Browser, Controller

**Dynamic instances** (on demand): Each gets its own container, database, Redis prefix, Traefik route, and optionally its own git branch via worktrees.

## Quick Start

```bash
# 1. Generate configs for your domain
./generate-config.py user196.online

# 2. Generate SSL certificates
./generate-certs.sh

# 3. Build Docker images
./build-images.sh all

# 4. Start base services
docker compose up -d

# 5. Create your first instances
./generate-config.py instance create --name v4-main --type v4 --subdomain v4
./generate-config.py instance create --name sh-main --type selfhosted --subdomain selfhosted

# 6. Access via VNC browser
# Open http://localhost:3000 in your browser
```

Or use the one-command setup:

```bash
./setup.sh user196.online
```

## Instance Management

### Create

```bash
# V4 instance on default source (apps/orangescrum-v4)
./generate-config.py instance create --name v4-main --type v4 --subdomain v4

# Selfhosted instance
./generate-config.py instance create --name sh-main --type selfhosted --subdomain selfhosted

# Instance on a specific branch (creates a git worktree)
./generate-config.py instance create --name v4-kanban --type v4 \
  --subdomain kanban --branch enhance/kanban-ui

# Instance from a custom source path
./generate-config.py instance create --name v4-custom --type v4 \
  --subdomain custom --source ./apps/my-fork
```

### Lifecycle

```bash
./generate-config.py instance list                        # List all instances
./generate-config.py instance stop --name v4-kanban       # Stop
./generate-config.py instance start --name v4-kanban      # Start
./generate-config.py instance destroy --name v4-kanban --drop-db  # Destroy + drop DB
./generate-config.py instance db-setup --name v4-main     # Run migrations & seeds
./generate-config.py instance logs --name v4-main -f      # Stream logs
./generate-config.py instance shell --name v4-main        # Shell into container
```

### Web Controller

Full management UI at `https://control.<domain>`:

- Dashboard with service status and resource usage
- Create/start/stop/destroy instances
- Run database migrations
- Live log streaming
- Web terminal (shell into any container)

Credentials are in `.env` (`CONTROLLER_USER` / `CONTROLLER_PASS`).

## Domain Routing

| Subdomain | Routes to |
|-----------|-----------|
| `www.<domain>` | V2 landing page |
| `app.<domain>` | V2 inner app |
| `old-selfhosted.<domain>` | V2 selfhosted |
| `*.<domain>` | V2 tenant wildcard (catch-all, lowest priority) |
| `v4.<domain>` | Dynamic V4 instance |
| `next.<domain>` | Dynamic V4 instance (feature branch) |
| `selfhosted.<domain>` | Dynamic selfhosted instance |
| `mail.<domain>` | MailHog email testing |
| `traefik.<domain>` | Traefik dashboard |
| `control.<domain>` | Controller web UI |

Routing uses Traefik priority: specific instance routes (100) always win over the V2 wildcard (10). New instances are auto-discovered via Traefik's file watcher.

## Branch Workflow

Run multiple branches simultaneously, each with its own isolated environment:

```bash
# Main branch — shared codebase
./generate-config.py instance create --name v4-main --type v4 --subdomain v4

# Feature branch — own worktree, DB, subdomain
./generate-config.py instance create --name v4-kanban --type v4 \
  --subdomain kanban --branch enhance/kanban-ui

# Bugfix branch
./generate-config.py instance create --name v4-fix --type v4 \
  --subdomain fix --branch fix/issue-456

# Each accessible at its own URL:
#   https://v4.user196.online       → main
#   https://kanban.user196.online   → enhance/kanban-ui
#   https://fix.user196.online      → fix/issue-456
```

Worktrees are stored at `apps/worktrees/<repo>/<branch>/` and cleaned up on destroy.

## Access Points

All apps are accessed through the VNC browser at **http://localhost:3000**.

Inside the browser, navigate to any subdomain over HTTPS. The self-signed certificate is auto-trusted via dnsmasq + certutil.

Host-exposed ports for IDE/database tools (bound to 127.0.0.1):

| Service | Port | Notes |
|---------|------|-------|
| PostgreSQL | See `.env` | Shared by all V4/selfhosted instances |
| MySQL | See `.env` | V2 only |
| Redis | See `.env` | Shared, isolated by key prefix |
| VNC Browser | 3000 | Primary access method |

Exact port values are auto-generated per domain (unique offset to avoid conflicts). Check `.env` after running `generate-config.py`.

## File Structure

```
├── apps/                          # Application source code
│   ├── orangescrum-v4/            # V4 app repo
│   ├── durango-pg/                # Selfhosted app repo
│   ├── orangescrum/               # V2 app
│   └── worktrees/                 # Git worktrees (per-branch instances)
│       ├── orangescrum-v4/
│       │   └── enhance-kanban-ui/ # Worktree for branch
│       └── durango-pg/
├── instances/                     # Dynamic instance configs (generated)
│   ├── registry.json              # Instance registry
│   ├── v4-main/                   # Per-instance compose + .env
│   └── sh-main/
├── traefik/                       # Traefik routing configs
│   ├── dynamic.yml                # Base routes (V2, mail, etc.)
│   ├── instance-v4-main.yml       # Auto-generated per instance
│   └── instance-sh-main.yml
├── templates/                     # Jinja2 templates (source of truth)
├── controller/                    # Web controller (FastAPI + Vue)
│   ├── backend/                   # Python API
│   └── frontend/                  # Vue 3 SPA
├── config/                        # Apache/PHP/dnsmasq configs
├── certs/                         # SSL certificates
├── entrypoints/                   # Container init scripts
├── generate-config.py             # Config generator + instance manager
├── setup.sh                       # One-command setup
└── build-images.sh                # Docker image builder
```

## Docker Images

| Image | Size | Contents |
|-------|------|----------|
| `orangescrum-base` | ~380 MB | Ubuntu 22.04, Apache, PHP PPA |
| `orangescrum-php8.3` | ~714 MB | PHP 8.3, Node 20, PostgreSQL client, Composer |
| `orangescrum-php7.2` | ~558 MB | PHP 7.2, MySQL client, Composer 2.2 |

Images are optimized: single apt layers, proper cleanup, no unnecessary packages. Code is volume-mounted, not baked in.

## Configuration

### Regenerate configs (preserves instances)

```bash
./generate-config.py user196.online
```

### Full reset (removes everything)

```bash
./generate-config.py --reset
```

This stops all instances, removes worktrees, clears the registry, and deletes all generated files.

### HTTPS

HTTPS is enabled by default. Disable with:

```bash
./generate-config.py user196.online --no-https
```

### Interactive mode

```bash
./generate-config.py user196.online -i
```

Prompts for which services to enable (V2, Redis vs Memcached, MailHog, MinIO).

## Troubleshooting

```bash
# Check service status
docker compose ps

# Check instance container logs
./generate-config.py instance logs --name v4-main -f

# Shell into a container
./generate-config.py instance shell --name v4-main

# Rebuild images after Dockerfile changes
./build-images.sh all

# Regenerate SSL certificates
./generate-certs.sh

# Restart a base service
docker compose restart traefik

# Browser can't resolve domains
docker compose restart dns browser
```
