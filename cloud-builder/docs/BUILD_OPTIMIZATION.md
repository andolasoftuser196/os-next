# FrankenPHP Two-Stage Build System

## Overview

Optimized build process that separates slow base compilation from fast app embedding.

## Architecture

### Stage 1: Base Builder (`base-build.Dockerfile`)

- **Purpose**: Compile static PHP + Caddy server with all extensions
- **Frequency**: Build ONCE or when:
  - PHP version changes
  - Extensions list changes
  - Caddy modules change
  - System dependencies change
- **Output**: `orangescrum-cloud-base:latest` image with pre-compiled artifacts
- **Time**: ~20-30 minutes (one-time cost)

### Stage 2: App Embedder (`app-embed.Dockerfile`)

- **Purpose**: Embed application code into pre-built binary
- **Frequency**: Build FREQUENTLY when:
  - Application code changes
  - Composer dependencies change
  - Configuration changes
- **Output**: Final FrankenPHP binary with embedded app
- **Time**: ~2-5 minutes (fast iteration)

## Usage

### First Time Setup (Build Base)

```bash
# Build the base FrankenPHP binary (slow, do once)
docker compose -f docker-compose.yaml --profile base-build build frankenphp-base-builder
```

This creates the `orangescrum-cloud-base:latest` image containing:

- Compiled static PHP 8.3
- All PHP extensions
- Caddy server with Mercure, Vulcain, Brotli
- All downloaded sources and libraries

### Daily Development (Embed App Only)

```bash
# Build with app embedding (fast, do frequently)
docker compose -f docker-compose.yaml build orangescrum-app-builder
docker compose -f docker-compose.yaml up -d orangescrum-app-builder

# Enter container to test
docker exec -it orangescrum-app-builder sh

# Extract the binary
docker cp orangescrum-app-builder:/go/src/app/dist/frankenphp-linux-x86_64 ./
```

### Rebuild Base (When Dependencies Change)

```bash
# Only needed when PHP version, extensions, or Caddy modules change
docker compose -f docker-compose.yaml --profile base-build build --no-cache frankenphp-base-builder
```

## Benefits

1. **Speed**: App embedding takes minutes vs. full rebuild taking 30+ minutes
2. **Caching**: Base image cached, reused across app iterations
3. **CI/CD**: Base image can be pre-built and stored in registry
4. **Iteration**: Developers can iterate on app code quickly

## File Structure

```txt
durango-builder/builder/
├── base-build.Dockerfile           # Stage 1: Build PHP + Caddy
├── app-embed.Dockerfile            # Stage 2: Embed app only
├── docker-compose.yaml   # Orchestration
└── package/                        # Your app source code
```

## CI/CD Integration

```yaml
# .github/workflows/build.yml example

# Job 1: Build base (runs on dependency changes only)
build-base:
  if: contains(github.event.head_commit.message, '[rebuild-base]')
  steps:
    - run: docker build -f base-build.Dockerfile -t myregistry/frankenphp-base:latest .
    - run: docker push myregistry/frankenphp-base:latest

# Job 2: Build app (runs on every commit)
build-app:
  steps:
    - run: docker pull myregistry/frankenphp-base:latest
    - run: docker build -f app-embed.Dockerfile --build-arg BASE_IMAGE=myregistry/frankenphp-base:latest .
```

## Comparison

| Aspect | Old Approach | New Approach |
|--------|--------------|--------------|
| Full rebuild | 30 min | 30 min (once) |
| App changes | 30 min | 2-5 min |
| Cache efficiency | Poor | Excellent |
| Developer experience | Slow | Fast |
| CI/CD time | Long | Short |

## Advanced: Multi-Stage Caching

For even better performance, you can publish the base image to a registry:

```bash
# Build and publish base
docker build -f base-build.Dockerfile -t myregistry/frankenphp-base:php8.3-v1 .
docker push myregistry/frankenphp-base:php8.3-v1

# Use in app-embed.Dockerfile
# FROM myregistry/frankenphp-base:php8.3-v1 AS app-embedder
```

## Troubleshooting

**Issue**: "Base image not found"

```bash
# Solution: Build base first
docker compose -f docker-compose.yaml --profile base-build build frankenphp-base-builder
```

**Issue**: "Extensions changed but app still uses old ones"

```bash
# Solution: Rebuild base
docker compose -f docker-compose.yaml --profile base-build build --no-cache frankenphp-base-builder
```
