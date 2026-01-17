# OrangeScrum FrankenPHP - Common Files

This directory contains the **common source files** for FrankenPHP-based deployments of OrangeScrum.

## 📁 Directory Structure

This folder serves as the **source of truth** for deployment files:

```
orangescrum-cloud/               # Common source files (this folder)
├── build-docker.sh              # Build Docker deployment
├── build-native.sh              # Build Native deployment
├── config/                      # Shared configuration files
├── docs/                        # Shared documentation
├── Dockerfile                   # Docker container definition
├── docker-compose.yaml          # Docker orchestration
├── docker-compose.services.yml  # Infrastructure services
├── entrypoint.sh                # Docker entrypoint
├── run-native.sh                # Native runner
├── run.sh                       # Alternative native runner
├── package.sh                   # Package builder
├── cake.sh                      # CakePHP CLI helper
├── queue-worker.sh              # Queue worker
├── validate-env.sh              # Environment validator
├── .env.example                 # Environment template
├── .env.full.example            # Complete env example
├── CONFIGS.md                   # Configuration reference
└── orangescrum-app/
    └── osv4-prod                # FrankenPHP binary (built by build.py)
```

## 🎯 How It Works

### Build Process

1. **Build the binary:**
   ```bash
   cd /home/ubuntu/workspace/os-next/cloud-builder
   python build.py
   ```

2. **Binary is extracted to:**
   ```
   orangescrum-cloud/orangescrum-app/osv4-prod
   ```

3. **Deployment folders are automatically built:**
   - `build-docker.sh` → Creates `../orangescrum-cloud-docker/`
   - `build-native.sh` → Creates `../orangescrum-cloud-native/`

### Deployment Folders

The build scripts create deployment-ready folders:

**🐳 orangescrum-cloud-docker/** - Docker containerized deployment
- Copies: `Dockerfile`, `docker-compose.yaml`, `entrypoint.sh`, `.dockerignore`
- Copies: Common files (config/, docs/, scripts)
- Copies: Binary from `orangescrum-app/osv4-prod`

**🖥️ orangescrum-cloud-native/** - Native binary deployment
- Copies: `run-native.sh`, `run.sh`, `package.sh`, `caddy.sh`
- Copies: Common files (config/, docs/, scripts)
- Copies: Binary from `orangescrum-app/osv4-prod`

## 🔧 Manual Build

If you need to rebuild deployment folders manually:

```bash
# Rebuild Docker deployment
./build-docker.sh

# Rebuild Native deployment
./build-native.sh

# Rebuild both
./build-docker.sh && ./build-native.sh
```

## 🧹 Clean/Reset Generated Folders

To remove auto-generated deployment folders and start fresh:

```bash
# Clean (remove) generated folders
./clean.sh

# Then rebuild
./build-docker.sh && ./build-native.sh

# Or rebuild everything from scratch
cd .. && python build.py
```

**What gets cleaned:**
- `../orangescrum-cloud-docker/` (entire folder)
- `../orangescrum-cloud-native/` (entire folder)

**What is preserved:**
- `orangescrum-cloud/` (source files)
- `orangescrum-app/osv4-prod` (binary)

## 📦 Create Distribution Packages

To create production-ready distribution packages with timestamps:

```bash
# Package both Docker and Native deployments
./dist-all.sh

# Or package individually
./dist-docker.sh   # Docker package only
./dist-native.sh   # Native package only

# Customize binary name (default: orangescrum)
BINARY_NAME=osv4-prod ./dist-native.sh        # Keep production name
BINARY_NAME=orangescrum ./dist-native.sh      # Use friendly name
BINARY_NAME=myapp ./dist-native.sh            # Custom name
```

**Output structure:**
```
dist/
└── 20260117_183045/                                    # Timestamp folder
    ├── README.txt                                      # Distribution overview
    ├── orangescrum-docker-v26.1.1-20260117_183045.tar.gz
    ├── orangescrum-docker-v26.1.1-20260117_183045.manifest.txt
    ├── orangescrum-native-v26.1.1-20260117_183045.tar.gz
    └── orangescrum-native-v26.1.1-20260117_183045.manifest.txt
```

**Package contents:**
- Complete deployment with binary
- Configuration templates
- Documentation
- Deployment instructions
- SHA256 checksums
- Systemd service files (Native)

**Usage:**
```bash
# Extract and deploy
tar -xzf orangescrum-docker-v26.1.1-20260117_183045.tar.gz
cd orangescrum-docker-v26.1.1-20260117_183045
cp .env.example .env
nano .env
# Then deploy...
```

## 📝 Making Changes

### Updating Common Files

Edit files in **this folder** (`orangescrum-cloud/`):

1. Make changes to config/, docs/, or scripts
2. Rebuild deployment folders:
   ```bash
   ./build-docker.sh
   ./build-native.sh
   ```

### Updating Docker-Specific Files

1. Edit in this folder: `Dockerfile`, `docker-compose.yaml`, `entrypoint.sh`
2. Rebuild: `./build-docker.sh`

### Updating Native-Specific Files

1. Edit in this folder: `run-native.sh`, `run.sh`, `package.sh`
2. Rebuild: `./build-native.sh`

## 🚀 Quick Start

### For Docker Deployment

```bash
# Build everything
cd /home/ubuntu/workspace/os-next/cloud-builder
python build.py

# Deploy
cd orangescrum-cloud-docker
nano .env
docker-compose -f docker-compose.services.yml up -d
docker compose up -d
```

### For Native Deployment

```bash
# Build everything
cd /home/ubuntu/workspace/os-next/cloud-builder
python build.py

# Deploy
cd orangescrum-cloud-native
cp .env.example .env
nano .env
./validate-env.sh
./run-native.sh
```

## 📚 Documentation

- **Docker:** See `../orangescrum-cloud-docker/README.md`
- **Native:** See `../orangescrum-cloud-native/README.md`
- **Build System:** See `../README.md`
- **Configuration:** See `CONFIGS.md`
- **Production:** See `docs/PRODUCTION_DEPLOYMENT_*.md`

## ⚠️ Important Notes

- **Don't edit deployment folders directly** - they are auto-generated
- **Edit source files here** - then rebuild deployment folders
- **The binary** is built by `python build.py` and extracted here first
- **Deployment folders** are rebuilt automatically during build process

## 🔄 Workflow Summary

```
1. Edit source files → orangescrum-cloud/
                         ├── config/
                         ├── docs/
                         ├── Dockerfile
                         ├── run-native.sh
                         └── ...

2. Build binary     → python build.py
                      ↓
                      orangescrum-cloud/orangescrum-app/osv4-prod

3. Build deployments → build-docker.sh & build-native.sh
                       ↓                 ↓
                       orangescrum-cloud-docker/
                       orangescrum-cloud-native/

4. Deploy           → cd orangescrum-cloud-docker/ OR orangescrum-cloud-native/
                      ↓
                      docker compose up -d OR ./run-native.sh
```

## 📦 Files Organization

### Docker-Specific
- `Dockerfile`
- `docker-compose.yaml`
- `docker-compose.services.yml`
- `entrypoint.sh`
- `.dockerignore`
- `.env.docker`

### Native-Specific
- `run-native.sh`
- `run.sh`
- `package.sh`
- `caddy.sh`
- `.env.full.example`

### Common (Used by Both)
- `config/` - Configuration templates
- `docs/` - Documentation
- `cake.sh` - CakePHP CLI
- `queue-worker.sh` - Queue worker
- `validate-env.sh` - Validation
- `.env.example` - Environment template
- `CONFIGS.md` - Config reference

---

**This is the source folder. Deploy from `orangescrum-cloud-docker/` or `orangescrum-cloud-native/`.**

docker-compose -f docker-compose.services.yml up -d

# Services:
# - PostgreSQL 16 on 5432 (user: postgres, password: postgres)
# - Redis 7 on 6379
# - MinIO (S3) on 9000/9090 (access: minioadmin/minioadmin)
# - MailHog (SMTP) on 1025/8025 (web: http://localhost:8025)

# Stop
docker-compose -f docker-compose.services.yml down

# View logs
docker-compose -f docker-compose.services.yml logs -f
```

---

## Documentation

📘 **Getting Started:**
- [DEPLOYMENT.md](docs/DEPLOYMENT.md) - Quick start and basic configuration

📚 **Production Deployment:**
- [PRODUCTION_READINESS_SUMMARY.md](docs/PRODUCTION_READINESS_SUMMARY.md) - Pre-production checklist
- [PRODUCTION_DEPLOYMENT_NATIVE.md](docs/PRODUCTION_DEPLOYMENT_NATIVE.md) - Native binary on Linux server
- [PRODUCTION_DEPLOYMENT_DOCKER.md](docs/PRODUCTION_DEPLOYMENT_DOCKER.md) - Docker Compose on server

⚙️ **Configuration & Operations:**
- [ENVIRONMENT_CONFIGURATION.md](docs/ENVIRONMENT_CONFIGURATION.md) - All environment variables
- [CONFIGS.md](CONFIGS.md) - Configuration files reference

---

## Pre-flight Checks

Before starting the application, `run.sh` verifies:

✅ FrankenPHP binary exists  
✅ PostgreSQL client (`psql`) is installed  
⚠️ Warns if database seeders cannot run (without `psql`)

### Installing Dependencies

```bash
# Ubuntu/Debian
sudo apt install -y postgresql-client

# macOS
brew install postgresql

# Alpine
apk add postgresql-client
```

---

## Running the Application

### Foreground Mode (Development)
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
├── .env.docker                     # Environment configuration template for development
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
