# OrangeScrum FrankenPHP — Quick Start Guide

## What You Have

A self-contained static binary (~560 MB) containing FrankenPHP + PHP 8.3 + Caddy + the complete OrangeScrum application. No PHP, Apache, or nginx installation required.

**Binary info:**
```bash
# Check version
bin/orangescrum version
# → FrankenPHP v1.12.1 PHP 8.3.x Caddy v2.11.x
```

---

## External Services Required

| Service          | Required? | Purpose                    |
| ---------------- | --------- | -------------------------- |
| PostgreSQL 16+   | Yes       | Database                   |
| Redis 7+         | Recommended | Cache, sessions, queue   |
| S3-compatible    | Yes       | File storage (uploads)     |
| SMTP / SendGrid  | Yes       | Email notifications        |

---

## Option A: Docker Deployment

### 1. Start Infrastructure (dev/test only)

```bash
docker compose -f docker-compose.services.yml up -d
# Starts: PostgreSQL, Redis, MinIO (S3), MailHog (email)
```

For production, use dedicated external services instead.

### 2. Configure

```bash
cp .env.example .env
nano .env
```

**Minimum required changes:**

```bash
DB_HOST=localhost              # or your PostgreSQL host
DB_PASSWORD=<strong-password>  # openssl rand -base64 24
SECURITY_SALT=<random-string>  # openssl rand -hex 32
FULL_BASE_URL=https://your-domain.com
```

### 3. Validate

```bash
./helpers/validate-env.sh
```

### 4. Deploy

```bash
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f orangescrum-app
```

### 5. Verify

```bash
curl http://localhost:8080/healthz
# → "ok"
```

### 6. Optional: Queue Worker

```bash
docker compose --profile queue up -d
```

---

## Option B: Native Deployment (No Docker)

### 1. Prerequisites

```bash
# PostgreSQL client (required for database initialization)
sudo apt install postgresql-client

# Create app extraction directory
sudo mkdir -p /app && sudo chown $USER:$USER /app
```

### 2. Configure

```bash
cp .env.example .env
nano .env
```

Same required changes as Docker above.

### 3. Validate

```bash
./helpers/validate-env.sh
```

### 4. Run

**Interactive (dev/test):**

```bash
./run.sh
```

**As a systemd service (production):**

```bash
# Install services (replace path as needed)
sed 's|@@INSTALL_DIR@@|/opt/orangescrum|g' systemd/orangescrum.service | \
    sudo tee /etc/systemd/system/orangescrum.service
sed 's|@@INSTALL_DIR@@|/opt/orangescrum|g' systemd/orangescrum-queue.service | \
    sudo tee /etc/systemd/system/orangescrum-queue.service

sudo systemctl daemon-reload
sudo systemctl enable --now orangescrum orangescrum-queue
```

### 5. Verify

```bash
curl http://localhost:8080/healthz
# → "ok"
```

---

## What Happens on Startup

```
1. Validate environment    — checks SECURITY_SALT, DB_PASSWORD, DEBUG
2. Extract embedded app    — unpacks to /app (or /tmp if /app not writable)
3. Activate config files   — copies *.example.php → *.php
4. Initialize database     — runs migrations + seeders (bin/cake init_database --seed -y)
5. Start HTTP server       — Caddy + FrankenPHP on configured port
```

Database initialization is automatic on first run. It:
- Creates all tables (migrations)
- Seeds required data (roles, permissions, system config)
- Skips seeding if data already exists (safe to restart)

---

## App Extraction Path

The embedded application extracts to a directory on startup:

| Environment | Path        | Notes                              |
| ----------- | ----------- | ---------------------------------- |
| Docker      | `/app`      | Fixed, always writable in container |
| Native      | `/app`      | Must create: `sudo mkdir -p /app && sudo chown $USER:$USER /app` |
| Native (fallback) | `/tmp/frankenphp_*` | Auto-detected if `/app` not writable |

To use a custom path:

```bash
export FRANKENPHP_APP_PATH=/opt/orangescrum/extracted
mkdir -p $FRANKENPHP_APP_PATH
./run.sh
```

---

## Health Checks

| Endpoint          | Handler          | Use for                         |
| ----------------- | ---------------- | ------------------------------- |
| `GET /healthz`    | Caddy (instant)  | Load balancer, Docker healthcheck |
| `GET /home/healthcheck` | PHP (full) | Readiness probe (checks DB)     |

