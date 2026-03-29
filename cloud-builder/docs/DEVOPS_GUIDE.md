# DevOps Guide — OrangeScrum FrankenPHP Deployment

## What You Receive

A dist package (either `dist-docker/` or `dist-native/`) containing a self-contained FrankenPHP static binary with the entire OrangeScrum V4 application embedded. No PHP, Apache, or nginx needed on the target host.

### Verify Integrity Before Deploying

```bash
# On the build machine (or after scp to production)
python3 build.py --verify dist/20260329_143000/dist-docker

# Or manually
cd dist-docker
sha256sum -c orangescrum-app/osv4-prod.sha256
cat build-manifest.json
```

---

## External Dependencies

The binary is fully self-contained. These services must be provisioned externally:

| Service | Required | Purpose |
|---------|----------|---------|
| PostgreSQL 16+ | Yes | Primary database |
| Redis 7+ | Recommended | Cache, sessions, queue |
| S3-compatible storage | Yes | File uploads, attachments |
| Email (SendGrid or SMTP) | Yes | Notifications |
| Reverse proxy (nginx/Apache) | Recommended | TLS termination, rate limiting |

---

## Docker Deployment

### 1. Transfer Package

```bash
scp -r dist/20260329_143000/dist-docker user@prod:/opt/orangescrum
```

### 2. Configure

```bash
cd /opt/orangescrum
cp .env.example .env
nano .env
```

**Required settings** (all others have safe defaults):

```bash
# Database
DB_HOST=your-postgres-host
DB_PORT=5432
DB_USERNAME=orangescrum
DB_PASSWORD=<openssl rand -base64 24>
DB_NAME=orangescrum

# Security (MUST change — app refuses to start with placeholders)
SECURITY_SALT=<openssl rand -hex 32 | sha256sum | cut -d' ' -f1>

# Redis
REDIS_HOST=your-redis-host
REDIS_PORT=6379

# S3 Storage
STORAGE_ENDPOINT=https://s3.amazonaws.com
STORAGE_ACCESS_KEY=<your-key>
STORAGE_SECRET_KEY=<your-secret>
STORAGE_BUCKET=orangescrum-files

# Application URL
FULL_BASE_URL=https://your-domain.com

# Email
EMAIL_TRANSPORT=sendgrid
SENDGRID_API_KEY=SG.xxx
FROM_EMAIL=noreply@your-domain.com
```

### 3. Validate Configuration

```bash
./helpers/validate-env.sh
```

This checks:

- `SECURITY_SALT` is set, not default, >= 32 chars
- `DB_PASSWORD` is set, not default, >= 16 chars
- `DEBUG=false`
- All required database/redis/storage vars configured

### 4. Deploy

```bash
# Start application
docker compose up -d orangescrum-app

# Optional: start queue worker for background jobs
docker compose --profile queue up -d

# Check status
docker compose ps

# View logs
docker compose logs -f orangescrum-app
```

### 5. Verify

```bash
# Caddy-native health check (no PHP overhead)
curl http://localhost:8080/healthz
# → "ok"

# Application-level health check (verifies PHP + app)
curl http://localhost:8080/home/healthcheck
```

### 6. Reverse Proxy (nginx example)

```nginx
server {
    listen 443 ssl http2;
    server_name app.your-domain.com;

    ssl_certificate     /etc/letsencrypt/live/app.your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/app.your-domain.com/privkey.pem;

    client_max_body_size 200M;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

server {
    listen 80;
    server_name app.your-domain.com;
    return 301 https://$server_name$request_uri;
}
```

### Resource Limits

Default in docker-compose.yaml:

| Service | CPU | Memory |
|---------|-----|--------|
| orangescrum-app | 2 cores / 0.5 reserved | 2 GB / 512 MB reserved |
| queue-worker | 1 core / 0.25 reserved | 1 GB / 256 MB reserved |

### Infrastructure Services (Dev/Test Only)

For local testing without external services:

```bash
docker compose -f docker-compose.services.yml up -d
# Starts: PostgreSQL, Redis, MinIO, MailHog
```

