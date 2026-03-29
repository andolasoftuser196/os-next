# Source Build Plan — FrankenPHP Static Builder from Source

## Overview

Build the `static-builder-musl` Docker image entirely from source instead of pulling from Docker Hub. This gives full control over the Go version, FrankenPHP version, and build flags.

## Prerequisites

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| Docker + BuildKit | 20.10+ | 24+ |
| CPU cores | 4 | 8+ (build is heavily parallelized) |
| RAM | 8 GB | 16 GB |
| Disk | 15 GB free | 25 GB free |
| Network | Required (downloads Go modules, PHP source, spc, xcaddy) | Fast connection saves ~5 min |
| Time | ~45 min (4 cores) | ~20 min (8+ cores) |

## Build Commands

### Option A: Using docker-bake (official method)

```bash
cd apps/frankenphp
git checkout v1.12.1

# Build for linux/amd64 only (faster than multi-arch)
VERSION=1.12.1 docker buildx bake static-builder-musl \
  --set static-builder-musl.platform=linux/amd64 \
  --load

# The image is tagged as: dunglas/frankenphp:static-builder-musl-1.12.1
```

### Option B: Using docker build (simpler, no bake dependency)

```bash
cd apps/frankenphp
git checkout v1.12.1

docker build \
  -f static-builder-musl.Dockerfile \
  --build-context golang-base=docker-image://golang:1.26-alpine \
  --build-arg FRANKENPHP_VERSION=1.12.1 \
  -t dunglas/frankenphp:static-builder-musl-1.12.1 \
  .
```

### Option C: Using docker-bake for multi-arch (CI/registry push)

```bash
VERSION=1.12.1 docker buildx bake static-builder-musl \
  --set static-builder-musl.platform=linux/amd64,linux/arm64 \
  --push
```

## What the Build Does (Layer by Layer)

```
Layer 1: golang:1.26-alpine                        ← Go toolchain (~300 MB pull)

Layer 2: apk add alpine-sdk autoconf automake       ← C/C++ build tools (~400 MB)
         bash cmake curl git jq make
         php84 php84-common php84-* (12 packages)   ← PHP 8.4 for running spc/composer
         upx wget xz

Layer 3: go install xcaddy@latest                   ← Caddy build tool

Layer 4: COPY --from=composer /composer              ← Composer binary

Layer 5: go mod download (frankenphp)               ← Go dependencies (~200 MB)
         go mod download (caddy)

Layer 6: COPY . ./                                  ← FrankenPHP source code

Layer 7: ./build-static.sh                          ← THE BIG STEP (~30 min)
         ├── spc doctor --auto-fix
         ├── spc install-pkg go-xcaddy
         ├── spc download PHP 8.3 sources + extension sources
         ├── spc build --enable-zts --build-embed --build-frankenphp
         │   ├── Compile PHP 8.3 from source (ZTS)
         │   ├── Compile 44 PHP extensions
         │   ├── Compile FrankenPHP Go binary with CGO
         │   └── Link everything statically with musl
         └── Output: dist/frankenphp-linux-x86_64
```

## Caveats and Gotchas

### 1. OPcache JIT is Disabled on musl

```bash
# build-static.sh line 47-49
if [ "${SPC_LIBC}" = "musl" ] && [[ "${SPC_OPT_BUILD_ARGS}" != *"--disable-opcache-jit"* ]]; then
    SPC_OPT_BUILD_ARGS="${SPC_OPT_BUILD_ARGS} --disable-opcache-jit"
fi
```

**Impact:** Our `php.ini` sets `opcache.jit = 1255` and `opcache.jit_buffer_size = 64M`, but JIT is **automatically disabled** in musl static builds. These settings are silently ignored at runtime — no error, just no JIT.

**Action required:** Remove or comment out the JIT settings in `builder/php.ini` to avoid confusion. JIT only works with the GNU (`glibc`) static builder, not musl.

### 2. Go Version Must Match

```hcl
# docker-bake.hcl line 14
GO_VERSION = "1.26"
```

The Dockerfile uses `golang:${GO_VERSION}-alpine` as the base. FrankenPHP 1.12.1 requires **Go 1.26**. Using a different Go version may cause build failures or runtime issues.

**If building with Option B**, make sure the `--build-context` matches:
```
--build-context golang-base=docker-image://golang:1.26-alpine
```

### 3. PHP 8.4 is Used for Build Tooling (Not Runtime)

```dockerfile
# static-builder-musl.Dockerfile lines 67-82
php84 php84-common php84-ctype php84-curl ...
```

The builder installs PHP 8.4 via Alpine's `apk` — this is only for running `composer` and `spc` (the static-php-cli build tool) during the build. The **runtime PHP version** is controlled by `PHP_VERSION=8.3` which compiles PHP 8.3 from source.

