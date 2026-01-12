# OrangeScrum Cloud Builder - Native FrankenPHP Deployment

Simplified deployment system for OrangeScrum Enterprise Edition v4 (Durango) as a native FrankenPHP binary with minimal external services.

---

## Architecture

Based on actual .env configuration:

```
┌─────────────────────────────────────────────┐
│         Host Machine (192.168.49.10)        │
├─────────────────────────────────────────────┤
│                                             │
│  ┌──────────────────────────────────────┐  │
│  │  FrankenPHP Native Binary            │  │
│  │  - APP_BIND_IP: 0.0.0.0              │  │
│  │  - APP_PORT: 8080                    │  │
│  └──────────────────────────────────────┘  │
│                                             │
│  Docker Services (docker-compose.services.yml):
│                                             │
│  ┌──────────────────────────────────────┐  │
│  │  PostgreSQL 16                       │  │
│  │  - DB_HOST: 192.168.49.10            │  │
│  │  - DB_PORT: 5432                     │  │
│  │  - DB_USERNAME: postgres             │  │
│  │  - DB_PASSWORD: postgres             │  │
│  │  - DB_NAME: durango                  │  │
│  └──────────────────────────────────────┘  │
│                                             │
│  ┌──────────────────────────────────────┐  │
│  │  Redis 7 (with authentication)       │  │
│  │  - REDIS_HOST: 192.168.49.10         │  │
│  │  - REDIS_PORT: 6379                  │  │
│  │  - REDIS_PASSWORD: orangescrum-redis-│  │
│  │    password                          │  │
│  │  - REDIS_DATABASE: 0                 │  │
│  │  - For: CACHE_ENGINE & QUEUE_ENGINE │  │
│  └──────────────────────────────────────┘  │
│                                             │
│  ┌──────────────────────────────────────┐  │
│  │  MailHog (Email Testing)             │  │
│  │  - SMTP_HOST: 192.168.49.10          │  │
│  │  - SMTP_PORT: 1025                   │  │
│  │  - Web UI: 8025                      │  │
│  │  - TLS: false                        │  │
│  └──────────────────────────────────────┘  │
│                                             │
└─────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────┐
│      External Services (AWS, Optional)      │
├─────────────────────────────────────────────┤
│  - STORAGE_ENDPOINT: AWS S3 / MinIO / etc  │
│  - STORAGE_ACCESS_KEY & STORAGE_SECRET_KEY │
│  - STORAGE_BUCKET: orangescrum-files       │
│  - STORAGE_REGION: us-east-1               │
│  - SESSION_HANDLER: cache (Redis-backed)   │
└─────────────────────────────────────────────┘
```

---

## Quick Start

### Step 1: Prerequisites

```bash
# Check Docker
docker --version          # Need 24.0+
docker compose version    # Need v2.0+

# Check Python
python3 --version         # Need 3.8+
```

### Step 2: Start Support Services

```bash
cd /home/ubuntu/workspace/project-durango

# Start PostgreSQL, Redis, MailHog
docker compose -f docker-compose.services.yml up -d

# Verify services
docker compose -f docker-compose.services.yml ps
```

Expected output:
```
NAME            STATUS              PORTS
postgres16      Up (healthy)        192.168.49.10:5432
redis-durango   Up (healthy)        192.168.49.10:6379
mailhog         Up                  192.168.49.10:1025, 192.168.49.10:8025
```

### Step 3: Configure Environment

```bash
cd durango-builder/orangescrum-ee

# Review environment configuration
cat .env
```

Key settings to verify:
- `DB_HOST=192.168.49.10` (PostgreSQL)
- `REDIS_HOST=192.168.49.10` (Redis)
- `REDIS_PASSWORD=orangescrum-redis-password`
- `SMTP_HOST=192.168.49.10` (MailHog)

### Step 4: Build FrankenPHP Binary

```bash
cd /home/ubuntu/workspace/project-durango/durango-builder

# Create Python virtual environment (one-time)
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run builder
python3 build.py
```

### Step 5: Run Native Binary

```bash
cd durango-builder/orangescrum-ee

# Run with automatic migrations and seeding
PORT=8080 ./run.sh

# Or in daemon mode
DAEMON=true ./run.sh
```

Access the application:
- **URL**: `http://192.168.49.10:8080`
- **Email Web UI**: `http://192.168.49.10:8025`

---

## Directory Structure

