# Plan: Fixed EmbeddedAppPath (Eliminate /tmp Polling)

## Problem

Currently, FrankenPHP extracts the embedded app to `/tmp/frankenphp_<checksum>` — a random path. Our startup scripts must:
1. Start the binary in background
2. Poll `/tmp/frankenphp_*` with sleep loops (up to 60s)
3. Verify extraction by checking for `webroot/index.php`
4. Write a sentinel file for cron to find the path
5. Handle crash-restart after extraction

This is the biggest remaining hack in the system.

## Solution

FrankenPHP 1.12.1 added `EmbeddedAppPath` — a Go variable that can be set at build time to use a **fixed, predictable path** instead of a random `/tmp` dir.

```go
// embed.go (FrankenPHP 1.12.1)
var EmbeddedAppPath string  // set via ldflags

func init() {
    if EmbeddedAppPath == "" {
        EmbeddedAppPath = filepath.Join(os.TempDir(), "frankenphp_"+string(embeddedAppChecksum))
    }
    // extraction happens HERE, synchronously, before main()
    if err := untar(EmbeddedAppPath); err != nil { panic(err) }
}
```

Key insight: **extraction completes in `init()` before `main()` runs.** With a fixed path, we don't need to poll at all — the path is known at build time.

## The ldflags Challenge

The intended way to set this is:
```
go build -ldflags "-X github.com/dunglas/frankenphp.EmbeddedAppPath=/app"
```

But our build chain is: `build.py` → `Docker` → `build-static.sh` → `spc build` → `xcaddy build` → `go build`

**spc does NOT support passing Go ldflags.** There's no `SPC_CMD_VAR_FRANKENPHP_GO_LDFLAGS` or similar. The only `SPC_CMD_VAR` for FrankenPHP is `SPC_CMD_VAR_FRANKENPHP_XCADDY_MODULES`.

## Approach: Patch via Go Source File

Instead of ldflags, we inject the path by adding a Go source file to the FrankenPHP source tree during the build. This file runs its `init()` before `embed.go`'s `init()` (Go init order is alphabetical by filename within a package).

**New file: `aaa_embed_path.go`** (prefixed with `aaa_` to ensure it runs first)

```go
package frankenphp

func init() {
    EmbeddedAppPath = "/app"
}
```

Wait — this won't work. `embed.go`'s `init()` checks `if EmbeddedAppPath == ""` and only then uses `/tmp`. But Go init order within a package is **not guaranteed by filename** — it's determined by the compiler. We can't rely on `aaa_` running first.

## Revised Approach: Patch embed.go Directly

During the Docker build, before `build-static.sh` runs, patch `embed.go` to hardcode the path:

```dockerfile
# In app-embed.Dockerfile, before the build step
RUN sed -i 's|EmbeddedAppPath = filepath.Join(os.TempDir(), "frankenphp_"+string(embeddedAppChecksum))|EmbeddedAppPath = "/app"|' /go/src/app/embed.go
```

This is a single `sed` replacement — changes the fallback path from `/tmp/frankenphp_<hash>` to `/app`.

**Pros:**
- No ldflags chain needed
- No new Go files
- Works with any spc version
- One line change in Dockerfile

**Cons:**
- Patches upstream source (fragile if embed.go changes)
- Must be re-tested on FrankenPHP upgrades

## What Changes

### With fixed path `/app`:

| Before (polling) | After (fixed path) |
|---|---|
| Start binary in background | Start binary in foreground (extraction is synchronous) |
| Poll `/tmp/frankenphp_*` for 60s | Path is known: `/app` |
| Check `webroot/index.php` exists | Always exists after binary starts |
| Handle crash-restart cycle | No crash — extraction to `/app` is deterministic |
| Sentinel file for cron | Cron uses `/app` directly |
| `find /tmp -name "frankenphp_*"` | Gone |

### `extract_frankenphp_app()` becomes:

