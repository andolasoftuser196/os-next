# OrangeScrum Cloud Builder - Production Deployment System

**Version:** v26.1.1  
**Updated:** January 17, 2026  
**Status:** Production Ready

---

## Overview

This build system creates production-ready FrankenPHP static binary deployments of OrangeScrum V4 with **clear separation** between Docker and Native deployment methods.

### What Is FrankenPHP?

FrankenPHP is a modern PHP application server that combines:
- **PHP 8.3** interpreter with all required extensions
- **Caddy** web server (HTTP/2, HTTP/3, automatic HTTPS)
- **Static binary** with embedded application code
- **Self-contained** - no external dependencies needed

### Deployment Options

1. **Docker Deployment** - Containerized with Docker Compose
   - Simplified setup and management
   - Includes infrastructure services for development
   - Recommended for most deployments

2. **Native Deployment** - Direct system execution
   - Optimized performance with lower overhead
   - systemd integration
   - Recommended for dedicated production servers

---

## Directory Structure

```
cloud-builder/
│
├── build.py                     #   Main build orchestrator
├── builder/                     # FrankenPHP build environment
│   ├── docker-compose.yaml
│   └── base-build.Dockerfile
│
├── orangescrum-cloud-common/    #  SHARED FILES (source)
│   ├── config/                  # Configuration templates
│   ├── docs/                    # Documentation
│   ├── helpers/                 # Helper scripts
│   ├── orangescrum-app/         # Binary location (after build)
│   │   └── osv4-prod           # FrankenPHP static binary
│   └── README.md
│
├── orangescrum-cloud-docker/    #  DOCKER SOURCE
│   ├── Dockerfile
│   ├── docker-compose.yaml
│   ├── entrypoint.sh
│   ├── build.sh                # Build Docker package
│   └── README.md
│
├── orangescrum-cloud-native/    #  NATIVE SOURCE
│   ├── run-native.sh
│   ├── systemd/
│   ├── build.sh                # Build Native package
│   └── README.md
│
├── dist-docker/                 #  DEPLOYMENT READY (auto-generated)
│   └── [Complete Docker package]
│
├── dist-native/                 #  DEPLOYMENT READY (auto-generated)
│   └── [Complete Native package]
│
└── docs/                        # Build system documentation
```

---

## Quick Start

### Prerequisites

- **Docker** 20.10+ and Docker Compose 2.0+
- **Python** 3.8+
- **OrangeScrum V4** source code in `../apps/orangescrum-v4`
- External **PostgreSQL** 13+, **Redis** 6+, **S3** storage

### Build Everything

```bash
cd $PROJECT_ROOT

# Build FrankenPHP binary and create deployment packages
python build.py

# This will:
# 1. Archive OrangeScrum V4 application
# 2. Build FrankenPHP base image (if needed)
# 3. Embed app into FrankenPHP binary
# 4. Extract binary to orangescrum-cloud-common/
# 5. Build Docker deployment package → dist-docker/
# 6. Build Native deployment package → dist-native/
```

### Deploy (Docker)

```bash
cd dist-docker
cp .env.example .env
nano .env  # Configure database, Redis, S3, security

./helpers/validate-env.sh  # Verify configuration
docker compose up -d       # Start application
```

### Deploy (Native)

```bash
cd dist-native
cp .env.example .env
nano .env  # Configure database, Redis, S3, security

./helpers/validate-env.sh  # Verify configuration

# Development
./run-native.sh

# Production (systemd)
sudo cp systemd/*.service /etc/systemd/system/
sudo systemctl enable orangescrum orangescrum-queue
sudo systemctl start orangescrum
```

---

## Build System Workflow

### Phase 1: Build Binary (build.py)

```
1. Archive app → builder/repo.tar
2. Build/verify base image → orangescrum-cloud-base:latest
3. Embed app + build binary
4. Extract binary → orangescrum-cloud-common/orangescrum-app/osv4-prod
```

### Phase 2: Build Deployment Packages

```
5. Docker build → orangescrum-cloud-docker/build.sh
   - Combine Docker-specific files + common files
   - Copy FrankenPHP binary
   - Output → dist-docker/

6. Native build → orangescrum-cloud-native/build.sh
   - Combine Native-specific files + common files
   - Copy and rename binary to bin/orangescrum
   - Output → dist-native/
```

---

## Production Readiness

###  Security

- [x] Environment validation (validates on startup)
- [x] Non-root execution (Docker: orangescrum:1000, Native: dedicated user)
- [x] Security salt enforcement
- [x] Password strength validation
- [x] Default value detection and rejection

###  Architecture

- [x] Stateless application (no local file storage)
- [x] External PostgreSQL database
- [x] External Redis cache and queue
- [x] S3-compatible storage for uploads
- [x] Horizontal scaling ready

###  Deployment

