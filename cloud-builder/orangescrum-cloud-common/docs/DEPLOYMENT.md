# OrangeScrum FrankenPHP - Deployment Guide

## Overview

This document provides deployment instructions for OrangeScrum using the native FrankenPHP binary runtime. This deployment method provides a standalone, self-contained application binary without Docker containerization.

**Alternative Deployment Methods:**
- Docker Compose deployment: See [PRODUCTION_DEPLOYMENT_DOCKER.md](PRODUCTION_DEPLOYMENT_DOCKER.md)
- Production deployment reference: See [PRODUCTION_DEPLOYMENT_NATIVE.md](PRODUCTION_DEPLOYMENT_NATIVE.md)
- Configuration reference: See [ENVIRONMENT_CONFIGURATION.md](ENVIRONMENT_CONFIGURATION.md)

---

## Development Environment Setup

### Prerequisites

- Linux-based system (Ubuntu 20.04+, Debian 11+, or equivalent)
- PostgreSQL client (`psql`) installed
- Docker and Docker Compose (for local infrastructure services)
- 2GB minimum RAM, 4GB recommended

### Installation Steps

**1. Extract the deployment package**

```bash
tar -xzf orangescrum-frankenphp-v26.1.1.tar.gz
cd orangescrum-frankenphp-v26.1.1/
```

**2. Configure environment**

```bash
cp .env.docker .env
nano .env
```

**3. Initialize infrastructure services (development only)**

For development and testing, local infrastructure services can be provisioned via Docker Compose:

```bash
docker-compose -f docker-compose.services.yml up -d
docker-compose -f docker-compose.services.yml ps
```

The following services will be available:
- PostgreSQL 16 (port 5432)
- Redis 7 (port 6379)
- MinIO S3-compatible storage (ports 9000/9090)
- MailHog SMTP service (ports 1025/8025)

**4. Start the application**

```bash
# Foreground mode (development)
./run.sh

# Background mode (daemon)
DAEMON=true ./run.sh &
```

Application will be available at: `http://localhost:8080`

---

## Production Environment

### Infrastructure Requirements

Production deployments require external, managed services:

- **Database**: PostgreSQL 12+ (managed service or dedicated server)
- **Cache/Queue**: Redis 6+ (managed service or dedicated server)
- **Object Storage**: AWS S3, DigitalOcean Spaces, or S3-compatible service
- **Email**: SendGrid, AWS SES, or SMTP relay service

### Configuration for Production

Set environment variables for external services:

```bash
# Database (external service)
DB_HOST=db.example.com
DB_PORT=5432
DB_USERNAME=orangescrum_user
DB_PASSWORD=<strong-password>
DB_NAME=orangescrum

# Cache/Queue (external service)
REDIS_HOST=cache.example.com
REDIS_PORT=6379
REDIS_PASSWORD=<redis-password>

# Object Storage
STORAGE_ENDPOINT=https://s3.amazonaws.com
STORAGE_ACCESS_KEY=AKIAXXXXXXXXXX
STORAGE_SECRET_KEY=<secret-key>
STORAGE_BUCKET=orangescrum-production
STORAGE_REGION=us-east-1

# Email Service
EMAIL_TRANSPORT=sendgrid
EMAIL_API_KEY=SG.xxxxxxxxxx
FROM_EMAIL=noreply@orangescrum.example.com

# Security
SECURITY_SALT=<generated-hex-32>
DEBUG=false
FULL_BASE_URL=https://orangescrum.example.com
```

For detailed production deployment instructions, see [PRODUCTION_DEPLOYMENT_NATIVE.md](PRODUCTION_DEPLOYMENT_NATIVE.md).

---

## Pre-flight Verification

The deployment script performs automatic verification:

- FrankenPHP binary availability
- PostgreSQL client installation
- Database connectivity
- Seeder configuration

### Installing Dependencies

PostgreSQL client is required for database operations and seeding:

```bash
# Ubuntu/Debian
sudo apt update && sudo apt install -y postgresql-client

# macOS
brew install postgresql

# Alpine Linux
apk add postgresql-client

# Verify installation
psql --version
```

---

## Application Lifecycle

### Starting the Application

**Development/Testing Mode:**
```bash
./run.sh
```
- Output logged to terminal
- Stop with Ctrl+C
- Useful for debugging and development

**Production Mode (Daemon):**
```bash
DAEMON=true ./run.sh &
```
- Runs in background
- Manage via systemd (recommended)
- See [PRODUCTION_DEPLOYMENT_NATIVE.md](PRODUCTION_DEPLOYMENT_NATIVE.md) for systemd configuration

**Custom Port:**
```bash
PORT=9000 ./run.sh
```

### Health Verification

```bash
# HTTP connectivity test
curl -I http://localhost:8080/

# Application health check
curl http://localhost:8080/home/healthcheck
```

### Monitoring and Logs

**Application logs:**
```bash
find /tmp -maxdepth 1 -name "frankenphp_*" -type d
tail -f /tmp/frankenphp_*/logs/error.log
```

**System logs (when running as systemd service):**
```bash
journalctl -u orangescrum -f
```

---

## Troubleshooting

### Database Connectivity Issues

Verify database connectivity and credentials:

```bash
psql -h <DB_HOST> -U <DB_USERNAME> -d orangescrum -c "SELECT version();"
```

### Redis Connection Failures

Test Redis connectivity:

```bash
redis-cli -h <REDIS_HOST> -p <REDIS_PORT> PING
```

### Port Conflicts

If port 8080 is already in use, specify an alternative:

```bash
PORT=9000 ./run.sh
```

### Application HTTP 404 Errors

Verify:
1. Database migrations completed successfully
2. Database connectivity confirmed
3. Application logs for detailed error messages

### Missing PostgreSQL Client

The `psql` utility is required for database operations. Without it, database seeders cannot run and master data will not be initialized. The application will not function properly.

Install PostgreSQL client before running the deployment script.

---

## Documentation Reference

- **Production Deployment**: [PRODUCTION_DEPLOYMENT_NATIVE.md](PRODUCTION_DEPLOYMENT_NATIVE.md)
- **Docker Deployment**: [PRODUCTION_DEPLOYMENT_DOCKER.md](PRODUCTION_DEPLOYMENT_DOCKER.md)
- **Environment Configuration**: [ENVIRONMENT_CONFIGURATION.md](ENVIRONMENT_CONFIGURATION.md)
- **Production Readiness**: [PRODUCTION_READINESS_SUMMARY.md](PRODUCTION_READINESS_SUMMARY.md)

---

## System Requirements

| Component | Requirement |
|-----------|-------------|
| Operating System | Linux x86_64 (Ubuntu 20.04+, Debian 11+, RHEL 8+) |
| Memory | 2GB minimum, 4GB+ recommended |
| Disk Space | 1GB for application + database storage |
| Network Ports | 8080 (or custom port) |
| PHP | Not required (included in binary) |
| PostgreSQL | 12+ (external service) |
| Redis | 6+ (external service) |

---

## Support and Documentation

For comprehensive guidance on production deployment architecture, systemd service management, reverse proxy configuration, and SSL/TLS setup, refer to [PRODUCTION_DEPLOYMENT_NATIVE.md](PRODUCTION_DEPLOYMENT_NATIVE.md).

For all available environment variables and advanced configuration options, refer to [ENVIRONMENT_CONFIGURATION.md](ENVIRONMENT_CONFIGURATION.md).
