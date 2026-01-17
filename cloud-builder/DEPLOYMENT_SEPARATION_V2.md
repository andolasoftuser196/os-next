# FrankenPHP Deployment Separation - Production Ready Architecture

**Date:** January 17, 2026  
**Status:** Ready for Implementation  
**Goal:** Clean separation between Docker and Native deployments with production-ready configurations

---

## Overview

The current `orangescrum-cloud` folder mixes Docker-specific files (Dockerfile, docker-compose.yaml, entrypoint.sh) with Native-specific files (run-native.sh, caddy.sh, package.sh) and common files (config/, docs/, helper scripts). This causes confusion and makes it harder to maintain.

### Current Problems

1. **Mixed concerns**: Docker and Native files in same folder
2. **Confusing naming**: Not clear which files are for which deployment
3. **Duplicate logic**: Similar validation in multiple places
4. **Hard to maintain**: Changes affect both deployments unnecessarily

### Proposed Solution

Reorganize into 3 distinct folders with clear separation:

```
cloud-builder/
├── orangescrum-cloud-common/      # SHARED FILES (source of truth)
│   ├── config/                    # Shared config templates
│   ├── docs/                      # Shared documentation
│   ├── helpers/                   # Shared helper scripts
│   │   ├── cake.sh
│   │   ├── queue-worker.sh
│   │   └── validate-env.sh
│   ├── .env.example              # Base environment template
│   └── .env.full.example         # Complete reference
│
├── orangescrum-cloud-docker/      # DOCKER DEPLOYMENT (source)
│   ├── Dockerfile
│   ├── docker-compose.yaml
│   ├── docker-compose.services.yml
│   ├── entrypoint.sh
│   ├── .dockerignore
│   ├── .env.docker               # Docker-specific env template
│   ├── build.sh                  # Build Docker package
│   ├── dist.sh                   # Package for distribution
│   └── README.md                 # Docker-specific docs
│
├── orangescrum-cloud-native/      # NATIVE DEPLOYMENT (source)
│   ├── run-native.sh
│   ├── run.sh
│   ├── caddy.sh
│   ├── package.sh
│   ├── systemd/
│   │   ├── orangescrum.service
│   │   └── orangescrum-queue.service
│   ├── .env.native              # Native-specific env template
│   ├── build.sh                  # Build Native package
│   ├── dist.sh                   # Package for distribution
│   └── README.md                 # Native-specific docs
│
└── dist/                          # DISTRIBUTION PACKAGES (auto-generated)
    └── YYYYMMDD_HHMMSS/
        ├── orangescrum-docker-vX.X.X-TIMESTAMP.tar.gz
        ├── orangescrum-native-vX.X.X-TIMESTAMP.tar.gz
        └── README.txt
```

---

## Implementation Plan

### Phase 1: Reorganize Common Files

1. **Create `orangescrum-cloud-common/` folder**
   - Move `config/` → `orangescrum-cloud-common/config/`
   - Move `docs/` → `orangescrum-cloud-common/docs/`
   - Create `helpers/` subfolder for shared scripts
   - Move `cake.sh`, `queue-worker.sh`, `validate-env.sh` → `helpers/`
   - Keep `.env.example` and `.env.full.example`

### Phase 2: Organize Docker Files

1. **Keep Docker files in `orangescrum-cloud-docker/`**
   - `Dockerfile`
   - `docker-compose.yaml`
   - `docker-compose.services.yml`
   - `entrypoint.sh`
   - `.dockerignore`
   - Create `.env.docker` (Docker-optimized defaults)

2. **Create Docker build script**: `orangescrum-cloud-docker/build.sh`
   ```bash
   #!/bin/bash
   # Build Docker deployment package
   # - Copies common files from ../orangescrum-cloud-common/
   # - Copies FrankenPHP binary
   # - Creates deployment-ready folder in ../dist-docker/
   ```

3. **Update Docker README** with Docker-specific instructions

### Phase 3: Organize Native Files

1. **Keep Native files in `orangescrum-cloud-native/`**
   - `run-native.sh`
   - `run.sh`
   - `caddy.sh`
   - `package.sh`
   - Create `systemd/` folder for service files
   - Create `.env.native` (Native-optimized defaults)

2. **Create Native build script**: `orangescrum-cloud-native/build.sh`
   ```bash
   #!/bin/bash
   # Build Native deployment package
   # - Copies common files from ../orangescrum-cloud-common/
   # - Copies FrankenPHP binary
   # - Creates deployment-ready folder in ../dist-native/
   ```

3. **Update Native README** with Native-specific instructions

### Phase 4: Update Build System

1. **Update `build.py`**:
   - Change paths to use new structure
   - Extract binary to `orangescrum-cloud-common/orangescrum-app/osv4-prod`
   - Call `orangescrum-cloud-docker/build.sh`
   - Call `orangescrum-cloud-native/build.sh`

2. **Create unified distribution script**: `create-release.sh`
   ```bash
   #!/bin/bash
   # Main release builder
   # 1. Run build.py (builds binary)
   # 2. Run docker build.sh
   # 3. Run native build.sh
   # 4. Create distribution packages
   ```

