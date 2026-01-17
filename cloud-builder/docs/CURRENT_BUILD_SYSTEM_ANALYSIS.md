# Current Build System - Detailed Analysis

**Generated:** January 17, 2026  
**Purpose:** Complete documentation of how the build system currently works

---

## Executive Summary

The build system creates a standalone FrankenPHP binary with embedded OrangeScrum V4 application, then packages it into two deployment formats:
- **Docker deployment** - Containerized with docker-compose
- **Native deployment** - Direct system execution

**Current Issue Discovered:** Binary is in legacy location `orangescrum-cloud/` instead of intended `orangescrum-cloud-common/` location.

---

## Directory Structure (Current State)

```
cloud-builder/
├── build.py                           # Main orchestrator - builds binary + packages
├── builder/                           # FrankenPHP build environment
│   ├── base-build.Dockerfile          # Stage 1: Build FrankenPHP base (~30 min)
│   ├── app-embed.Dockerfile           # Stage 2: Embed app into binary (~2 min)
│   ├── docker-compose.yaml            # Build orchestration
│   ├── Caddyfile                      # Caddy web server config
│   ├── php.ini                        # PHP configuration
│   └── package/                       # TEMP: Extracted app source for Docker build
│
├── orangescrum-cloud/                 # LEGACY: Build scripts (being phased out)
│   ├── orangescrum-app/               # ⚠️ CURRENT BINARY LOCATION (should move)
│   │   └── osv4-prod                  # 371 MB binary (WRONG LOCATION)
│   ├── build-docker.sh                # Builds Docker deployment
│   ├── build-native.sh                # Builds Native deployment
│   ├── dist-docker.sh                 # Creates Docker tarball
│   ├── dist-native.sh                 # Creates Native tarball
│   ├── Dockerfile                     # Docker-specific
│   ├── docker-compose.yaml            # Docker-specific
│   ├── entrypoint.sh                  # Docker-specific
│   ├── run.sh                         # Native-specific
│   └── package.sh                     # Native-specific
│
├── orangescrum-cloud-common/          # INTENDED: Shared files source
│   ├── orangescrum-app/               # ⚠️ MISSING - Should contain binary
│   │   └── osv4-prod                  # Should be here (currently missing)
│   ├── config/                        # Configuration templates
│   │   ├── cache_*.example.php
│   │   ├── storage.example.php
│   │   ├── smtp.example.php
│   │   └── queue.example.php
│   ├── docs/                          # Shared documentation
│   ├── helpers/                       # Helper scripts
│   │   ├── cake.sh
│   │   ├── queue-worker.sh
│   │   └── validate-env.sh
│   ├── .env.example
│   ├── .env.full.example
│   └── CONFIGS.md
│
├── orangescrum-cloud-docker/          # SOURCE: Docker assembly scripts
│   ├── build.sh                       # Assembles dist-docker/ from common + docker files
│   ├── Dockerfile
│   ├── docker-compose.yaml
│   ├── docker-compose.services.yml
│   ├── entrypoint.sh
│   └── .env.example
│
├── orangescrum-cloud-native/          # SOURCE: Native assembly scripts
│   ├── build.sh                       # Assembles dist-native/ from common + native files
│   ├── run.sh
│   ├── package.sh
│   ├── caddy.sh
│   ├── .env.example
│   └── systemd/
│
├── dist-docker/                       # OUTPUT: Docker deployment package (auto-generated)
│   ├── Dockerfile
│   ├── docker-compose.yaml
│   ├── docker-compose.services.yml
│   ├── entrypoint.sh
│   ├── orangescrum-app/               # Binary should be copied here
│   ├── config/                        # Copied from common
│   ├── docs/                          # Copied from common
│   ├── helpers/                       # Copied from common
│   └── .env.example
│
└── dist-native/                       # OUTPUT: Native deployment package (auto-generated)
    ├── run.sh
    ├── package.sh
    ├── caddy.sh
    ├── orangescrum-app/               # Binary should be copied here
    ├── config/                        # Copied from common
    ├── docs/                          # Copied from common
    ├── helpers/                       # Copied from common
    ├── systemd/
    └── .env.example
```

---

## Build Process Flow

