# OrangeScrum Cloud Builder - Quick Reference

## Directory Purpose Summary

| Directory | Purpose | Generated? | Can Delete? |
|-----------|---------|------------|-------------|
| `builder/package/` | Temp app extraction + Docker context | Yes (auto-generated) | Yes (rebuild) |
| `orangescrum-cloud-common/orangescrum-app/osv4-prod` | Built FrankenPHP binary | Yes (by build.py) | Yes (rebuild) |
| `dist-docker/` | Docker deployment package | Yes (by build.py) | Yes (rebuild) |
| `dist-native/` | Native deployment package | Yes (by build.py) | Yes (rebuild) |
| `orangescrum-cloud/` | Source build scripts | No (source) | No (keep) |
| `orangescrum-cloud-common/` | Common shared files (config, docs) | No (source) | No (keep) |
| `orangescrum-cloud-docker/` | Docker deployment source | No (source) | No (keep) |
| `orangescrum-cloud-native/` | Native deployment source | No (source) | No (keep) |
| `builder/*.Dockerfile` | Docker build configs | No (source) | No (keep) |
| `build.py` | Main build orchestrator | No (source) | No (keep) |

## Build Flow in 5 Steps

```txt
1. SOURCE (../apps/orangescrum-v4)
   ↓ git archive / tar
2. EXTRACT → builder/package/ (Docker context)
   ↓ docker build (2-stage)
3. BINARY → orangescrum-cloud-common/orangescrum-app/osv4-prod
   ↓ run build scripts
4. DEPLOY PACKAGES:
   - orangescrum-cloud-docker/build.sh → dist-docker/
   - orangescrum-cloud-native/build.sh → dist-native/
5. READY TO DEPLOY from dist-docker/ or dist-native/
```

## Common Commands

### Build (First Time - Slow ~30min)

```bash
cd cloud-builder
python3 build.py
```

Creates:
- FrankenPHP binary at `orangescrum-cloud-common/orangescrum-app/osv4-prod`
- Docker package at `dist-docker/`
- Native package at `dist-native/`

### Build (Code Changes - Fast ~2min)

```bash
python3 build.py
# Base image is cached, only app embedding runs
```

### Rebuild Deployment Packages Only

```bash
# Rebuild Docker package (if common files changed)
cd orangescrum-cloud-docker
./build.sh

# Rebuild Native package (if common files changed)
cd orangescrum-cloud-native
./build.sh
```

### Build Options

```bash
# Run pre-flight checks only (no build)
python3 build.py --check

# Force rebuild base image (slow)
python3 build.py --rebuild-base

# Skip deployment, just build binary
python3 build.py --skip-deploy

# Clean package directory before build
python3 build.py --clean

# Skip base image build (use cached)
python3 build.py --skip-base

# Skip git archive/extract step
python3 build.py --skip-archive

# Keep package directory after build (default is to delete)
python3 build.py --keep-package

# Specify custom environment file
python3 build.py --env-file /path/to/.env

# Configure application port
python3 build.py --app-port 8081

# Configure bind IP
python3 build.py --app-bind-ip 127.0.0.1

# Configure database settings
python3 build.py --db-host localhost --db-port 5432 \
  --db-username orangescrum --db-password secret --db-name orangescrum
```

### Deploy

**Docker:**
```bash
cd dist-docker
cp .env.example .env
nano .env  # Configure DB, security, etc
docker-compose -f docker-compose.services.yml up -d  # Infrastructure (optional)
docker compose up -d  # Start application
```

**Native:**
```bash
cd dist-native
cp .env.example .env
nano .env  # Configure DB, security, etc
./validate-env.sh  # Validate configuration
./run.sh  # Start application
```

## What to Commit

**DO COMMIT:**

- Scripts: `build.py`, `deploy.sh`, `*.sh`
- Configs: `*.Dockerfile`, `*.yaml`, `*.ini`
- Docs: `*.md`
- Structure: `.gitkeep` files
- Source folders: `orangescrum-cloud/`, `orangescrum-cloud-common/` (structure/config only)

**DON'T COMMIT:**

- Binary: `orangescrum-cloud-common/orangescrum-app/osv4-prod`
- Packages: `dist-docker/`, `dist-native/`
- Temp source: `builder/package/*` contents
- Env files: `.env` (except `.env.example`)

## Key Files

| File | Purpose |
|------|---------|
| `build.py` | Build orchestration script |
| `builder/base-build.Dockerfile` | Stage 1: Build FrankenPHP base (~30 min) |
| `builder/app-embed.Dockerfile` | Stage 2: Embed app into binary (~2 min) |
| `orangescrum-cloud-common/orangescrum-app/osv4-prod` | FrankenPHP binary (built) |
| `dist-docker/docker-compose.yaml` | Docker deployment orchestration |
| `dist-native/run.sh` | Native deployment runner |

## Making Changes

### Update Common Configuration Files

```bash
# Edit shared config
nano orangescrum-cloud-common/config/cache_redis.example.php

# Rebuild deployment packages
cd orangescrum-cloud-docker && ./build.sh
cd ../orangescrum-cloud-native && ./build.sh
```

### Update Docker-Specific Files

```bash
# Edit Docker files
nano orangescrum-cloud-docker/Dockerfile
nano orangescrum-cloud-docker/docker-compose.yaml

# Rebuild Docker package
cd orangescrum-cloud-docker && ./build.sh
```

### Update Native-Specific Files

```bash
# Edit Native files
nano orangescrum-cloud-native/run.sh

# Rebuild Native package
cd orangescrum-cloud-native && ./build.sh
```

### Update Application Code

```bash
# Edit code in ../apps/orangescrum-v4
# Then rebuild binary and packages
cd cloud-builder
python3 build.py
```

## Clean Everything

```bash
# Remove built binary
rm -f orangescrum-cloud-common/orangescrum-app/osv4-prod

# Remove deployment packages
rm -rf dist-docker/ dist-native/

# Remove temp files
rm -rf builder/package/*

# Rebuild from scratch
python3 build.py --clean
```

## Full Documentation

- [README.md](../README.md) - Main documentation
- [REPOSITORY_STRUCTURE.md](REPOSITORY_STRUCTURE.md) - Detailed structure
- [DEPLOYMENT_SEPARATION.md](../DEPLOYMENT_SEPARATION.md) - Architecture explanation
- [GIT_SETUP_GUIDE.md](GIT_SETUP_GUIDE.md) - Git configuration