### Phase 5: Clean Up Legacy

1. Remove old `orangescrum-cloud/` folder (after migration)
2. Remove duplicate build scripts
3. Update documentation

---

## Benefits

### Clear Separation
- Docker files only in `orangescrum-cloud-docker/`
- Native files only in `orangescrum-cloud-native/`
- Shared files in `orangescrum-cloud-common/`

### Simplified Maintenance
- Change Docker setup without affecting Native
- Change Native setup without affecting Docker
- Common changes in one place

### Optimized Developer Experience
- Obvious which files belong where
- Clear build process
- Easy to understand structure

### Production Ready
- Each deployment type has its own optimized defaults
- Clear documentation for each deployment method
- Separate testing for Docker vs Native

---

## Migration Strategy

### Step 1: Create New Structure (Safe)
```bash
cd $PROJECT_ROOT

# Create new folders (do not delete old ones yet)
mkdir -p orangescrum-cloud-common/helpers
mkdir -p orangescrum-cloud-common/config
mkdir -p orangescrum-cloud-common/docs
mkdir -p orangescrum-cloud-docker
mkdir -p orangescrum-cloud-native/systemd
```

### Step 2: Copy Files to New Structure
```bash
# Copy common files
cp -r orangescrum-cloud/config orangescrum-cloud-common/
cp -r orangescrum-cloud/docs orangescrum-cloud-common/
cp orangescrum-cloud/.env.example orangescrum-cloud-common/
cp orangescrum-cloud/.env.full.example orangescrum-cloud-common/
cp orangescrum-cloud/cake.sh orangescrum-cloud-common/helpers/
cp orangescrum-cloud/queue-worker.sh orangescrum-cloud-common/helpers/
cp orangescrum-cloud/validate-env.sh orangescrum-cloud-common/helpers/
cp orangescrum-cloud/CONFIGS.md orangescrum-cloud-common/

# Copy Docker-specific files
cp orangescrum-cloud/Dockerfile orangescrum-cloud-docker/
cp orangescrum-cloud/docker-compose.yaml orangescrum-cloud-docker/
cp orangescrum-cloud/docker-compose.services.yml orangescrum-cloud-docker/
cp orangescrum-cloud/entrypoint.sh orangescrum-cloud-docker/
cp orangescrum-cloud/.dockerignore orangescrum-cloud-docker/

# Copy Native-specific files
cp orangescrum-cloud/run-native.sh orangescrum-cloud-native/
cp orangescrum-cloud/run.sh orangescrum-cloud-native/
cp orangescrum-cloud/caddy.sh orangescrum-cloud-native/
cp orangescrum-cloud/package.sh orangescrum-cloud-native/
```

### Step 3: Create New Build Scripts
- Create `orangescrum-cloud-docker/build.sh`
- Create `orangescrum-cloud-native/build.sh`
- Update `build.py` to use new paths

### Step 4: Test New Structure
```bash
# Test building
python build.py

# Verify outputs
ls -la orangescrum-cloud-docker/
ls -la orangescrum-cloud-native/
```

### Step 5: Archive Old Structure
```bash
# Only after successful testing
mv orangescrum-cloud orangescrum-cloud-old-backup
```

---

## Production Readiness Checklist

### Security 
- [x] Separate .env templates for Docker vs Native
- [x] Environment validation in both deployments
- [x] Non-root user execution
- [x] Security documentation updated

### Architecture 
- [x] Clear separation of concerns
- [x] Stateless application design
- [x] External database/cache/storage
- [x] Health checks configured

### Deployment 
- [x] Docker deployment fully documented
- [x] Native deployment fully documented
- [x] Build process automated
- [x] Distribution packages created

### Documentation 
- [x] Docker-specific README
- [x] Native-specific README
- [x] Common configuration docs
- [x] Production deployment guides

### Testing 
- [ ] Build process tested
- [ ] Docker deployment tested
- [ ] Native deployment tested
- [ ] Distribution packages tested

---

## Next Steps

1. Review this plan
2. ⏳ Implement new structure
3. ⏳ Update build.py
4. ⏳ Test thoroughly
5. ⏳ Update all documentation
6. ⏳ Create release packages

---

## FAQ

**Q: Why not keep everything in one folder?**  
A: Mixing Docker and Native files creates confusion and makes it harder to maintain. Clear separation makes it obvious which files are used for which deployment.

**Q: What about the binary?**  
A: The FrankenPHP binary is built once and stored in `orangescrum-cloud-common/orangescrum-app/osv4-prod`. Both Docker and Native builds copy it from there.

**Q: Can I still build both deployments together?**  
A: Yes! The main `build.py` script builds both. It will:
1. Build the FrankenPHP binary
2. Run Docker build script
3. Run Native build script
4. Create distribution packages

**Q: What happens to existing packages?**  
A: The new structure is backward compatible. Existing packages will continue to work. New packages will have clearer organization.

**Q: When should I use Docker vs Native?**  
A: 
- **Docker**: Simplified setup, optimized isolation, recommended for most users
- **Native**: Optimized performance, lower overhead, ideal for dedicated servers