```bash
extract_frankenphp_app() {
    EXTRACTED_APP="/app"  # Fixed, known at build time

    # Clean stale extraction (if binary was updated)
    if [ -d "$EXTRACTED_APP" ] && [ "$EXTRACTED_APP/webroot/index.php" -ot "$1" ]; then
        rm -rf "$EXTRACTED_APP"
    fi

    # Start binary — extraction happens synchronously in init()
    "$@" &
    FRANKENPHP_PID=$!

    # Wait briefly for the server to be ready (not for extraction — that's already done)
    sleep 2
    if ! kill -0 "$FRANKENPHP_PID" 2>/dev/null; then
        echo "[ERROR] FrankenPHP failed to start"
        return 1
    fi

    echo "  [OK] FrankenPHP ready (PID: $FRANKENPHP_PID)"
}
```

### Cron becomes:

```cron
*/30 * * * * cd /app && /orangescrum-app/osv4-prod php-cli bin/cake.php recurring_task >> /data/logs/cron.log 2>&1
```

No sentinel file, no `find`, no `cat`.

## Docker vs Native

| | Docker | Native |
|---|---|---|
| Path | `/app` (inside container) | `/app` (or configurable) |
| Writable | Yes (container filesystem) | Must ensure `/app` is writable |
| Cleanup | Fresh on container restart | Stale data persists across restarts |

For native: `/app` might conflict with existing directories. Alternative: `/var/lib/orangescrum/app` or use an env var `FRANKENPHP_APP_PATH` read at startup.

**Recommended:** Use `/app` for Docker (clean, container-scoped). Keep the current `/tmp` approach for native (it works, extraction dir is cleaned on restart). The sed patch only applies to Docker builds.

## Implementation Steps

### Step 1: Patch embed.go in app-embed.Dockerfile

```dockerfile
# Before the build step, patch the extraction path
ARG EMBEDDED_APP_PATH=/app
RUN sed -i "s|EmbeddedAppPath = filepath.Join(os.TempDir(), \"frankenphp_\"+string(embeddedAppChecksum))|EmbeddedAppPath = \"${EMBEDDED_APP_PATH}\"|" /go/src/app/embed.go
```

### Step 2: Simplify extract_frankenphp_app() for Docker

In `lib/frankenphp-common.sh`, detect if fixed path is available:

```bash
extract_frankenphp_app() {
    local fixed_path="${FRANKENPHP_APP_PATH:-}"

    if [ -n "$fixed_path" ] && [ -d "$fixed_path/webroot" ]; then
        # Fixed path mode — extraction already happened in init()
        EXTRACTED_APP="$fixed_path"
        "$@" &
        FRANKENPHP_PID=$!
        sleep 2
        if ! kill -0 "$FRANKENPHP_PID" 2>/dev/null; then
            echo "[ERROR] FrankenPHP failed to start"
            return 1
        fi
    else
        # Fallback: polling mode (native runner or unpatched binary)
        # ... existing polling code ...
    fi
}
```

### Step 3: Set FRANKENPHP_APP_PATH in Docker entrypoint

```bash
# In entrypoint.sh or docker-compose.yaml
export FRANKENPHP_APP_PATH=/app
```

### Step 4: Update cron config

```cron
*/30 * * * * cd ${FRANKENPHP_APP_PATH:-/app} && /orangescrum-app/osv4-prod php-cli bin/cake.php recurring_task >> /data/logs/cron.log 2>&1
```

### Step 5: Update Dockerfile

```dockerfile
RUN mkdir -p /app && chown orangescrum:orangescrum /app
```

## Risk Assessment

| Risk | Likelihood | Mitigation |
|---|---|---|
| `sed` patch breaks on FrankenPHP upgrade | Medium | Pin to exact line; test on upgrade |
| `/app` path conflicts in container | Low | Alpine image is minimal, no `/app` |
| Native runner expects fixed path | N/A | Native keeps polling fallback |
| Stale extraction in Docker | Low | Container restart = fresh filesystem |

## Verification

1. Build with patch: `python3 build.py --skip-deploy`
2. Start container: `docker compose up -d`
3. Check extraction: `docker exec <container> ls /app/webroot/index.php` — exists immediately
4. Check no `/tmp/frankenphp_*`: `docker exec <container> ls /tmp/frankenphp_*` — empty
5. Health check: `curl http://localhost:8080/healthz` — returns "ok"
6. Cron: `docker exec <container> cat /etc/crontabs/root` — uses `/app` path
