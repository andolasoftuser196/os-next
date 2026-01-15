# OrangeScrum FrankenPHP Static Binary Setup

This directory contains the deployment configuration for OrangeScrum as a FrankenPHP static binary.

## ⚠️ Production Deployment

**Before deploying to production**, please read:

📘 **[Production Readiness Summary](docs/PRODUCTION_READINESS_SUMMARY.md)** - Start here!

Choose your deployment mode:
- 🐳 **[Docker Production Guide](docs/PRODUCTION_DEPLOYMENT_DOCKER.md)** - Recommended for most users
- 🖥️ **[Native Binary Production Guide](docs/PRODUCTION_DEPLOYMENT_NATIVE.md)** - For direct server deployment

**Required before production:**
1. Run `./validate-env.sh` to check configuration
2. Generate secure passwords and secrets
3. Configure external services (PostgreSQL, Redis, S3)
4. Set up SSL certificate and reverse proxy
5. Configure firewall and monitoring

---

## Quick Start (Development)

### Prerequisites

- Docker and Docker Compose installed
- PostgreSQL database (local or external)
- Redis server for caching and queuing (recommended)

### 1. Configure Environment

```bash
cp .env.example .env
nano .env
```

**Critical: Set these values**

```bash
# Generate a secure salt (REQUIRED)
SECURITY_SALT=$(php -r 'echo hash("sha256", bin2hex(random_bytes(32)));')

# Database configuration (REQUIRED)
DB_HOST=your-database-host
DB_PASSWORD=your-secure-password
DB_NAME=orangescrum

# Cache engine: 'redis' (recommended) or 'file'
CACHE_ENGINE=redis

# Redis configuration (if CACHE_ENGINE=redis)
REDIS_HOST=your-redis-host
REDIS_PORT=6379
REDIS_PASSWORD=your-redis-password  # If authentication enabled

# S3 Storage (REQUIRED for file uploads)
STORAGE_ENDPOINT=https://s3.amazonaws.com
STORAGE_ACCESS_KEY=your-access-key
STORAGE_SECRET_KEY=your-secret-key
STORAGE_BUCKET=orangescrum-files
STORAGE_REGION=us-east-1

# Email (REQUIRED for notifications)
EMAIL_TRANSPORT=sendgrid
EMAIL_API_KEY=your-sendgrid-api-key
FROM_EMAIL=noreply@yourdomain.com
```

### 2. Validate Configuration

```bash
# Validate environment before deployment
./validate-env.sh

# Should output: "✓ VALIDATION PASSED"
# Fix any errors before proceeding
```

### 3. Build and Deploy

```bash
# Build the image (first time only)
docker compose build

# Start the application
docker compose up -d

# Start with queue worker (recommended for production)
docker compose --profile queue up -d
```

### 3. Verify Deployment

```bash
# Check logs
docker compose logs -f orangescrum-app

# Test health check
curl http://localhost:8080/home/healthcheck

# Check running containers
docker compose ps
```

## Project Structure

```
orangescrum-cloud/
├── Dockerfile                      # FrankenPHP runtime container
├── docker-compose.yaml             # Service orchestration
├── entrypoint.sh                   # Startup script with config generation
├── .env.example                    # Environment configuration template
├── FRANKENPHP_DEPLOYMENT.md       # Detailed deployment guide
├── README.md                       # This file
├── orangescrum-app/
│   └── osv4-prod             # FrankenPHP static binary (embedded app)
└── config/
    ├── cache_file.php             # File cache configuration
    └── cron/
        └── recurring_task_cron_franken  # Cron schedule
```

## Configuration Files

### Static Files (Bundled)

These are included in the FrankenPHP binary:

- Application source code
- Vendor dependencies
- Base configuration (`config/app.php`)

### Dynamic Files (Generated at Runtime)

Created by entrypoint based on environment variables:

- `config/cache_redis.php` - When `CACHE_ENGINE=redis`
- `config/queue.php` - When `QUEUE_ENGINE=redis`
- `config/smtp.php` - When `SMTP_HOST` is set
- `config/sendgrid.php` - When `EMAIL_API_KEY` is set

## Services

### orangescrum-app

Main application server.

**Environment Variables:**