- [x] Docker deployment with compose
- [x] Native deployment with systemd
- [x] Health checks configured
- [x] Resource limits set
- [x] Log rotation configured
- [x] Graceful shutdown handling

###  Documentation

- [x] Complete production deployment guides
- [x] Security best practices
- [x] Configuration reference
- [x] Troubleshooting guides
- [x] Clear separation of deployment types

###  Recommended Before Production

- [ ] Set up external managed PostgreSQL (RDS, Cloud SQL, etc.)
- [ ] Set up external managed Redis (ElastiCache, Cloud Memorystore, etc.)
- [ ] Configure S3 bucket with IAM policies
- [ ] Set up reverse proxy (nginx/Apache) with SSL
- [ ] Configure monitoring and alerting
- [ ] Set up automated backups
- [ ] Test disaster recovery procedure

---

## Build Options

```bash
# Full build (default)
python build.py

# Skip deployment (build binary only)
python build.py --skip-deploy

# Skip base image build (if already exists)
python build.py --skip-base

# Rebuild base image from scratch
python build.py --rebuild-base

# Keep package directory for debugging
python build.py --keep-package

# Build and deploy immediately
python build.py  # Starts Docker deployment after build

# Custom environment file
python build.py --env-file /path/to/.env

# Check prerequisites only
python build.py --check
```

---

## Manual Package Building

If you only want to rebuild deployment packages (binary already built):

```bash
# Rebuild Docker package
cd orangescrum-cloud-docker
./build.sh
# Output: ../dist-docker/

# Rebuild Native package
cd orangescrum-cloud-native
./build.sh
# Output: ../dist-native/
```

---

## Distribution Packages

To create distribution tarballs:

```bash
# Build packages first
python build.py --skip-deploy

# Create tarballs (future feature)
# cd orangescrum-cloud-docker && ./dist.sh
# cd orangescrum-cloud-native && ./dist.sh
```

---

## Folder Purposes

| Folder | Purpose | Edit? |
|--------|---------|-------|
| `orangescrum-cloud-common/` | Shared files (configs, docs, helpers) |  Yes (source) |
| `orangescrum-cloud-docker/` | Docker-specific source files |  Yes (source) |
| `orangescrum-cloud-native/` | Native-specific source files |  Yes (source) |
| `dist-docker/` | Docker deployment package |  No (auto-generated) |
| `dist-native/` | Native deployment package |  No (auto-generated) |
| `builder/` | FrankenPHP build environment |  Advanced only |

---

## Making Changes

### Update Configuration Templates

```bash
# Edit common configs
cd orangescrum-cloud-common
nano config/redis.example.php

# Rebuild packages
cd ../orangescrum-cloud-docker && ./build.sh
cd ../orangescrum-cloud-native && ./build.sh
```

### Update Docker Deployment

```bash
cd orangescrum-cloud-docker
nano docker-compose.yaml  # Make changes
./build.sh                # Rebuild package
cd ../dist-docker         # Test deployment
```

### Update Native Deployment

```bash
cd orangescrum-cloud-native
nano systemd/orangescrum.service  # Make changes
./build.sh                         # Rebuild package
cd ../dist-native                  # Test deployment
```

---

## Troubleshooting

### Binary Not Found

```bash
# Check if binary exists
ls -lh orangescrum-cloud-common/orangescrum-app/osv4-prod

# If missing, rebuild
python build.py
```

### Build Fails

```bash
# Check prerequisites
python build.py --check

# Clean and rebuild
docker compose -f builder/docker-compose.yaml down -v
python build.py --rebuild-base
```

### Deployment Package Missing

```bash
# Check dist folders
ls -la dist-docker/
ls -la dist-native/

# Rebuild packages
cd orangescrum-cloud-docker && ./build.sh
cd orangescrum-cloud-native && ./build.sh
```

---

## Support

- **Documentation**: See `orangescrum-cloud-common/docs/`
- **Docker Guide**: `orangescrum-cloud-common/docs/PRODUCTION_DEPLOYMENT_DOCKER.md`
- **Native Guide**: `orangescrum-cloud-common/docs/PRODUCTION_DEPLOYMENT_NATIVE.md`
- **Production Readiness**: `orangescrum-cloud-common/docs/PRODUCTION_READINESS_SUMMARY.md`

---

## Migration from Old Structure

If you have the old `orangescrum-cloud/` folder with mixed files:

```bash
# Old structure is preserved as backup
# New structure is now:
# - orangescrum-cloud-common/  (shared)
# - orangescrum-cloud-docker/  (Docker source)
# - orangescrum-cloud-native/  (Native source)
# - dist-docker/               (Docker deployment)
# - dist-native/               (Native deployment)

# To use new structure:
python build.py
# Deployment packages are now in dist-docker/ and dist-native/
```

---

## License

See OrangeScrum application license.
