# FrankenPHP Deployment Organization - No More Duplication!

## Overview

The FrankenPHP deployment has been reorganized to **eliminate file duplication** while maintaining clear separation between Docker and Native deployments.

**Key Principle:** Common files live in one place (`orangescrum-cloud/`), and deployment-specific folders are **built on demand** using build scripts.

## New Structure

```
cloud-builder/
├── orangescrum-cloud/              # 📦 SOURCE OF TRUTH (common files)
│   ├── build-docker.sh             # Build Docker deployment
│   ├── build-native.sh             # Build Native deployment
│   ├── config/                     # Common configs
│   ├── docs/                       # Common docs
│   ├── Dockerfile                  # Docker-specific
│   ├── docker-compose.yaml         # Docker-specific
│   ├── entrypoint.sh               # Docker-specific
│   ├── run-native.sh               # Native-specific
│   ├── run.sh                      # Native-specific
│   ├── package.sh                  # Native-specific
│   ├── cake.sh                     # Common helper
│   ├── queue-worker.sh             # Common helper
│   ├── validate-env.sh             # Common helper
│   └── orangescrum-app/
│       └── osv4-prod               # Binary (built by build.py)
│
├── orangescrum-cloud-docker/       # 🐳 AUTO-GENERATED (do not edit)
│   └── [Built by build-docker.sh]
│
└── orangescrum-cloud-native/       # 🖥️  AUTO-GENERATED (do not edit)
    └── [Built by build-native.sh]
```

## How It Works

### 1. Build Process

```bash
cd /home/ubuntu/workspace/os-next/cloud-builder
python build.py
```

**What happens:**
1. ✓ Archives OrangeScrum V4 app
2. ✓ Builds FrankenPHP base image
3. ✓ Embeds app into FrankenPHP binary
4. ✓ Extracts binary to `orangescrum-cloud/orangescrum-app/osv4-prod`
5. ✓ **Runs `build-docker.sh`** → Creates `orangescrum-cloud-docker/`
6. ✓ **Runs `build-native.sh`** → Creates `orangescrum-cloud-native/`

### 2. What Gets Built

**build-docker.sh** assembles:
- Docker-specific: `Dockerfile`, `docker-compose.yaml`, `entrypoint.sh`, `.dockerignore`
- Common files: `config/`, `docs/`, helper scripts
- Binary: `orangescrum-app/osv4-prod`
- Output: `orangescrum-cloud-docker/`

**build-native.sh** assembles:
- Native-specific: `run-native.sh`, `run.sh`, `package.sh`, `caddy.sh`
- Common files: `config/`, `docs/`, helper scripts
- Binary: `orangescrum-app/osv4-prod`
- Output: `orangescrum-cloud-native/`

## No More Duplication! 🎉

### Before (Duplicated)
```
❌ config/ existed in 3 places
❌ docs/ existed in 3 places  
❌ Helper scripts duplicated everywhere
❌ Confusing which is the "source"
```

### After (Single Source)
```
✅ config/ in orangescrum-cloud/ only
✅ docs/ in orangescrum-cloud/ only
✅ Helper scripts in one place
✅ Clear: orangescrum-cloud/ is the source
✅ Deployment folders are auto-generated
```

## Making Changes

### Updating Common Files (config, docs, scripts)

**Edit in source folder:**
```bash
cd orangescrum-cloud/
nano config/cache_redis.example.php  # Make your changes
nano docs/DEPLOYMENT.md              # Update docs
```

**Rebuild deployment folders:**
```bash
./build-docker.sh   # Update Docker deployment
./build-native.sh   # Update Native deployment

# Or rebuild both at once
./build-docker.sh && ./build-native.sh
```

### Updating Docker-Specific Files

**Edit in source folder:**
```bash
cd orangescrum-cloud/
nano Dockerfile
nano docker-compose.yaml
nano entrypoint.sh
```

**Rebuild:**
```bash
./build-docker.sh
```

### Updating Native-Specific Files

**Edit in source folder:**
```bash
cd orangescrum-cloud/
nano run-native.sh
nano package.sh
```

**Rebuild:**
```bash
./build-native.sh
```

## Deployment Workflow

### Full Build