**Do not use in production** — provision dedicated external services.

---

## Native Deployment (No Docker)

### 1. Transfer Package

```bash
scp -r dist/20260329_143000/dist-native user@prod:/opt/orangescrum
```

### 2. System Prerequisites

```bash
# Create application user
sudo useradd -r -m -d /opt/orangescrum -s /bin/bash orangescrum

# Install PostgreSQL client (required for auto-seeding)
sudo apt install postgresql-client

# Directory permissions
sudo chown -R orangescrum:orangescrum /opt/orangescrum
```

### 3. Configure

```bash
cd /opt/orangescrum
cp .env.example .env
nano .env    # Same required settings as Docker section above
./helpers/validate-env.sh
```

### 4. Start Application

**Interactive (for testing):**

```bash
./run.sh
```

**As systemd service (production):**

```bash
# Install service files (replace @@INSTALL_DIR@@ with actual path)
sed 's|@@INSTALL_DIR@@|/opt/orangescrum|g' systemd/orangescrum.service | \
    sudo tee /etc/systemd/system/orangescrum.service

sed 's|@@INSTALL_DIR@@|/opt/orangescrum|g' systemd/orangescrum-queue.service | \
    sudo tee /etc/systemd/system/orangescrum-queue.service

sudo systemctl daemon-reload
sudo systemctl enable orangescrum orangescrum-queue
sudo systemctl start orangescrum orangescrum-queue
```

### 5. Verify

```bash
sudo systemctl status orangescrum
curl http://localhost:8080/healthz
```

### 6. Recurring Tasks (Cron)

The cron job runs every 30 minutes. For native deployment, add to the orangescrum user's crontab:

```bash
sudo -u orangescrum crontab -e
```

Add:

```cron
*/30 * * * * [ -f /tmp/.frankenphp_app_path ] && EXTRACTED_APP=$(cat /tmp/.frankenphp_app_path) && [ -d "$EXTRACTED_APP" ] && cd "$EXTRACTED_APP" && /opt/orangescrum/bin/orangescrum php-cli bin/cake.php recurring_task >> /var/log/orangescrum/cron.log 2>&1
```

### 7. Log Rotation

```bash
# /etc/logrotate.d/orangescrum
/var/log/orangescrum/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 orangescrum orangescrum
}
```

---

## Startup Lifecycle

Both Docker and Native follow the same sequence (via `lib/frankenphp-common.sh`):

```
1. validate_production_env()
   ├─ SECURITY_SALT not placeholder, >= 32 chars
   ├─ DB_PASSWORD not placeholder, >= 16 chars
   └─ DEBUG=false
   → Exits immediately on fatal errors

2. apply_php_overrides()
   └─ Writes /tmp/php-overrides/99-overrides.ini from PHP_* env vars

3. extract_frankenphp_app()
   ├─ Cleans old /tmp/frankenphp_* dirs
   ├─ Starts binary in background
   ├─ Polls for extraction (timeout: 60s, configurable via FRANKENPHP_EXTRACT_TIMEOUT)
   ├─ Verifies: webroot/index.php + vendor/autoload.php exist
   ├─ Handles crash-restart cycle (expected FrankenPHP behavior)
   └─ Writes sentinel: /tmp/.frankenphp_app_path

4. copy_config_files()
   └─ Globs config/*.example.php → *.php (+ plugins)

5. run_migrations()
   ├─ bin/cake migrations migrate
   └─ bin/cake migrations migrate -p <plugin> (for each plugin)

6. run_seeders()    (auto-detect by default)
   ├─ SELECT COUNT(*) FROM actions → if 0, seed
   ├─ Convert identity columns (pg_config_1.sql)
   ├─ bin/cake migrations seed
   └─ Reset sequences (pg_config_2.sql)

7. Server mode: wait for FrankenPHP
   Queue mode: kill server, exec queue worker CLI
```

---

## Environment Variable Reference

