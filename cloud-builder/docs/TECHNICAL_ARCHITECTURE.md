# FrankenPHP Static Binary Build System

Complete documentation for building and deploying OrangeScrum with FrankenPHP static binaries.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Data Persistence](#data-persistence)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Build Process Detailed](#build-process-detailed)
- [Performance Benchmarks](#performance-benchmarks)
- [Directory Structure](#directory-structure)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Advanced Usage](#advanced-usage)

---

## Overview

This build system creates a **self-contained static binary** of FrankenPHP (PHP + Caddy web server) with the OrangeScrum application embedded directly into the executable. This approach provides:

- ✅ **Single binary deployment** - No PHP runtime or web server installation needed
- ✅ **Fast startup** - Application code embedded, no file system access required
- ✅ **Optimal performance** - Static linking, minimal overhead
- ✅ **Two-stage build** - Separate base compilation from app embedding for rapid iteration

### Key Innovation: Two-Stage Build

```txt
Stage 1: Base Builder (Slow, One-Time)
├── Compile static PHP with extensions (~20-30 min)
├── Build Caddy server with modules
└── Cache artifacts for reuse

Stage 2: App Embedder (Fast, Frequent)
├── Use pre-built base (~30 seconds)
├── Embed application code
└── Link final binary
```

**Result**: 49x faster builds for code changes!

---

## Architecture

### Components

1. **Base Builder** (`base-build.Dockerfile`)
   - Compiles PHP 8.3 with 30+ extensions
   - Builds Caddy with Mercure, Vulcain, Brotli modules
  - Creates reusable `orangescrum-cloud-base:latest` image

2. **App Embedder** (`app-embed.Dockerfile`)
   - Installs Composer dependencies
   - Copies application source
   - Embeds app into FrankenPHP binary

3. **Build Orchestrator** (`build_optimized.py`)
   - Manages the entire build pipeline
   - Archives repository from git
   - Extracts binary and deploys application

4. **Deployment** (`orangescrum-ee/`)
   - Minimal Alpine container
   - Runs the static binary
   - PostgreSQL database

### Build Flow Diagram

```txt
┌─────────────────────────────────────────────────────────┐
│                    Build Pipeline                        │
└─────────────────────────────────────────────────────────┘

Step 1: Archive Repository
    ↓
    git archive → repo.tar → extract to package/
    
Step 2: Copy to Builder
    ↓
    package/ → builder/package/
    
Step 3: Build Base (One-Time or Cache Hit)
    ↓
    ┌─────────────────────────────────────┐
    │  Base Image: orangescrum-cloud-base:latest │
    │  - Static PHP 8.3                   │
    │  - All extensions compiled          │
    │  - Caddy server with modules        │
    │  Size: 9.08 GB (build artifacts)    │
    └─────────────────────────────────────┘
    
Step 4: Embed Application
    ↓
    ┌─────────────────────────────────────┐
    │  App Builder Container              │
    │  - composer install                 │
    │  - Copy app source                  │
    │  - Run post-install scripts         │
    │  - Embed app into binary            │
    └─────────────────────────────────────┘
    
Step 5: Extract Binary
    ↓
    frankenphp-linux-x86_64 (90MB executable)
    
Step 6: Deploy
    ↓
    ┌─────────────────────────────────────┐
    │  Docker Compose Stack               │
    │  - Alpine container + binary        │
    │  - PostgreSQL database              │
    │  - Network bridge                   │
    └─────────────────────────────────────┘
```

---

## Data Persistence

### The Challenge

FrankenPHP embeds the application directly into the binary. When the binary starts, it extracts the embedded app to a temporary directory (`/tmp/frankenphp_<hash>`). This creates a challenge: **any runtime changes (uploads, cache, logs) are lost when the container restarts**.

### The Solution: Persistent Volumes with Symlinks

The system uses an **entrypoint script** that automatically creates symlinks from the extracted app to persistent Docker volumes:

```txt
Container Restart Flow:
┌──────────────────────────────────────────────────────────┐
│ 1. FrankenPHP starts and extracts embedded app           │
│    → /tmp/frankenphp_<hash>/                             │
├──────────────────────────────────────────────────────────┤
│ 2. Entrypoint script detects extraction                  │
│    → Waits for directory creation                        │
├──────────────────────────────────────────────────────────┤
│ 3. Creates symlinks to persistent volumes:               │
│    /tmp/frankenphp_<hash>/webroot/files                  │
│    → /data/webroot/files (Docker volume)                 │
│                                                           │
│    /tmp/frankenphp_<hash>/logs                           │
│    → /data/logs (Docker volume)                          │
│                                                           │
│    ... (8 directories total)                             │
├──────────────────────────────────────────────────────────┤
│ 4. Application writes to extracted path                  │
│    → Data actually stored in persistent volumes          │
└──────────────────────────────────────────────────────────┘
```

### Persistent Directories

The following directories are automatically made persistent:

| Directory | Purpose | Volume Name |
|-----------|---------|-------------|
| `tmp/cache/models` | Model cache | `app-tmp` |
| `tmp/cache/persistent` | Application cache | `app-tmp` |
| `tmp/cache/views` | Template cache | `app-tmp` |
| `tmp/sessions` | PHP sessions | `app-tmp` |
| `logs/` | Application logs | `app-logs` |
| `webroot/files/` | User uploads | `app-uploads` |
| `webroot/csv/` | CSV exports | `app-csv` |
| `webroot/invoice-logo/` | Invoice logos | `app-invoice` |
| `webroot/timesheetpdf/` | Timesheet PDFs | `app-timesheet` |
| `webroot/pdfreports/` | PDF reports | `app-reports` |
| `config/app_local.php` | Runtime config | `app-config` |

### How It Works

**entrypoint.sh** script logic:

```bash
# 1. Start FrankenPHP in background
/orangescrum-app/orangescrum-ee "$@" &

# 2. Wait for embedded app extraction (max 30 seconds)
for i in {1..30}; do
  APP_DIR=$(find /tmp -maxdepth 1 -name "frankenphp_*" -type d 2>/dev/null | head -1)
  [ -n "$APP_DIR" ] && break
  sleep 1
done

# 3. Create symlinks for each persistent directory
setup_persistent_dir() {
  local app_path="$1"     # e.g., tmp/cache/models
  local data_path="$2"     # e.g., /data/tmp/cache/models
  
  # Migrate initial content if volume is empty
  if [ ! "$(ls -A "$data_path")" ]; then
    cp -r "$APP_DIR/$app_path/"* "$data_path/" 2>/dev/null
  fi
  
  # Replace directory with symlink
  rm -rf "$APP_DIR/$app_path"
  ln -s "$data_path" "$APP_DIR/$app_path"
}

# 4. Wait for FrankenPHP process to complete
wait
```

### Verifying Persistence

Test that data persists across container restarts:

```bash
# 1. Create a test file
docker exec orangescrum-multitenant-base-orangescrum-app-1 \
  sh -c 'echo "Test file" > /tmp/frankenphp_*/webroot/files/test.txt'

# 2. Restart container
docker compose -f durango-builder/orangescrum-ee/docker-compose.yaml restart orangescrum-app

# 3. Wait 15 seconds, then verify file still exists
sleep 15
docker exec orangescrum-multitenant-base-orangescrum-app-1 \
  sh -c 'cat /tmp/frankenphp_*/webroot/files/test.txt'
# Output: Test file ✓
```

### Volume Management

```bash
# List all volumes
docker volume ls | grep app-

# Inspect a volume
docker volume inspect orangescrum-multitenant-base_app-uploads

# Backup a volume
docker run --rm -v orangescrum-multitenant-base_app-uploads:/data \
  -v $(pwd):/backup alpine tar czf /backup/uploads-backup.tar.gz /data

# Restore a volume
docker run --rm -v orangescrum-multitenant-base_app-uploads:/data \
  -v $(pwd):/backup alpine tar xzf /backup/uploads-backup.tar.gz -C /
```

---

## Prerequisites

### System Requirements

- **OS**: Linux (Ubuntu 20.04+, Debian 11+, or compatible)
- **RAM**: 8GB minimum (16GB recommended for building)
- **Disk**: 20GB free space
- **Docker**: 24.0+ with Compose V2
- **Python**: 3.8+ with venv support

### Required Software

```bash
# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Install Python and dependencies
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv git

# Verify installations
docker --version          # Should be 24.0+
docker compose version    # Should be v2.x
python3 --version         # Should be 3.8+
```

---

## Quick Start

### First-Time Build (Full Process)

```bash
# 1. Clone repository
cd /path/to/project-durango/durango-multitenant

# 2. Set up Python environment
python3 -m venv .venv
source .venv/bin/activate
pip install docker

# 3. Run full build with all steps (~25-30 minutes for first build)
python3 durango-builder/build_optimized.py --all
```

### Subsequent Builds (Code Changes Only)

```bash
# Activate environment
source .venv/bin/activate

# Build and deploy (~30-60 seconds)
python3 durango-builder/build_optimized.py --all --skip-base
```

### Build Options

The build script supports granular control over each step:

```bash
# Full pipeline (archive → build base → build app → extract → deploy)
python3 durango-builder/build_optimized.py --all

# Skip base build (use existing orangescrum-cloud-base:latest)
python3 durango-builder/build_optimized.py --all --skip-base

# Only archive repository
python3 durango-builder/build_optimized.py --archive

# Only build base image (~20-30 min)
python3 durango-builder/build_optimized.py --build-base

# Only build app image (~1-2 min)
python3 durango-builder/build_optimized.py --build-app

# Only extract binary (no deployment)
python3 durango-builder/build_optimized.py --extract

# Force rebuild base image even if it exists
python3 durango-builder/build_optimized.py --all --rebuild-base

# Show all options
python3 durango-builder/build_optimized.py --help
```

---

## Build Process Detailed

### Phase 1: Base Image Build

**When to run**: First time, or when PHP version/extensions change

**What happens**:

```bash
docker compose -f docker-compose.yaml --profile base-build build frankenphp-base-builder
```

**Steps**:

1. **Environment Setup** (~2 min)
   - Pull dunglas/frankenphp:static-builder base
   - Install system dependencies (php84-iconv)
   - Install Go 1.25

2. **Download Sources** (~5-10 min)
   - Fetch PHP 8.3 source
   - Download 30+ extension sources
   - Download library sources (libavif, nghttp2, etc.)

3. **Compile Static PHP** (~10-15 min)
   - Configure with ZTS (Zend Thread Safety)
   - Compile with extensions:

     ```txt
     bcmath, calendar, ctype, curl, dom, exif, fileinfo,
     filter, ftp, gd, iconv, intl, ldap, mbstring, mysqli,
     mysqlnd, opcache, openssl, pcntl, pdo, pdo_mysql,
     pdo_pgsql, pdo_sqlite, pgsql, phar, posix, readline,
     session, shmop, simplexml, soap, sockets, sodium,
     sqlite3, sysvmsg, sysvsem, sysvshm, tidy, tokenizer,
     xml, xmlreader, xmlwriter, zip, zlib, zstd
     ```

   - Create libphp.a static library

4. **Build Caddy Server** (~5 min)
   - Use xcaddy to build Caddy
   - Include FrankenPHP module
   - Include additional modules:
     - Mercure (Server-Sent Events)
     - Vulcain (HTTP/2 Server Push)
     - Brotli compression
   - Link against static PHP library

5. **Create Base Image** (~1 min)
  - Tag as `orangescrum-cloud-base:latest`
   - Size: ~9.08 GB (includes all build artifacts)
   - Verify binary with `frankenphp version`

**Output**:

```txt
orangescrum-cloud-base:latest - Ready for app embedding
```

---

### Phase 2: Application Embedding

**When to run**: Every code change

**What happens**:

```bash
python3 durango-builder/build_optimized.py --all --skip-base
```

**Detailed Steps**:

#### Step 1: Archive Repository (~2 seconds)

```python
# Extract current branch
git rev-parse --abbrev-ref HEAD
# Output: feature/multi-tenant

# Create tar archive
git archive --format=tar HEAD -o durango-builder/repo.tar

# Extract to package/
tar -xf repo.tar -C durango-builder/package/
```

**Purpose**: Get clean snapshot of committed code (ignores uncommitted changes)

---

#### Step 2: Prepare Build Package (~1 second)

```bash
# Copy to builder directory
cp -r durango-builder/package/ durango-builder/builder/package/
```

**Structure**:

```txt
builder/package/
├── composer.json
├── composer.lock
├── config/
│   ├── app.php
│   ├── app_local.example.php
│   └── ...
├── src/
│   ├── Controller/
│   ├── Model/
│   └── ...
├── webroot/
├── templates/
└── ...
```

---

#### Step 3: Build Application Image (~18-30 seconds)

**Dockerfile**: `app-embed.Dockerfile`

**Two-stage process**:

##### Stage 1: Composer Helper (PHP 8.3)

```dockerfile
FROM php:8.3-alpine AS composer-helper

# Install Composer and dependencies
RUN apk add --no-cache curl git unzip && \
    curl -sS https://getcomposer.org/installer | php -- \
        --install-dir=/usr/local/bin --filename=composer

# Install PHP dependencies
COPY ./package/composer.json ./
RUN composer install --ignore-platform-req=* --no-dev --no-scripts

# Copy application source
COPY ./package/ .

# Generate optimized autoloader for PHP 8.3 runtime
# CRITICAL: --ignore-platform-req=php prevents PHP 8.4+ version check
RUN composer dump-autoload --optimize --no-dev --ignore-platform-req=php

# Run post-install scripts (set permissions, etc.)
RUN composer run-script post-install-cmd --no-interaction
```

##### Stage 2: App Embedding (frankenphp-base)

```dockerfile
FROM orangescrum-cloud-base:latest AS app-embedder

WORKDIR /go/src/app/dist/app

# Copy prepared application from composer-helper
COPY --from=composer-helper /app/ ./

# Embed application into FrankenPHP binary
WORKDIR /go/src/app/
RUN EMBED=dist/app/ ./build-static.sh
```

**Build command**:

```bash
docker compose -f docker-compose.yaml build orangescrum-app-builder
```

**What `build-static.sh` does with EMBED**:

1. Detects embedded app at `dist/app/`
2. Adds flag: `--with-frankenphp-app=dist/app/`
3. Compiles app into binary as embedded filesystem
4. Creates final executable: `dist/frankenphp-linux-x86_64`

**Binary contents**:

- PHP 8.3 runtime (statically linked)
- Caddy web server
- All PHP extensions
- **Embedded application files** (read from memory at runtime)
- **Correct PHP 8.3 autoloader** (no version check errors)

---

#### Step 4: Start Builder Container (~1 second)

```bash
docker compose -f docker-compose.yaml up -d orangescrum-app-builder
```

**Container state**:

- Name: `orangescrum-app-builder`
- Command: `tail -f /dev/null` (keeps container running)
- Volume: `build-output:/go/src/app/dist` (persistent binary storage)

---

#### Step 5: Extract Binary (~2 seconds)

```python
# Get container handle
container = docker_client.containers.get("orangescrum-app-builder")

# Extract binary as tar stream
bits, stat = container.get_archive("/go/src/app/dist/frankenphp-linux-x86_64")

# Extract from tar
tar_stream = io.BytesIO(b"".join(bits))
with tarfile.open(fileobj=tar_stream) as tar:
    tar.extractall(path="durango-builder/orangescrum-ee/orangescrum-app/")

# Make executable
chmod 0755 durango-builder/orangescrum-ee/orangescrum-app/orangescrum-ee
```

**Output**:

```txt
durango-builder/orangescrum-ee/orangescrum-app/orangescrum-ee
Size: ~90 MB
Type: ELF 64-bit LSB pie executable
```

---

#### Step 6: Verify Binary (~1 second)

```bash
# Test version
./frankenphp-linux-x86_64 version
# Output:
# FrankenPHP v1.x.x
# PHP 8.3.28 (cli) (built: Dec 2 2024)
# Caddy v2.x.x

# Test build info
./frankenphp-linux-x86_64 build-info
# Output shows all compiled extensions and modules
```

---

## Performance Benchmarks

### Build Time Comparison

| Scenario | Old Method | Optimized (First) | Optimized (Cached) |
|----------|-----------|-------------------|-------------------|
| Full build | ~30 min | ~27 min | ~25 min |
| Code change | ~30 min | ~2.5 min (147s) | **~36 sec** |
| Speed improvement | 1x | **12x faster** | **49x faster** |

### Build Phase Breakdown

#### First Optimized Build (147.8 seconds)

```txt
Archive repository:        2.5s   ( 1.7%)
Copy package:             1.2s   ( 0.8%)
Build app image:         69.4s   (47.0%)  ← Main work
  ├─ Composer install:   18.4s
  ├─ Copy files:          2.7s
  ├─ Post-install:        0.3s
  ├─ Build binary:       34.7s
  └─ Verify:              0.8s
Start container:          2.0s   ( 1.4%)
Extract binary:           2.1s   ( 1.4%)
Verify binary:            1.5s   ( 1.0%)
Stop old containers:      0.9s   ( 0.6%)
Start new stack:         23.9s   (16.2%)
Test application:         5.2s   ( 3.5%)
Container startup:       39.1s   (26.4%)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total:                  147.8s  (100.0%)
```

#### Cached Build (36.4 seconds)

```txt
Archive repository:        1.8s   ( 4.9%)
Copy package:             0.9s   ( 2.5%)
Build app image:         18.2s   (50.0%)  ← Mostly cached!
  ├─ Composer (cached):   0.1s
  ├─ Copy files:          1.4s
  ├─ Post-install:        0.2s
  ├─ Build binary:       14.8s
  └─ Verify:              0.5s
Start container:          1.2s   ( 3.3%)
Extract binary:           1.5s   ( 4.1%)
Verify binary:            0.8s   ( 2.2%)
Stop old containers:      0.7s   ( 1.9%)
Start new stack:         10.9s   (29.9%)
Test application:         0.4s   ( 1.1%)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total:                   36.4s  (100.0%)
```

---

## Directory Structure

```txt
durango-multitenant/
├── durango-builder/
│   ├── README.md                          # This file
│   ├── build_optimized.py                 # Main build script
│   │
│   ├── builder/
│   │   ├── docker-compose.yaml  # Two-stage orchestration
│   │   ├── base-build.Dockerfile          # Stage 1: Base builder
│   │   ├── app-embed.Dockerfile           # Stage 2: App embedder
│   │   ├── BUILD_OPTIMIZATION.md          # Optimization documentation
│   │   └── package/                       # Temporary build directory
│   │
│   ├── orangescrum-ee/
│   │   ├── docker-compose.yaml            # Deployment stack
│   │   ├── Dockerfile                     # Runtime container
│   │   └── orangescrum-app/
│   │       └── orangescrum-ee             # Final binary (90MB)
│   │
│   └── package/                           # Git archive extraction
│
├── durango-pg/                            # Application source repository
├── frankenphp/                            # FrankenPHP source
└── .venv/                                 # Python virtual environment
```

---

## Configuration

### Environment Variables

**Base Build Configuration** (`base-build.Dockerfile`):

```bash
PHP_VERSION=8.3
NO_COMPRESS=1
FRANKENPHP_VERSION=latest
PHP_EXTENSIONS=bcmath,calendar,ctype,curl,dom,exif,fileinfo,filter,ftp,gd,iconv,intl,ldap,mbstring,mysqli,mysqlnd,opcache,openssl,pcntl,pdo,pdo_mysql,pdo_pgsql,pdo_sqlite,pgsql,phar,posix,readline,redis,session,shmop,simplexml,soap,sockets,sodium,sqlite3,sysvmsg,sysvsem,sysvshm,tidy,tokenizer,xml,xmlreader,xmlwriter,zip,zlib,zstd
```

---

## Troubleshooting

### Common Issues

#### 1. "Base image not found"

```bash
# Build base image first (or let --all build it automatically)
python3 durango-builder/build_optimized.py --build-base
```

#### 2. "ModuleNotFoundError: No module named 'docker'"

```bash
source .venv/bin/activate
pip install docker
```

#### 3. Application won't start

```bash
# Check logs
docker logs orangescrum-multitenant-base-orangescrum-app-1

# Test binary manually
cd durango-builder/orangescrum-ee/orangescrum-app
./orangescrum-ee version
```

#### 4. Data not persisting after container restart

**Symptoms**: Uploaded files, logs, or cache disappear after restart.

**Check symlinks**:

```bash
# Verify symlinks are created
docker exec orangescrum-multitenant-base-orangescrum-app-1 \
  ls -la /tmp/frankenphp_*/webroot/ | grep files

# Expected output:
# lrwxrwxrwx 1 root root 19 Dec 2 06:28 files -> /data/webroot/files
```

**Check entrypoint logs**:

```bash
docker logs orangescrum-multitenant-base-orangescrum-app-1 | grep -E "(Found extracted|Linked|configured)"

# Expected output:
# Found extracted app at: /tmp/frankenphp_xxx
# ✓ Linked: /tmp/frankenphp_xxx/webroot/files -> /data/webroot/files
# ✓ All persistent directories configured
```

**Verify volumes exist**:

```bash
docker volume ls | grep app-

# Expected output:
# orangescrum-multitenant-base_app-uploads
# orangescrum-multitenant-base_app-logs
# ... (8 volumes total)
```

**Manual fix**:

```bash
# If entrypoint didn't run correctly, recreate container
docker compose -f durango-builder/orangescrum-ee/docker-compose.yaml down
docker compose -f durango-builder/orangescrum-ee/docker-compose.yaml up -d
```

#### 5. "Waiting for app extraction..." timeout

**Symptoms**: Entrypoint script logs show waiting for 30 seconds, then times out.

**Cause**: FrankenPHP binary failed to extract embedded app.

**Debug**:

```bash
# Check if FrankenPHP is running
docker exec orangescrum-multitenant-base-orangescrum-app-1 ps aux | grep frankenphp

# Test binary manually
docker exec orangescrum-multitenant-base-orangescrum-app-1 /orangescrum-app/orangescrum-ee version
```

**Fix**:

```bash
# Rebuild application with embedded app
python3 durango-builder/build_optimized.py --all --skip-base
```

#### 6. Volume permissions issues

**Symptoms**: Application shows "Permission denied" errors for uploads or logs.

**Fix**:

```bash
# Fix volume permissions
docker exec orangescrum-multitenant-base-orangescrum-app-1 \
  sh -c 'chown -R root:root /data/webroot/files && chmod -R 755 /data/webroot/files'

# Or for all volumes
docker exec orangescrum-multitenant-base-orangescrum-app-1 \
  sh -c 'find /data -type d -exec chmod 755 {} \; && find /data -type f -exec chmod 644 {} \;'
```

#### 7. PHP version compatibility errors

**Symptoms**: Application shows "PHP version >= 8.4.0 required" but runtime has PHP 8.3.

**Cause**: Composer autoloader was generated with incorrect platform requirements.

**Solution**: The build system automatically handles this by:

1. Using `--ignore-platform-req=php` in `composer dump-autoload` during build
2. This generates `platform_check.php` with correct PHP 8.3 requirements
3. No runtime composer install needed

**Verify fix**:

```bash
# Check embedded autoloader requirements
docker exec orangescrum-app-builder \
  grep "PHP_VERSION_ID" /go/src/app/dist/app/vendor/composer/platform_check.php

# Expected output: >= 80300 (PHP 8.3.0)
# Not: >= 80400 (PHP 8.4.0)
```

**If still seeing errors**:

```bash
# Rebuild with fresh autoloader
python3 durango-builder/build_optimized.py --all --skip-base
```

---

## Advanced Usage

### CI/CD Integration

See `BUILD_OPTIMIZATION.md` for GitHub Actions example and advanced configurations.

### Multi-Architecture Builds

```bash
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -f base-build.Dockerfile \
  -t orangescrum-cloud-base:latest \
  .
```

---

## License

See main project LICENSE file.

## Credits

- **FrankenPHP**: <https://frankenphp.dev/>
- **static-php-cli**: <https://github.com/crazywhalecc/static-php-cli>
- **Caddy**: <https://caddyserver.com/>
