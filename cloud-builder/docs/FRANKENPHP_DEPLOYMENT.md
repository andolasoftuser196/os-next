# FrankenPHP Static Binary Deployment Guide

This document describes the Docker setup for deploying the OrangeScrum CakePHP 4 application as a FrankenPHP static binary.

## Architecture Overview

### FrankenPHP Static Binary

The application is embedded into a self-contained FrankenPHP binary (`orangescrum-ee`) that includes:

- PHP 8.3 interpreter with all required extensions
- Caddy web server
- Complete OrangeScrum application code
- All PHP dependencies (vendor directory)

### Runtime Environment

The Docker container runs on Alpine Linux with minimal dependencies:

- Runtime tools: bash, wget, postgresql-client
- Cron daemon for scheduled tasks
- No PHP installation required (included in FrankenPHP binary)

## Configuration System

The application follows CakePHP 4 conventions with environment-based configuration:

### 1. Cache Configuration

Controlled by `CACHE_ENGINE` environment variable:

- `file` (default): File-based caching using `/tmp/cache`
- `redis`: Redis-based caching (requires external Redis server)

The entrypoint dynamically creates `config/cache_redis.php` when `CACHE_ENGINE=redis`.

Configuration includes:

- `default`: General application cache
- `_cake_core_`: Framework translation cache
- `_cake_model_`: Schema and table listing cache
- `_cake_routes_`: Route collection cache

### 2. Queue Configuration

Controlled by `QUEUE_ENGINE` environment variable:

- `redis` (default): Redis-based queue (recommended)
- `database`: Database-based queue (fallback)

The entrypoint dynamically creates `config/queue.php` with proper Redis URL.

### 3. Email Configuration

Supports two transports:

- **SMTP**: Traditional SMTP server (set via `SMTP_HOST`, `SMTP_PORT`, etc.)
- **SendGrid**: SendGrid API (set via `EMAIL_API_KEY`)

The entrypoint dynamically creates:

- `config/smtp.php` when `SMTP_HOST` is provided
- `config/sendgrid.php` when `EMAIL_API_KEY` is provided

### 4. Database Configuration

PostgreSQL database connection configured via environment variables:

- `DB_HOST`: Database hostname
- `DB_PORT`: Database port (default: 5432)
- `DB_USERNAME`: Database username
- `DB_PASSWORD`: Database password
- `DB_PASSWORD_FILE`: Path to file containing password (for Docker secrets)
- `DB_NAME`: Database name

## Environment Variables

### Required

```bash
SECURITY_SALT=<random-string>  # Generate with: openssl rand -base64 32
DB_HOST=<database-host>
DB_PASSWORD=<database-password>
```

### Application

```bash
DEBUG=false                     # Enable debug mode (development only)
CACHE_ENGINE=file              # Cache backend: file|redis
QUEUE_ENGINE=redis             # Queue backend: redis|database
SKIP_MIGRATIONS=1              # Skip database migrations on startup
```

### Redis (if CACHE_ENGINE=redis or QUEUE_ENGINE=redis)

```bash
REDIS_HOST=localhost           # Redis server hostname
REDIS_PORT=6379               # Redis server port
REDIS_PASSWORD=               # Redis password (optional)
REDIS_DATABASE=0              # Redis database number (0-15)
REDIS_PREFIX=cake_            # Cache key prefix
REDIS_TIMEOUT=1               # Connection timeout (seconds)
```

### Email

```bash
# SMTP Configuration
EMAIL_TRANSPORT=smtp
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=user@example.com
SMTP_PASSWORD=secret
SMTP_TLS=true

# OR SendGrid Configuration
EMAIL_TRANSPORT=sendgrid
EMAIL_API_KEY=SG.xxxxxxxxxxxxx

# Common
FROM_EMAIL=noreply@orangescrum.local
NOTIFY_EMAIL=admin@orangescrum.local
```

### PHP

```bash
PHP_MEMORY_LIMIT=512M
PHP_POST_MAX_SIZE=200M
PHP_UPLOAD_MAX_FILESIZE=200M
PHP_MAX_EXECUTION_TIME=300
```

## Deployment

### 1. Build the Docker Image

```bash
cd durango-builder/orangescrum-ee
docker build -t orangescrum-ee:latest .
```

### 2. Configure Environment

```bash
cp .env.example .env
nano .env  # Edit configuration
```

Important: Set `SECURITY_SALT` to a random value:

```bash
SECURITY_SALT=$(openssl rand -base64 32)
```

### 3. Run with Docker Compose

```bash
# Start application only
docker compose up -d

# Start application + queue worker
docker compose --profile queue up -d
```

### 4. Health Check

The application exposes a health check endpoint:

```bash
curl http://localhost:8080/home/healthcheck
```

## Services

### orangescrum-app

Main application server running FrankenPHP.

**Ports:**

- 80 (internal) → 8080 (host)

**Volumes:**

- None (stateless, connects to external database)

**Resource Limits:**

- CPU: 0.5-2 cores
- Memory: 512M-2G

### queue-worker (optional)

Background queue worker for async tasks.

**Enabled by:**

```bash
docker compose --profile queue up -d
```

**Resource Limits:**

- CPU: 0.25-1 cores
- Memory: 256M-1G

## Cron Tasks

The container runs cron daemon for recurring tasks:

- **Schedule**: Every 30 minutes
- **Command**: `bin/cake.php recurring_task`
- **Logs**: `/data/logs/cron.log`

Configuration: `config/cron/recurring_task_cron_franken`

## Startup Sequence

1. **FrankenPHP starts** and extracts embedded app to `/tmp/frankenphp_*`
2. **Wait for extraction** (max 30 seconds)
3. **Create dynamic configs** based on environment variables:
   - `cache_redis.php` (if `CACHE_ENGINE=redis`)
   - `queue.php` (if `QUEUE_ENGINE=redis`)
   - `smtp.php` (if `SMTP_HOST` set)
   - `sendgrid.php` (if `EMAIL_API_KEY` set)
4. **Run database migrations** (unless `SKIP_MIGRATIONS=1`)
5. **Start cron daemon** (for recurring tasks)
6. **FrankenPHP serves requests** on port 80

## Configuration Loading Order

CakePHP loads configurations in this order (see `config/bootstrap.php`):

1. `config/app.php` (base configuration)
2. `config/app_local.php` (environment overrides)
3. `config/queue.php` (queue configuration)
4. `config/cache_{engine}.php` (cache configuration based on `CacheEngine`)
5. `config/smtp.php` or `config/sendgrid.php` (email transport)
6. Other optional configs: `recaptcha.php`, `cloudstorage.php`, etc.

## Production Best Practices

### 1. Use External Services

- **Database**: Managed PostgreSQL (AWS RDS, Azure Database, etc.)
- **Redis**: Managed Redis (AWS ElastiCache, Redis Cloud, etc.)
- **Email**: SendGrid or managed SMTP service

### 2. Security

- Set strong `SECURITY_SALT` (never commit to git)
- Use Docker secrets for `DB_PASSWORD_FILE`
- Keep `DEBUG=false` in production
- Use TLS/SSL for Redis and SMTP connections

### 3. Scaling

- Run multiple `orangescrum-app` instances behind a load balancer
- Run dedicated `queue-worker` instances for background processing
- Use Redis for cache and queue (enables distributed caching)

### 4. Monitoring

- Watch health check endpoint: `/home/healthcheck`
- Monitor logs: `/data/logs/cron.log`, application logs
- Set up container resource monitoring (CPU, memory, network)

### 5. Backups

- Backup PostgreSQL database regularly
- No file uploads stored in container (stateless design)
- External storage (S3, MinIO) recommended for user files

## Troubleshooting

### App fails to start

```bash
# Check logs
docker logs orangescrum-cloud-base-orangescrum-app-1

# Common issues:
# - DB connection failed: Check DB_HOST, DB_PASSWORD
# - Redis connection failed: Check REDIS_HOST, REDIS_PASSWORD
# - Migration failed: Set SKIP_MIGRATIONS=1 and run manually
```

### Cache not working

```bash
# Verify cache configuration
docker exec orangescrum-cloud-base-orangescrum-app-1 \
  ls -la /tmp/frankenphp_*/config/cache_*.php

# Test Redis connection (if using Redis)
docker exec orangescrum-cloud-base-orangescrum-app-1 \
  /orangescrum-app/orangescrum-ee php-cli -r \
  "var_dump((new Redis())->connect(getenv('REDIS_HOST'), getenv('REDIS_PORT')));"
```

### Queue not processing

```bash
# Check queue worker logs
docker logs orangescrum-cloud-base-queue-worker-1

# Verify queue configuration
docker exec orangescrum-cloud-base-orangescrum-app-1 \
  cat /tmp/frankenphp_*/config/queue.php
```

### Cron not running

```bash
# Check cron logs
docker exec orangescrum-cloud-base-orangescrum-app-1 \
  cat /data/logs/cron.log

# Verify cron is running
docker exec orangescrum-cloud-base-orangescrum-app-1 \
  ps aux | grep cron
```

## References

- **FrankenPHP**: <https://frankenphp.dev/>
- **CakePHP 4**: <https://book.cakephp.org/4/en/>
- **Docker Compose**: <https://docs.docker.com/compose/>
- **Redis**: <https://redis.io/>