```
durango-builder/
├── README.md (full stack - deprecated)
├── CLOUD_BUILDER_README.md (this file)
├── build.py (build script for FrankenPHP binary)
├── requirements.txt (Python dependencies)
├── builder/
│   ├── docker-compose.yaml (builder services)
│   ├── base-build.Dockerfile (FrankenPHP build)
│   ├── app-embed.Dockerfile (app embedding)
│   └── package/ (temp git archive extraction)
├── orangescrum-ee/
│   ├── .env (environment configuration)
│   ├── .env.example (template)
│   ├── run.sh (native binary runner)
│   ├── docker-compose.yaml (deprecated - full stack)
│   ├── orangescrum-app/
│   │   └── orangescrum-ee (FrankenPHP binary - built)
│   └── config/ (config overrides)
└── docs/
    ├── FRANKENPHP_DEPLOYMENT.md (binary deployment)
    ├── QUICK_REFERENCE.md (quick commands)
    └── ... (other docs - may need cleanup)

../docker-compose.services.yml (minimal services setup)
```

---

## Environment Variables

Refer to `.env.example` for complete list. Key variables for cloud builder:

### Required - Database

```bash
DB_HOST=192.168.49.10              # PostgreSQL hostname
DB_PORT=5432                       # PostgreSQL port
DB_USERNAME=postgres               # Database user
DB_PASSWORD=postgres               # Database password
DB_NAME=durango                    # Database name
```

### Required - Application

```bash
DEBUG=false                        # Enable debug (development only)
SECURITY_SALT=<random-string>     # Generate: openssl rand -base64 32
COMPOSE_PROJECT_NAME=orangescrum-cloud
```

### Cache & Queue (Redis)

```bash
CACHE_ENGINE=redis                # Cache backend
QUEUE_ENGINE=redis                # Queue backend
QUEUE_URL=redis://:orangescrum-redis-password@192.168.49.10:6379/0

REDIS_HOST=192.168.49.10          # Redis hostname
REDIS_PORT=6379                   # Redis port
REDIS_PASSWORD=orangescrum-redis-password  # Redis auth password
REDIS_DATABASE=0                  # Redis database number
REDIS_PREFIX=cake_                # Cache key prefix
REDIS_TIMEOUT=1                   # Connection timeout (seconds)
REDIS_TLS_ENABLED=false           # TLS for ElastiCache (future)
REDIS_TLS_VERIFY_PEER=false       # TLS verification
```

### Email (SMTP via MailHog)

```bash
EMAIL_TRANSPORT=smtp              # Transport type
SMTP_HOST=192.168.49.10           # SMTP hostname
SMTP_PORT=1025                    # SMTP port
SMTP_USERNAME=                    # SMTP username (empty for MailHog)
SMTP_PASSWORD=                    # SMTP password (empty for MailHog)
SMTP_TLS=false                    # TLS enabled

FROM_EMAIL=noreply@ossiba.local   # From email address
NOTIFY_EMAIL=admin@ossiba.local   # Notification email
```

### PHP Configuration

```bash
PHP_MEMORY_LIMIT=512M             # PHP memory limit
PHP_POST_MAX_SIZE=200M            # Max POST data
PHP_UPLOAD_MAX_FILESIZE=200M      # Max upload file size
PHP_MAX_EXECUTION_TIME=300        # Max execution time (seconds)
```

### Session Configuration

```bash
SESSION_HANDLER=cache             # Use Redis for sessions
SESSION_COOKIE_DOMAIN=            # Cookie domain (optional)
```

### File Storage (S3-Compatible)

```bash
STORAGE_ENDPOINT=https://s3.amazonaws.com  # S3 endpoint or MinIO
STORAGE_ACCESS_KEY=                        # AWS/MinIO access key
STORAGE_SECRET_KEY=                        # AWS/MinIO secret key
STORAGE_BUCKET=orangescrum-files           # Bucket name
STORAGE_REGION=us-east-1                   # AWS region
STORAGE_PATH_STYLE=false                   # URL style (MinIO needs true)
```

### Optional - reCAPTCHA

```bash
RECAPTCHA_ENABLED=false           # Enable reCAPTCHA
RECAPTCHA_SITE_KEY=               # reCAPTCHA site key
RECAPTCHA_SECRET_KEY=             # reCAPTCHA secret key
RECAPTCHA_VERSION=v3              # reCAPTCHA version (v2 or v3)
RECAPTCHA_MIN_SCORE=0.5           # Min score for v3 (0.0-1.0)
```

### Optional - Google OAuth

