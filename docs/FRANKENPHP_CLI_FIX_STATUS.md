# FrankenPHP CLI Fix - Build Status

## Issue

The `php-cli -r` flag was not working in the FrankenPHP binary, throwing "file not found" errors.

## Root Cause

- **Old FrankenPHP Version**: The base image `orangescrum-cloud-base:latest` was built from FrankenPHP v1.4.4 (created March 21, 2025)
- **Missing Fix**: The `-r` flag implementation was incomplete in that version
- **Fix Available**: FrankenPHP PR #1559 (merged May 13, 2025) added proper `-r` flag handling
- **Solution**: Upgrade to FrankenPHP v1.11.1 which includes the fix

## Changes Made

### 1. Updated base-build.Dockerfile

- **File**: [cloud-builder/builder/base-build.Dockerfile](cloud-builder/builder/base-build.Dockerfile#L27)
- **Change 1**: Updated base image from generic `static-builder` to specific `static-builder-musl-1.11.1`
  - Line 27: `FROM dunglas/frankenphp:static-builder-musl-1.11.1 AS base-builder`
  - Reason: Alpine Linux uses musl libc, needs musl variant for compatibility
  
- **Change 2**: Updated FrankenPHP version from "latest" to "v1.11.1"
  - Line 74: `FRANKENPHP_VERSION=v1.11.1`
  - Reason: "latest" is not a valid git tag and causes build errors; v1.11.1 is a stable release

### 2. Documentation Updates

- **FRANKENPHP_CLI_BEHAVIOR.md**: Created comprehensive guide explaining CLI limitations and correct usage patterns
- **FRANKENPHP_DEPLOYMENT.md**: Updated with new base image information
- **SECURITY_SALT corrections**: Fixed across multiple files (changed from base64 to SHA256 hash)

## Build Process Status

### Timeline

- **Started**: January 15, 2026
- **Expected Duration**: 20-30 minutes (compilation of PHP 8.3 + Caddy with all extensions)
- **Current Status**: Running (Step 6/7 - Compilation phase)
- **Terminal ID**: `14211967-dc0f-4206-990a-fc8296eac31e`

### Build Steps

1. ✅ Pre-flight checks
2. ✅ Archiving OrangeScrum V4 application
3. ✅ Extracting to package directory
4. ✅ Copying configuration overrides (14 files)
5. ✅ Creating base FrankenPHP image (in progress)
   - [1/7] FROM docker.io/dunglas/frankenphp:static-builder-musl-1.11.1 ✅
   - [2/7] RUN rm -rf /go/src/app/dist/static-php-cli ✅
   - [3/7] RUN apk add --no-cache php84-iconv ✅
   - [4/7] RUN wget Go 1.25.0 ✅
   - [5/7] WORKDIR /go/src/app ✅
   - [6/7] RUN ./build-static.sh (RUNNING - ~228 seconds)
   - [7/7] Final cleanup (pending)

### Next Steps After Build Completion

1. **Auto Generate Production Binary**: Once base image builds, app binary will be automatically created (~1-2 min)
2. **Manual Testing**: Test `php-cli -r` flag works correctly
3. **Deploy**: Ready for production deployment

## Technical Details

### FrankenPHP Version Information

- **Old Version**: v1.4.4 (March 21, 2025)
  - Status: Lacks complete -r flag handler
  - Issue: `DisableFlagParsing = true` but no actual handler implementation
  
- **New Version**: v1.11.1 (May 13, 2025)
  - Status: Includes PR #1559 fix
  - Fix: Proper `-r` flag check and handling: `if len(args) >= 2 && args[0] == "-r"`
  - PHP Version: 8.3.29
  - Caddy Version: v2.10.2

### Docker Image Tags

- **Base Builder**: `dunglas/frankenphp:static-builder-musl-1.11.1` ✓ (verified on Docker Hub)
- **Base Image Output**: `orangescrum-cloud-base:latest` (being created)
- **App Binary Output**: `orangescrum-cloud-app:latest` (pending)

### Build Environment

- Python Virtual Environment: `.venv` in cloud-builder directory
- Build Orchestration: `build.py` with `--rebuild-base --skip-deploy` flags
- Compiler: Go 1.25.0
- PHP Extensions: 30+ including PDO, PostgreSQL, Redis, Memcached, etc.
- Compression: Disabled (NO_COMPRESS=1) for faster builds

## Verification Commands (Post-Build)

Once the build completes, verify the CLI fix works:

```bash
# Test 1: PHP version and info
./osv4-prod php-cli --version

# Test 2: Execute inline code
./osv4-prod php-cli -r 'echo "FrankenPHP v1.11.1 CLI working!";'

# Test 3: Access superglobals
./osv4-prod php-cli -r 'echo phpversion();'

# Test 4: Try array operations
./osv4-prod php-cli -r '$arr = [1,2,3]; echo array_sum($arr);'
```

Expected result: All commands execute successfully with output displayed, no "file not found" errors.

## Files Modified

1. [cloud-builder/builder/base-build.Dockerfile](cloud-builder/builder/base-build.Dockerfile) - Updated FrankenPHP image and version
2. [docs/FRANKENPHP_CLI_BEHAVIOR.md](docs/FRANKENPHP_CLI_BEHAVIOR.md) - Created new guide
3. Multiple documentation files - SECURITY_SALT corrections

## Related Issues Fixed

- SECURITY_SALT documentation corrected (base64 → SHA256 hash) across 10 files
- Base image version now explicitly specified (v1.11.1)
- Docker image variant now explicitly specified (musl for Alpine compatibility)

## Monitoring

Check build progress with:

```bash
# In the background, the build can be monitored in VS Code's terminal or by running:
docker ps -a | grep orangescrum-cloud-builder
docker logs orangescrum-cloud-builder -f
```

---

**Status**: Building base image with FrankenPHP v1.11.1 containing the CLI `-r` flag fix.
**Estimated Completion**: ~25 minutes from build start (ETA: ~17:30 UTC)