### Complete Build Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ INPUT: ../apps/orangescrum-v4/                                  │
│ - OrangeScrum V4 PHP application                                │
│ - CakePHP framework structure                                   │
│ - index.php, config/, src/, webroot/, vendor/                   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                    python3 build.py
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 1: Archive Application                                     │
│ - git archive (if .git exists) OR tar with exclusions           │
│ - Creates: builder/repo.tar                                     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 2: Extract to Package Directory                            │
│ - Extracts tar to: builder/package/                             │
│ - Copies config overrides from: orangescrum-cloud-common/config/│
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 3: Build FrankenPHP Base Image (if needed)                 │
│ - Uses: builder/base-build.Dockerfile                           │
│ - Docker Compose: builder/docker-compose.yaml                   │
│ - Profile: base-build                                           │
│ - Time: ~30 minutes (first time only, then cached)              │
│ - Output: Docker image "orangescrum-cloud-base:latest"          │
│                                                                 │
│ Contains:                                                       │
│ - FrankenPHP from source                                        │
│ - PHP 8.3 + extensions                                          │
│ - Caddy web server                                              │
│ - Static compilation                                            │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 4: Embed Application into Binary                           │
│ - Uses: builder/app-embed.Dockerfile                            │
│ - Docker Compose: builder/docker-compose.yaml                   │
│ - Service: orangescrum-app-builder                              │
│ - Time: ~2 minutes                                              │
│ - Embeds builder/package/ into FrankenPHP                       │
│ - Output: Binary in container at /go/src/app/dist/frankenphp-*  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 5: Extract Binary from Container                           │
│ - Starts orangescrum-app-builder container                      │
│ - Extracts binary via Docker API                                │
│ - Renames: frankenphp-linux-x86_64 → osv4-prod                  │
│ - Sets permissions: chmod 755                                   │
│                                                                 │
│ CURRENT: Saves to orangescrum-cloud/orangescrum-app/osv4-prod   │
│ INTENDED: Should save to orangescrum-cloud-common/...           │
│                                                                 │
│ Size: ~371 MB (340 MB typical)                                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 6: Build Deployment Packages                               │
│                                                                 │
│ A) Docker Package                                               │
│    - Script: orangescrum-cloud-docker/build.sh                  │
│    - Output: dist-docker/                                       │
│                                                                 │
│ B) Native Package                                               │
│    - Script: orangescrum-cloud-native/build.sh                  │
│    - Output: dist-native/                                       │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ FINAL OUTPUT                                                    │
│                                                                 │
│ dist-docker/                - Ready for Docker deployment       │
│ dist-native/                - Ready for native deployment       │
│                                                                 │
│ Both contain:                                                   │
│ - FrankenPHP binary (osv4-prod)                                 │
│ - Configuration templates                                       │
│ - Helper scripts                                                │
│ - Documentation                                                 │
│ - Deployment scripts                                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Build.py Detailed Analysis

### Key Variables (build.py lines 38-62)

```python
# Source paths
ROOT = Path(__file__).parent.resolve()
REPO = (ROOT / "../apps/orangescrum-v4").resolve()
BUILDER = ROOT / "builder"
PACKAGE = BUILDER / "package"

# Common source
ORANGESCRUM_COMMON_DIR = ROOT / "orangescrum-cloud-common"

# Deployment sources
ORANGESCRUM_DOCKER_SOURCE = ROOT / "orangescrum-cloud-docker"
ORANGESCRUM_NATIVE_SOURCE = ROOT / "orangescrum-cloud-native"

# Output directories
DIST_DOCKER_DIR = ROOT / "dist-docker"
DIST_NATIVE_DIR = ROOT / "dist-native"

# Binary location (INTENDED)
COMMON_BINARY = ORANGESCRUM_COMMON_DIR / "orangescrum-app/osv4-prod"
```

### Critical Functions

#### 1. `_copy_frankenphp_binary()` - Lines 300-343
```python
def _copy_frankenphp_binary(docker_client: docker.DockerClient):
    """Extract binary from builder container"""
    
    # Create output directory in NEW common location
    common_binary_dir = ORANGESCRUM_COMMON_DIR / "orangescrum-app"
    common_binary_dir.mkdir(parents=True, exist_ok=True)
    common_binary = common_binary_dir / "osv4-prod"
    
    # Get container and extract binary
    container = docker_client.containers.get(container_id)
    bits, _ = container.get_archive("/go/src/app/dist/frankenphp-linux-x86_64")
    
    # Extract and rename
    tar_stream = io.BytesIO(b"".join(bits))
    with tarfile.open(fileobj=tar_stream) as tar:
        tar.extractall(path=common_binary_dir)
    
    extracted_binary = common_binary_dir / "frankenphp-linux-x86_64"
    extracted_binary.rename(common_binary)
    common_binary.chmod(0o755)
```