```bash
GOOGLE_OAUTH_ENABLED=false        # Enable Google OAuth
GOOGLE_OAUTH_CLIENT_ID=           # Google OAuth client ID
GOOGLE_OAUTH_CLIENT_SECRET=       # Google OAuth client secret
GOOGLE_OAUTH_REDIRECT_URI=        # OAuth redirect URI
```

### Queue Worker Configuration

```bash
WORKER_MAX_RUNTIME=1800           # Worker max runtime (seconds)
WORKER_SLEEP=5                    # Worker sleep interval (seconds)
```

### V2 Routing (Optional - for multi-app setup)

```bash
V4_ROUTING_ENABLED=false          # Enable V4 routing
V2_ROUTING_API_KEY=               # API key for V2 routing
V2_BASE_URL=https://app.ossiba.com   # V2 application URL
V4_BASE_URL=https://v4.ossiba.com    # V4 application URL
V2_ROUTING_TOKEN_EXPIRATION=15    # Auto-login token expiration (minutes)
V2_ROUTING_TIMEOUT=10             # API request timeout (seconds)
V2_ROUTING_SSL_VERIFY=true        # SSL verification for API
```

### Application Bind Configuration

```bash
APP_BIND_IP=0.0.0.0               # Bind to all interfaces
APP_PORT=8080                     # Application port
```

See `.env.example` for complete documentation on all variables.

---

## Common Tasks

### View Application Logs

```bash
# Find extraction directory
PID_FILE="durango-builder/orangescrum-ee/frankenphp.pid"
EXTRACTED_APP=$(cat "$PID_FILE" 2>/dev/null)

# View logs
tail -f /tmp/frankenphp_*/logs/error.log
```

### Stop the Application

```bash
# Get PID
PID=$(cat durango-builder/orangescrum-ee/frankenphp.pid 2>/dev/null)

# Kill process
kill $PID
```

### Stop Support Services

```bash
cd /home/ubuntu/workspace/project-durango

docker compose -f docker-compose.services.yml down
```

### Rebuild Application (code changes)

```bash
cd /home/ubuntu/workspace/project-durango/durango-builder

# Skip base image rebuild (faster)
python3 build.py --skip-base

# Then run again
cd orangescrum-ee
PORT=8080 ./run.sh
```

### Run Database Migrations Manually

```bash
cd /tmp/frankenphp_*/

# Find binary location from frankenphp.pid output
BINARY="path/to/orangescrum-ee"

# Run migrations
$BINARY php-cli bin/cake.php migrations migrate
```

---

## Migration Path to AWS

This setup is designed to transition easily to AWS:

1. **Phase 1** (Current): All services on single host
   - PostgreSQL in Docker → AWS RDS
   - Redis in Docker → AWS ElastiCache
   - MailHog → AWS SES
   - Binary stays native

2. **Phase 2**: Update `.env` to point to AWS services
   ```bash
   DB_HOST=my-db.rds.amazonaws.com
   REDIS_HOST=my-cache.cache.amazonaws.com
   SMTP_HOST=email.us-east-1.amazonaws.com
   ```

3. **Phase 3**: Package binary for AWS Lambda/EC2
   - No Docker dependency needed
   - Binary is self-contained

---

## Troubleshooting

### Binary not found
```bash
# Build it first
cd durango-builder
python3 build.py
```

### Database connection refused
```bash
# Check services are running
docker compose -f docker-compose.services.yml ps

# Verify IP address
ip a | grep 192.168.49
```

### Redis connection failed
```bash
# Check Redis password
docker compose -f docker-compose.services.yml exec redis-durango \
  redis-cli -a orangescrum-redis-password ping

# Should output: PONG
```

### Port already in use
```bash
# Find what's using the port
lsof -i :8080

# Kill the process
kill -9 <PID>
```

---

## Documentation

- [FRANKENPHP_DEPLOYMENT.md](docs/FRANKENPHP_DEPLOYMENT.md) - Binary deployment details
- [QUICK_REFERENCE.md](docs/QUICK_REFERENCE.md) - Quick command reference
- [../docker-compose.services.yml](../docker-compose.services.yml) - Service configuration

---

## Notes

- **No Docker for App**: The FrankenPHP binary runs natively on the host
- **Minimal Services**: Only PostgreSQL, Redis, and MailHog run in Docker
- **Easy Scaling**: Replace Docker services with AWS equivalents without code changes
- **Self-Contained Binary**: ~340 MB, includes PHP + all dependencies
- **Single IP**: All services bind to `192.168.49.10` for consistent networking