```bash
# Build everything from scratch
cd /home/ubuntu/workspace/os-next/cloud-builder
python build.py

# This automatically:
# 1. Builds the binary
# 2. Runs build-docker.sh
# 3. Runs build-native.sh
```

### Rebuild Deployments Only

If you've updated common files but haven't rebuilt the binary:

```bash
cd orangescrum-cloud/
./build-docker.sh && ./build-native.sh
```

### Deploy Docker

```bash
cd orangescrum-cloud-docker/
nano .env
docker-compose -f docker-compose.services.yml up -d
docker compose up -d
```

### Deploy Native

```bash
cd orangescrum-cloud-native/
cp .env.example .env
nano .env
./validate-env.sh
./run-native.sh
```

## Important Rules

### ✅ DO:
- ✅ Edit files in `orangescrum-cloud/`
- ✅ Run build scripts to update deployment folders
- ✅ Deploy from `orangescrum-cloud-docker/` or `orangescrum-cloud-native/`
- ✅ Treat deployment folders as auto-generated

### ❌ DON'T:
- ❌ Edit files in `orangescrum-cloud-docker/` or `orangescrum-cloud-native/`
- ❌ Manually copy files between folders
- ❌ Commit deployment folders to git (add to .gitignore)

## File Organization

### Source Folder (`orangescrum-cloud/`)

**Common Files** (used by both deployments):
- `config/` - Configuration templates
- `docs/` - Documentation
- `cake.sh` - CakePHP CLI helper
- `queue-worker.sh` - Queue worker
- `validate-env.sh` - Environment validator
- `.env.example` - Environment template
- `CONFIGS.md` - Configuration reference

**Docker-Specific** (copied to docker deployment):
- `Dockerfile`
- `docker-compose.yaml`
- `docker-compose.services.yml`
- `entrypoint.sh`
- `.dockerignore`
- `.env.docker`

**Native-Specific** (copied to native deployment):
- `run-native.sh`
- `run.sh`
- `package.sh`
- `caddy.sh`
- `.env.full.example`

**Build Scripts:**
- `build-docker.sh` - Builds `../orangescrum-cloud-docker/`
- `build-native.sh` - Builds `../orangescrum-cloud-native/`

**Binary:**
- `orangescrum-app/osv4-prod` - Created by `build.py`

## Benefits

### ✨ No Duplication
- Files exist in one place only
- Updates propagate to all deployments
- Smaller repository size

### ✨ Clear Organization
- Source files in `orangescrum-cloud/`
- Generated files in deployment folders
- Easy to understand what to edit

### ✨ Automated Building
- `python build.py` builds everything
- Build scripts ensure consistency
- No manual file copying

### ✨ Easy Maintenance
- Edit once, rebuild deployments
- Version control tracks source only
- Clear separation of concerns

## Migration from Old Structure

If you were using the old duplicated structure:

1. **Delete old deployment folders:**
   ```bash
   cd /home/ubuntu/workspace/os-next/cloud-builder
   rm -rf orangescrum-cloud-docker/ orangescrum-cloud-native/
   ```

2. **Rebuild everything:**
   ```bash
   python build.py
   ```

3. **Copy your .env if you had one:**
   ```bash
   # For Docker
   cp old-backup/.env orangescrum-cloud-docker/.env
   
   # For Native
   cp old-backup/.env orangescrum-cloud-native/.env
   ```

## Quick Reference

| Task | Command |
|------|---------|
| Full build | `python build.py` |
| Rebuild Docker only | `cd orangescrum-cloud && ./build-docker.sh` |
| Rebuild Native only | `cd orangescrum-cloud && ./build-native.sh` |
| Rebuild both deployments | `cd orangescrum-cloud && ./build-docker.sh && ./build-native.sh` |
| Edit common files | Edit in `orangescrum-cloud/` |
| Edit Docker files | Edit in `orangescrum-cloud/`, run `build-docker.sh` |
| Edit Native files | Edit in `orangescrum-cloud/`, run `build-native.sh` |
| Deploy Docker | `cd orangescrum-cloud-docker && docker compose up -d` |
| Deploy Native | `cd orangescrum-cloud-native && ./run-native.sh` |

---

**Remember:** `orangescrum-cloud/` is the source, deployment folders are auto-generated!