**ISSUE:** Code is correct but actual binary ends up in `orangescrum-cloud/orangescrum-app/` instead.

#### 2. `_build_deployment_folders()` - Lines 415-444
```python
def _build_deployment_folders():
    """Build deployment folders using separated build scripts"""
    
    # Run Docker build script
    docker_build_script = ORANGESCRUM_DOCKER_SOURCE / "build.sh"
    if docker_build_script.exists():
        _run_cmd(["bash", str(docker_build_script)], cwd=ORANGESCRUM_DOCKER_SOURCE)
    
    # Run Native build script
    native_build_script = ORANGESCRUM_NATIVE_SOURCE / "build.sh"
    if native_build_script.exists():
        _run_cmd(["bash", str(native_build_script)], cwd=ORANGESCRUM_NATIVE_SOURCE)
```

---

## Docker Deployment Package Build

### Script: orangescrum-cloud-docker/build.sh

**Purpose:** Assembles complete Docker deployment package

**Input Sources:**
1. `orangescrum-cloud-common/` - Shared files
2. `orangescrum-cloud/` - Docker-specific files (Dockerfile, compose files)

**Output:** `dist-docker/`

### Build Process

```bash
#!/bin/bash
set -e

# Configuration
BUILDER_ROOT="$(dirname "$SCRIPT_DIR")"  # cloud-builder/
COMMON_DIR="$BUILDER_ROOT/orangescrum-cloud-common"
DOCKER_SOURCE="$SCRIPT_DIR"              # orangescrum-cloud-docker/
OUTPUT_DIR="$BUILDER_ROOT/dist-docker"

# Step 1: Validate
if [ ! -d "$COMMON_DIR" ]; then
    echo "ERROR: Common files not found"
    exit 1
fi

# Step 2: Check for binary
BINARY="$COMMON_DIR/orangescrum-app/osv4-prod"
if [ ! -f "$BINARY" ]; then
    echo "WARNING: Binary not found"
    BINARY_EXISTS=false
else
    BINARY_EXISTS=true
fi

# Step 3: Create output directory
mkdir -p "$OUTPUT_DIR"

# Step 4: Copy Docker-specific files
cp Dockerfile "$OUTPUT_DIR/"
cp docker-compose.yaml "$OUTPUT_DIR/"
cp docker-compose.services.yml "$OUTPUT_DIR/"
cp entrypoint.sh "$OUTPUT_DIR/"
cp .dockerignore "$OUTPUT_DIR/"
cp .env.example "$OUTPUT_DIR/"

# Step 5: Copy common files
cp -r "$COMMON_DIR/config" "$OUTPUT_DIR/"
cp -r "$COMMON_DIR/docs" "$OUTPUT_DIR/"
mkdir -p "$OUTPUT_DIR/helpers"
cp "$COMMON_DIR/helpers"/*.sh "$OUTPUT_DIR/helpers/"
cp "$COMMON_DIR/CONFIGS.md" "$OUTPUT_DIR/"

# Step 6: Copy binary (if exists)
if [ "$BINARY_EXISTS" = true ]; then
    mkdir -p "$OUTPUT_DIR/orangescrum-app"
    cp "$BINARY" "$OUTPUT_DIR/orangescrum-app/"
    chmod +x "$OUTPUT_DIR/orangescrum-app/osv4-prod"
fi

# Step 7: Create README
cat > "$OUTPUT_DIR/README.md" << 'EOF'
# OrangeScrum Docker Deployment Package
[deployment instructions]
EOF

# Step 8: Create build manifest
cat > "$OUTPUT_DIR/.build-manifest.txt" << EOF
Build Date: $(date)
Version: $VERSION
Timestamp: $TIMESTAMP
Binary: $([ "$BINARY_EXISTS" = true ] && echo "Included" || echo "Not included")
EOF
```

### Result: dist-docker/

```
dist-docker/
├── Dockerfile                         # Docker container definition
├── docker-compose.yaml                # App orchestration
├── docker-compose.services.yml        # Infrastructure (PostgreSQL, Redis, MinIO)
├── entrypoint.sh                      # Container startup script
├── .dockerignore                      # Docker build exclusions
├── .env.example                       # Environment template
├── config/                            # From common
│   ├── cache_*.example.php
│   ├── storage.example.php
│   └── ...
├── docs/                              # From common
│   ├── PRODUCTION_DEPLOYMENT_DOCKER.md
│   └── ...
├── helpers/                           # From common
│   ├── cake.sh
│   ├── queue-worker.sh
│   └── validate-env.sh
├── orangescrum-app/                   # Binary directory
│   └── osv4-prod                      # 371 MB executable
├── CONFIGS.md                         # From common
├── README.md                          # Generated by build.sh
└── .build-manifest.txt                # Build metadata
```

