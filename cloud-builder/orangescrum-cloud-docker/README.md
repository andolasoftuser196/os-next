# OrangeScrum Cloud - Docker Deployment Source

This directory contains **source files** for Docker deployment.

## Directory Structure

```
orangescrum-cloud-docker/
+-- Dockerfile                   # Container image definition
+-- docker-compose.yaml          # Application services
+-- docker-compose.services.yml  # Infrastructure services (dev/test)
+-- entrypoint.sh                # Container startup script
+-- .dockerignore                # Docker build exclusions
+-- .env.example                 # Docker environment template
+-- build.sh                     # Build deployment package
+-- README.md                    # This file
```

## Purpose

This folder contains Docker-specific configuration files. The `build.sh` script combines these files with common files to create a deployment-ready package in `../dist-docker/`.

## Building Deployment Package

```bash
# Build deployment package manually
./build.sh

# Output: ../dist-docker/
```

Or use the main build system:

```bash
# Build everything (binary + deployments)
python build.py

# This will automatically run build.sh
```

## Build Output

The `build.sh` script creates a deployment package by combining:

**From this folder (Docker-specific):**
- `Dockerfile`
- `docker-compose.yaml`
- `docker-compose.services.yml`
- `entrypoint.sh`
- `.dockerignore`
- `.env.example`

**From `../orangescrum-cloud-common/` (shared):**
- `config/` - Configuration templates
- `docs/` - Documentation
- `helpers/` - Helper scripts
- `orangescrum-app/osv4-prod` - FrankenPHP binary

**Output:** `../dist-docker/` - Complete, ready-to-deploy package

## Deployment

The built package in `dist-docker/` can be deployed immediately:

```bash
cd ../dist-docker
cp .env.example .env
nano .env  # Configure settings
./helpers/validate-env.sh
docker compose up -d
```

See `../dist-docker/README.md` and `../orangescrum-cloud-common/docs/PRODUCTION_DEPLOYMENT_DOCKER.md` for details.

## Development

To modify Docker deployment:

1. Edit files in this folder
2. Rebuild: `./build.sh`
3. Test: `cd ../dist-docker && docker compose up -d`

## Production Configuration

- Non-root user execution (orangescrum:1000)
- Health checks configured
- Resource limits enforced (CPU/Memory)
- Log rotation enabled
- Security validation on startup
- External database/cache/storage integration
- Dedicated queue worker service