**Not a problem**, just confusing if you see PHP 8.4 in the build logs.

### 4. GitHub Token Secret (Optional but Recommended)

```dockerfile
RUN --mount=type=secret,id=github-token GITHUB_TOKEN=$(cat /run/secrets/github-token) ...
```

The Dockerfile optionally uses a GitHub token to avoid API rate limits when downloading Go modules and xcaddy. Without it, you may hit rate limits on repeated builds.

**For CI builds:**
```bash
echo $GITHUB_TOKEN > /tmp/github-token
docker build --secret id=github-token,src=/tmp/github-token ...
```

**For local one-off builds:** Usually fine without it.

### 5. Network Dependencies During Build

The build downloads from multiple external sources:

| Source | What | Failure Mode |
|--------|------|--------------|
| php.net (+ mirror) | PHP 8.3 source | Falls back to `phpmirror.static-php.dev` |
| github.com | Go modules, xcaddy, static-php-cli, FrankenPHP | Rate limited without token |
| dl.static-php.dev | spc binary (if SPC_REL_TYPE=binary) | No fallback |
| Alpine repos | Build tools (apk packages) | Retry |

**Air-gapped builds are not supported.** The build requires internet access.

### 6. Build Cache is Fragile

Docker BuildKit caches each layer, but the big `./build-static.sh` RUN is a single layer. If it fails partway through (e.g., network timeout downloading PHP source), the entire 30-min step reruns from scratch.

**Mitigation:** Our `base-build.Dockerfile` wraps `build-static.sh` with `CI=''` which prevents cleanup of the `downloads/` directory, allowing SPC to reuse already-downloaded sources on retry. But the Docker layer cache doesn't help — you need to retry the full `docker build`.

### 7. Binary is Platform-Specific

The static builder produces a binary for the **build platform only** (linux/amd64 or linux/arm64). If your build machine is amd64 but production is arm64 (or vice versa), you need to either:
- Build on the target architecture
- Use `docker buildx bake` with `--platform linux/arm64` (QEMU emulation — 3-5x slower)

### 8. Image Size is Large (~3-4 GB)

The builder image contains the full Go toolchain, C compiler, PHP source, and all intermediate build artifacts. This is expected — it's a build environment, not a runtime image.

**Don't push this to production.** The runtime image (Alpine + binary) is ~350 MB.

### 9. Composer.lock Not Used

```bash
# build-static.sh line 160 (checking for extensions)
[ -f "${EMBED}/vendor/composer/installed.json" ]
```

Our `app-embed.Dockerfile` runs `composer install --no-dev` without a lock file. This is intentional (see comments in the Dockerfile), but means builds aren't 100% reproducible. If reproducibility matters, include `composer.lock` in the git archive.

## After Building

### Save to Registry (Recommended)

```bash
# Tag with version
docker tag dunglas/frankenphp:static-builder-musl-1.12.1 \
  your-registry.com/frankenphp-base:1.12.1-php8.3

# Push
docker push your-registry.com/frankenphp-base:1.12.1-php8.3
```

### Save to File (Offline Transfer)

```bash
docker save dunglas/frankenphp:static-builder-musl-1.12.1 | gzip > frankenphp-static-builder-musl-1.12.1.tar.gz
# ~1.5 GB compressed

# Load on another machine
docker load < frankenphp-static-builder-musl-1.12.1.tar.gz
```

### Use with OrangeScrum Cloud Builder

After the builder image exists locally (via pull, build, or load):

```bash
cd cloud-builder
python3 build.py --skip-deploy
# Step 5 will find the cached base and skip the 30-min compilation
```

## Full CI Pipeline Example

```bash
#!/bin/bash
set -euo pipefail

# 1. Build the static builder from source (or pull)
cd apps/frankenphp
git checkout v1.12.1
docker build \
  -f static-builder-musl.Dockerfile \
  --build-context golang-base=docker-image://golang:1.26-alpine \
  --build-arg FRANKENPHP_VERSION=1.12.1 \
  -t dunglas/frankenphp:static-builder-musl-1.12.1 \
  .

# 2. Build OrangeScrum base (compiles PHP 8.3 into the binary)
cd ../../cloud-builder
python3 build.py --skip-deploy

# 3. Push base image to registry for other machines
docker tag orangescrum-cloud-base:latest registry.example.com/orangescrum-cloud-base:1.12.1
docker push registry.example.com/orangescrum-cloud-base:1.12.1

# 4. Verify dist package
python3 build.py --verify dist/*/dist-docker

# 5. Upload dist to production
scp -r dist/*/dist-docker user@prod:/opt/orangescrum/
```