- See [.env.example](.env.example) for all options
- See [FRANKENPHP_DEPLOYMENT.md](FRANKENPHP_DEPLOYMENT.md) for detailed documentation

**Ports:**

- `8080:80` - HTTP web server

**Health Check:**

- URL: `http://localhost/home/healthcheck`
- Interval: 30s
- Start period: 60s

### queue-worker (Optional)

Background queue worker for async task processing.

**Enable:**

```bash
docker compose --profile queue up -d
```

**Command:**

```bash
/orangescrum-app/osv4-prod php-cli bin/cake.php queue worker --verbose
```

## Environment Configuration

### Minimal Configuration (Development)

```bash
SECURITY_SALT=generated-random-string
DB_HOST=host.docker.internal
DB_PASSWORD=orangescrum
DB_NAME=orangescrum
CACHE_ENGINE=file
QUEUE_ENGINE=redis
REDIS_HOST=localhost
```

### Production Configuration

```bash
SECURITY_SALT=generated-random-string

# External managed database
DB_HOST=postgres.production.example.com
DB_PORT=5432
DB_USERNAME=orangescrum_prod
DB_PASSWORD_FILE=/run/secrets/db_password
DB_NAME=orangescrum_prod

# Redis cache and queue
CACHE_ENGINE=redis
QUEUE_ENGINE=redis
REDIS_HOST=redis.production.example.com
REDIS_PORT=6379
REDIS_PASSWORD=redis-auth-token

# Email via SendGrid
EMAIL_TRANSPORT=sendgrid
EMAIL_API_KEY=SG.xxxxxxxxxxxxx
FROM_EMAIL=noreply@yourcompany.com

# Production settings
DEBUG=false
SKIP_MIGRATIONS=1
```

## Cache Strategies

### File-based Cache (Default)

```bash
CACHE_ENGINE=file
```

- **Pros**: No external dependencies, simple setup
- **Cons**: Not suitable for multi-instance deployments
- **Use case**: Development, single-instance deployments

### Redis Cache (Recommended)

```bash
CACHE_ENGINE=redis
REDIS_HOST=your-redis-host
REDIS_PORT=6379
REDIS_PASSWORD=optional-auth-token
```

- **Pros**: Fast, distributed, scalable
- **Cons**: Requires external Redis server
- **Use case**: Production, multi-instance deployments

## Queue Processing

### Redis Queue (Default)

```bash
QUEUE_ENGINE=redis
REDIS_HOST=your-redis-host
```

Background tasks processed by separate `queue-worker` service.

**Start worker:**

```bash
docker compose --profile queue up -d queue-worker
```

**Monitor:**

```bash
docker compose logs -f queue-worker
```

### Database Queue (Fallback)

```bash
QUEUE_ENGINE=database
```

Jobs stored in database, processed by scheduled cron or worker.

## Email Configuration

### SMTP

```bash
EMAIL_TRANSPORT=smtp
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_TLS=true
```

### SendGrid

```bash
EMAIL_TRANSPORT=sendgrid
EMAIL_API_KEY=SG.xxxxxxxxxxxxx
```

## Scheduled Tasks

Cron runs every 30 minutes for recurring tasks:

- Task processing
- Email notifications
- Data cleanup

**Configuration:** [config/cron/recurring_task_cron_franken](config/cron/recurring_task_cron_franken)

**Logs:** `/data/logs/cron.log`

**View logs:**

```bash
docker exec orangescrum-cloud-base-orangescrum-app-1 tail -f /data/logs/cron.log
```

## Database Migrations

### Automatic (Default)

Migrations run automatically on container startup.

### Manual

```bash
# Skip auto migrations
SKIP_MIGRATIONS=1

# Run manually
docker exec -it orangescrum-cloud-base-orangescrum-app-1 bash
cd /tmp/frankenphp_*
/orangescrum-app/osv4-prod php-cli bin/cake.php migrations migrate
/orangescrum-app/osv4-prod php-cli bin/cake.php migrations migrate -p Gitsync
```

## Scaling

### Horizontal Scaling

Run multiple app instances behind a load balancer:

```bash
docker compose up -d --scale orangescrum-app=3
```

**Requirements:**