---

## Useful Commands

### Docker

```bash
docker compose ps                          # Status
docker compose logs -f orangescrum-app     # Logs
docker compose restart orangescrum-app     # Restart
docker compose down                        # Stop all

# Run CakePHP commands
docker compose exec orangescrum-app /orangescrum-app/osv4-prod php-cli bin/cake.php migrations status
```

### Native

```bash
./run.sh                                   # Start (foreground)
DAEMON=true ./run.sh                       # Start (background)
./helpers/cake.sh bin/cake.php migrations status  # CakePHP CLI
./helpers/queue-worker.sh start            # Queue worker
./helpers/queue-worker.sh status           # Queue status
```

---

## Configuration Reference

### Environment Variables

See `.env.example` for all available settings. Key groups:

| Group        | Variables                        | Notes                         |
| ------------ | -------------------------------- | ----------------------------- |
| Database     | `DB_HOST`, `DB_PORT`, `DB_USERNAME`, `DB_PASSWORD`, `DB_NAME` | PostgreSQL required |
| Security     | `SECURITY_SALT`, `DEBUG`         | Salt must be unique per install |
| Cache/Queue  | `REDIS_HOST`, `CACHE_ENGINE`, `QUEUE_ENGINE` | Redis recommended  |
| Storage      | `STORAGE_ENDPOINT`, `STORAGE_ACCESS_KEY`, `STORAGE_SECRET_KEY`, `STORAGE_BUCKET` | S3-compatible |
| Email        | `EMAIL_TRANSPORT`, `SMTP_HOST` or `SENDGRID_API_KEY` | Required for notifications |
| Application  | `FULL_BASE_URL`, `APP_PORT`, `APP_BIND_IP` | URL used in emails/redirects |

### PHP Runtime Overrides

Override embedded php.ini values at runtime:

```bash
PHP_MEMORY_LIMIT=1G
PHP_UPLOAD_MAX_FILESIZE=200M
PHP_POST_MAX_SIZE=200M
PHP_MAX_EXECUTION_TIME=600
```

### Startup Control

| Variable                     | Default | Purpose                           |
| ---------------------------- | ------- | --------------------------------- |
| `RUN_MIGRATIONS`             | true    | Set `false` to skip migrations    |
| `RUN_SEEDERS`                | auto    | `true`, `false`, or `auto`        |
| `SKIP_MIGRATIONS`            | (unset) | Set to skip migrations            |
| `SKIP_SEEDERS`               | (unset) | Set to skip seeders               |
| `FRANKENPHP_EXTRACT_TIMEOUT` | 30      | Seconds to wait for extraction    |
| `FRANKENPHP_APP_PATH`        | /app    | Custom extraction path            |

---

## Reverse Proxy (Production)

Place behind nginx or Apache for TLS termination:

```nginx
server {
    listen 443 ssl http2;
    server_name app.example.com;

    ssl_certificate     /etc/letsencrypt/live/app.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/app.example.com/privkey.pem;

    client_max_body_size 200M;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Set `APP_BIND_IP=127.0.0.1` in `.env` when behind a reverse proxy.

---

## Troubleshooting

### "permission denied" on startup

```
panic: mkdir /app: permission denied
```

Fix: `sudo mkdir -p /app && sudo chown $USER:$USER /app`

Or set a custom path: `export FRANKENPHP_APP_PATH=$HOME/orangescrum-app`

### "SECURITY_SALT is still the placeholder value"

Edit `.env` and generate a real salt:

```bash
openssl rand -hex 32
```

### Database connection error

Check `DB_HOST`, `DB_PORT`, `DB_USERNAME`, `DB_PASSWORD` in `.env`. Test manually:

```bash
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USERNAME -d $DB_NAME -c "SELECT 1;"
```

### Missing tables after startup

Check if init_database ran. Run it manually:

```bash
# Docker
docker compose exec orangescrum-app /orangescrum-app/osv4-prod php-cli bin/cake.php init_database --seed -y

# Native
bin/orangescrum php-cli bin/cake.php init_database --seed -y
```

---

## Build Info

Check the build manifest for version and integrity:

```bash
cat build-manifest.json
```

Verify binary integrity:

```bash
sha256sum -c orangescrum-app/osv4-prod.sha256    # Docker dist
sha256sum -c bin/orangescrum.sha256               # Native dist
```