---

## Native Deployment Package Build

### Script: orangescrum-cloud-native/build.sh

**Purpose:** Assembles complete Native deployment package

**Input Sources:**
1. `orangescrum-cloud-common/` - Shared files
2. `orangescrum-cloud/` - Native-specific files (run scripts)

**Output:** `dist-native/`

### Build Process

```bash
#!/bin/bash
set -e

# Configuration
BUILDER_ROOT="$(dirname "$SCRIPT_DIR")"  # cloud-builder/
COMMON_DIR="$BUILDER_ROOT/orangescrum-cloud-common"
NATIVE_SOURCE="$SCRIPT_DIR"              # orangescrum-cloud-native/
OUTPUT_DIR="$BUILDER_ROOT/dist-native"

# Step 1: Validate
if [ ! -d "$COMMON_DIR" ]; then
    echo "ERROR: Common files not found"
    exit 1
fi

# Step 2: Check for binary
BINARY="$COMMON_DIR/orangescrum-app/osv4-prod"
if [ ! -f "$BINARY" ]; then
    echo "WARNING: Binary not found"
    BINARY_EXISTS=false
else
    BINARY_EXISTS=true
fi

# Step 3: Create output directory
mkdir -p "$OUTPUT_DIR"

# Step 4: Copy Native-specific files
cp run.sh "$OUTPUT_DIR/"
cp run.sh "$OUTPUT_DIR/"
cp package.sh "$OUTPUT_DIR/"
cp caddy.sh "$OUTPUT_DIR/"
cp .env.example "$OUTPUT_DIR/"
cp -r systemd "$OUTPUT_DIR/"

# Step 5: Copy common files
cp -r "$COMMON_DIR/config" "$OUTPUT_DIR/"
cp -r "$COMMON_DIR/docs" "$OUTPUT_DIR/"
mkdir -p "$OUTPUT_DIR/helpers"
cp "$COMMON_DIR/helpers"/*.sh "$OUTPUT_DIR/helpers/"
cp "$COMMON_DIR/CONFIGS.md" "$OUTPUT_DIR/"

# Step 6: Copy binary (if exists)
if [ "$BINARY_EXISTS" = true ]; then
    mkdir -p "$OUTPUT_DIR/orangescrum-app"
    cp "$BINARY" "$OUTPUT_DIR/orangescrum-app/"
    chmod +x "$OUTPUT_DIR/orangescrum-app/osv4-prod"
fi

# Step 7: Create bin directory symlink
mkdir -p "$OUTPUT_DIR/bin"
if [ "$BINARY_EXISTS" = true ]; then
    ln -sf ../orangescrum-app/osv4-prod "$OUTPUT_DIR/bin/osv4-prod"
fi

# Step 8: Create README and manifest
# Similar to Docker build
```

### Result: dist-native/

```
dist-native/
├── run.sh                             # Main runner (daemon support)
├── run.sh                             # Alternative runner
├── package.sh                         # Packaging script
├── caddy.sh                           # Caddy helper
├── .env.example                       # Environment template
├── config/                            # From common
├── docs/                              # From common
├── helpers/                           # From common
├── systemd/                           # Systemd service files
│   ├── orangescrum.service
│   └── orangescrum-queue-worker.service
├── bin/                               # Symlinks to binary
│   └── osv4-prod -> ../orangescrum-app/osv4-prod
├── orangescrum-app/                   # Binary directory
│   └── osv4-prod                      # 371 MB executable
├── CONFIGS.md                         # From common
├── README.md                          # Generated by build.sh
└── .build-manifest.txt                # Build metadata
```

---

## Current Issues & Discrepancies

### 1. Binary Location Mismatch

**Expected (per code):**
```
orangescrum-cloud-common/orangescrum-app/osv4-prod
```

**Actual (current state):**
```
orangescrum-cloud/orangescrum-app/osv4-prod  (371 MB)
```

**Impact:**
- Build scripts look for binary in `orangescrum-cloud-common/` 
- Binary not found during deployment package builds
- Packages are created WITHOUT binary (warning shown)
- Manual intervention needed to deploy