- Use `CACHE_ENGINE=redis` (file cache doesn't work across instances)
- Use `QUEUE_ENGINE=redis` (database queue may cause race conditions)
- External PostgreSQL database
- External Redis server

### Dedicated Queue Workers

```bash
docker compose up -d --scale queue-worker=2
```

## Troubleshooting

### Container won't start

```bash
# View logs
docker compose logs orangescrum-app

# Common issues:
# 1. Database connection failed
docker compose exec orangescrum-app \
  /orangescrum-app/osv4-prod php-cli -r \
  "var_dump(pg_connect('host='.getenv('DB_HOST').' dbname='.getenv('DB_NAME').' user='.getenv('DB_USERNAME').' password='.getenv('DB_PASSWORD')));"

# 2. Redis connection failed
docker compose exec orangescrum-app \
  /orangescrum-app/osv4-prod php-cli -r \
  "\$r = new Redis(); var_dump(\$r->connect(getenv('REDIS_HOST'), getenv('REDIS_PORT')));"
```

### Configuration not applied

```bash
# Check extracted app location
docker compose exec orangescrum-app ls -la /tmp/frankenphp_*

# View generated configs
docker compose exec orangescrum-app cat /tmp/frankenphp_*/config/cache_redis.php
docker compose exec orangescrum-app cat /tmp/frankenphp_*/config/queue.php
```

### Cron not running

```bash
# Check cron process
docker compose exec orangescrum-app ps aux | grep cron

# View cron logs
docker compose exec orangescrum-app cat /data/logs/cron.log

# Test cron command manually
docker compose exec orangescrum-app bash -c \
  "cd /tmp/frankenphp_* && /orangescrum-app/osv4-prod php-cli bin/cake.php recurring_task"
```

### Performance issues

```bash
# Increase resources in docker-compose.yaml
deploy:
  resources:
    limits:
      cpus: '4'
      memory: 4G

# Enable Redis cache
CACHE_ENGINE=redis

# Check memory usage
docker stats
```

## Security Best Practices

1. **Never commit `.env` file** - Contains secrets
2. **Generate strong SECURITY_SALT** - `php -r 'echo hash("sha256", bin2hex(random_bytes(32)));'`
3. **Use Docker secrets** for passwords - Set `DB_PASSWORD_FILE`
4. **Keep DEBUG=false** in production
5. **Use TLS for Redis** - Set `REDIS_PASSWORD`
6. **Use TLS for SMTP** - Set `SMTP_TLS=true`
7. **Regular updates** - Rebuild image with latest dependencies

## Monitoring

### Health Checks

```bash
# Application health
curl http://localhost:8080/home/healthcheck

# Docker health status
docker compose ps
```

### Logs

```bash
# Application logs
docker compose logs -f orangescrum-app

# Queue worker logs
docker compose logs -f queue-worker

# Cron logs
docker compose exec orangescrum-app tail -f /data/logs/cron.log
```

### Metrics

```bash
# Resource usage
docker stats

# Container inspect
docker inspect orangescrum-cloud-base-orangescrum-app-1
```

## Backup and Recovery

### Database Backup

```bash
# Export database
docker compose exec orangescrum-app \
  pg_dump -h $DB_HOST -U $DB_USERNAME -d $DB_NAME > backup.sql

# Restore database
docker compose exec -T orangescrum-app \
  psql -h $DB_HOST -U $DB_USERNAME -d $DB_NAME < backup.sql
```

### Configuration Backup

```bash
# Backup .env file (securely)
cp .env .env.backup
chmod 600 .env.backup
```

## Further Reading

- [FRANKENPHP_DEPLOYMENT.md](FRANKENPHP_DEPLOYMENT.md) - Detailed deployment guide
- [.env.example](.env.example) - All environment variables
- [FrankenPHP Documentation](https://frankenphp.dev/)
- [CakePHP 4 Documentation](https://book.cakephp.org/4/)

## Support

For issues and questions:

1. Check logs: `docker compose logs`
2. Review [FRANKENPHP_DEPLOYMENT.md](FRANKENPHP_DEPLOYMENT.md)
3. Verify environment variables in `.env`
4. Test database and Redis connectivity