### Control Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `SKIP_MIGRATIONS` | (unset) | Set to skip migrations |
| `RUN_SEEDERS` | auto | `true`, `false`, or `auto` (checks DB) |
| `SKIP_SEEDERS` | (unset) | Set to skip seeders |
| `QUEUE_WORKER` | (unset) | Set `true` to run as queue worker |
| `WORKER_MAX_RUNTIME` | 1800 | Queue worker max runtime (seconds) |
| `FRANKENPHP_EXTRACT_TIMEOUT` | 60 | Max seconds to wait for app extraction |
| `DEBUG` | false | **Must be false in production** |

### PHP Runtime Overrides

| Variable | Default (embedded) | Purpose |
|----------|-------------------|---------|
| `PHP_MEMORY_LIMIT` | 512M | Per-request memory |
| `PHP_UPLOAD_MAX_FILESIZE` | 100M | Max upload file size |
| `PHP_POST_MAX_SIZE` | 100M | Max POST body |
| `PHP_MAX_EXECUTION_TIME` | 300 | Request timeout (seconds) |

---

## Health Checks

| Endpoint | Handler | Use for |
|----------|---------|---------|
| `GET /healthz` | Caddy (instant, no PHP) | ALB/k8s liveness probes, Docker healthcheck |
| `GET /home/healthcheck` | CakePHP (verifies app + DB) | Readiness probes |

Docker compose uses `/healthz` by default (30s interval, 60s start period, 5 retries).

---

## Troubleshooting

### Container won't start — "SECURITY_SALT is still the placeholder value"

The `.env` file has `SECURITY_SALT=__CHANGE_THIS_TO_RANDOM_STRING__`. Generate a real one:

```bash
openssl rand -hex 32 | sha256sum | cut -d' ' -f1
```

### Container starts but health check fails

Check logs:

```bash
docker compose logs orangescrum-app --tail 100
```

Common causes:

- Database not reachable (check `DB_HOST`, firewall, pg_hba.conf)
- Redis not reachable (check `REDIS_HOST`)
- Migrations failed (check logs for SQL errors)

### Queue jobs not processing

```bash
# Docker
docker compose --profile queue up -d
docker compose logs queue-worker

# Native
./helpers/queue-worker.sh start
./helpers/queue-worker.sh status
```

### Cron not running recurring tasks

Check the sentinel file exists:

```bash
cat /tmp/.frankenphp_app_path
```

If empty/missing, the FrankenPHP extraction didn't complete. Restart the container/service.

### Binary SHA256 mismatch

```bash
python3 build.py --verify dist/20260329_143000/dist-docker
```

If it fails, the binary was corrupted during transfer. Re-scp with checksums:

```bash
scp -C dist-docker/orangescrum-app/osv4-prod user@prod:/opt/orangescrum/orangescrum-app/
```

---

## Backup & Recovery

### Database

```bash
# Backup
PGPASSWORD="$DB_PASSWORD" pg_dump -h $DB_HOST -U orangescrum -d orangescrum -Fc \
    > orangescrum-$(date +%Y%m%d).dump

# Restore
PGPASSWORD="$DB_PASSWORD" pg_restore -h $DB_HOST -U orangescrum -d orangescrum \
    --clean --if-exists orangescrum-20260329.dump
```

### Application

The binary is immutable — just keep the dist package. To roll back:

```bash
# List available builds
ls dist/

# Deploy older build
./deploy.sh 20260328_100000
```

---

## Security Checklist

- [ ] `SECURITY_SALT` is unique, >= 32 chars, not shared across environments
- [ ] `DB_PASSWORD` is strong, >= 16 chars
- [ ] `DEBUG=false`
- [ ] `APP_BIND_IP=127.0.0.1` (when behind reverse proxy)
- [ ] Direct port 8080 blocked by firewall (only reverse proxy reaches it)
- [ ] TLS certificate configured on reverse proxy
- [ ] `REDIS_PASSWORD` set (if Redis is network-accessible)
- [ ] S3 bucket not publicly accessible
- [ ] `.env` file permissions: `chmod 600 .env`