**Root Cause:** Unknown - possibly:
- Previous version of build.py saved to old location
- Manual copy to old location
- Legacy code path still active somewhere

### 2. Git Tracking

**Should be tracked (source files):**
- `orangescrum-cloud/` - Build orchestration scripts ✓
- `orangescrum-cloud-common/` - Shared config/docs ✓
- `orangescrum-cloud-docker/` - Docker source files ✗ (currently untracked)
- `orangescrum-cloud-native/` - Native source files ✗ (currently untracked)

**Should be ignored (generated files):**
- `orangescrum-cloud-common/orangescrum-app/osv4-prod` - Binary ✓
- `dist-docker/` - Generated package ✓
- `dist-native/` - Generated package ✓
- `builder/package/` - Temporary build files ✓

---

## File Flow Summary

### Common Files (Shared by Both Deployments)

```
orangescrum-cloud-common/
├── config/          → Copied to both dist-docker/ and dist-native/
├── docs/            → Copied to both dist-docker/ and dist-native/
├── helpers/         → Copied to both dist-docker/ and dist-native/
├── CONFIGS.md       → Copied to both dist-docker/ and dist-native/
└── orangescrum-app/ → Binary copied to both dist-docker/ and dist-native/
    └── osv4-prod
```

### Docker-Specific Files

```
orangescrum-cloud/               (SOURCE)
├── Dockerfile                   → dist-docker/Dockerfile
├── docker-compose.yaml          → dist-docker/docker-compose.yaml
├── docker-compose.services.yml  → dist-docker/docker-compose.services.yml
├── entrypoint.sh                → dist-docker/entrypoint.sh
└── .dockerignore                → dist-docker/.dockerignore
```

### Native-Specific Files

```
orangescrum-cloud/               (SOURCE)
├── run.sh                       → dist-native/run.sh
├── run.sh                       → dist-native/run.sh
├── package.sh                   → dist-native/package.sh
├── caddy.sh                     → dist-native/caddy.sh
└── systemd/                     → dist-native/systemd/
```

---

## Build Command Examples

### Full Build
```bash
cd cloud-builder
python3 build.py
```

**Output:**
- `orangescrum-cloud-common/orangescrum-app/osv4-prod` (binary)
- `dist-docker/` (complete Docker package)
- `dist-native/` (complete Native package)

**Time:** ~30 min (first time), ~2 min (subsequent)

### Build Binary Only
```bash
python3 build.py --skip-deploy
```

**Output:**
- `orangescrum-cloud-common/orangescrum-app/osv4-prod` (binary only)

### Rebuild Packages Only
```bash
# If binary exists but packages need updating
cd orangescrum-cloud-docker
./build.sh

cd ../orangescrum-cloud-native
./build.sh
```

### Clean Build
```bash
python3 build.py --clean
```

**Effect:** Deletes `builder/package/` before building

---

## Deployment Package Usage

### Docker Deployment

```bash
cd dist-docker

# Configure
cp .env.example .env
nano .env  # Set DB_HOST, DB_PASSWORD, SECURITY_SALT, etc.

# Optional: Start infrastructure
docker-compose -f docker-compose.services.yml up -d

# Deploy application
docker compose up -d

# Check status
docker compose ps
docker compose logs -f orangescrum-app
```

### Native Deployment

```bash
cd dist-native

# Configure
cp .env.example .env
nano .env  # Set DB_HOST, DB_PASSWORD, SECURITY_SALT, etc.

# Validate
./helpers/validate-env.sh

# Run (foreground)
./run.sh

# Or run as daemon
DAEMON=true ./run.sh &

# Check status
ps aux | grep osv4-prod
```

---

## Dependencies

### Build Dependencies
- Docker (24.0+)
- Docker Compose (v2.0+)
- Python 3.8+
- Python docker package (`pip install docker`)

### Runtime Dependencies (External)
- PostgreSQL database
- Redis (optional - for cache/queue)
- S3-compatible storage (optional - MinIO or AWS S3)
- SendGrid (optional - for email)

---

## Conclusion

The build system is **functionally correct** in code but has a **binary location mismatch**:

- **Code expects:** `orangescrum-cloud-common/orangescrum-app/osv4-prod`
- **Reality:** `orangescrum-cloud/orangescrum-app/osv4-prod`

This causes deployment package builds to complete but without the binary, requiring manual intervention.

**Recommendation:** Investigate why binary ends up in wrong location, then migrate safely to correct location without breaking existing deployments.
