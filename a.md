# Plan: Robust FrankenPHP Cloud Builder Overhaul

## Context

The cloud-builder works but is held together with hardcoded values, duplicated logic, global mutable state, and fragile sleep-based polling. A thorough audit found 38 issues across 23 files. The goal is: **one command, zero manual intervention, production-ready dist output**.

This plan is organized into 6 phases. Each phase builds on the previous. Phases are ordered by dependency — later phases can't work without earlier ones.

---

## Phase 1: Single Source of Truth (Version + Build Config)

**Problem:** `VERSION="v26.1.1"` is hardcoded in 3 files. Image names, paths, and build parameters are scattered everywhere.

### New files

| File | Purpose |
|------|---------|
| `VERSION` | Single line: `v26.1.1` — read by all scripts |
| `build.conf` | INI-format build parameters (frankenphp version, php version, image names, extension list, dist keep count) |
| `lib/__init__.py` | Empty, makes `lib/` a Python package |
| `lib/config.py` | `BuildConfig` frozen dataclass — reads VERSION + build.conf + CLI args, generates git SHA/build date metadata |
| `lib/config.sh` | Sourceable shell script — `load_version()`, `load_build_conf()` functions |

### Files to modify

| File | Change |
|------|--------|
| `orangescrum-cloud-docker/build.sh:11` | Replace `VERSION="${VERSION:-v26.1.1}"` with `source "$BUILDER_ROOT/lib/config.sh"; load_version` |
| `orangescrum-cloud-native/build.sh:11` | Same |
| `orangescrum-cloud-native/package.sh:9` | Same |
| `builder/base-build.Dockerfile:19` | `ARG FRANKENPHP_VERSION=1.11.1` + `FROM dunglas/frankenphp:static-builder-musl-${FRANKENPHP_VERSION}` |
| `builder/docker-compose.yaml` | Pass `FRANKENPHP_VERSION`, `BASE_IMAGE_NAME`, `APP_IMAGE_NAME` from env |
| `build.py:59-61` | Read image names from `BuildConfig` instead of `os.environ.get()` with hardcoded default |

---

## Phase 2: Refactor build.py — Eliminate Global State

**Problem:** 6 global `None` variables set later via `global` statements. Functions silently break if called before `main()` sets them.

### Changes to `build.py`

1. **Create `Builder` class** that receives `BuildConfig` in constructor
   - Every current module-level function becomes a method on `Builder` using `self.config`
   - Delete all `global` statements (lines 567, 589, 446)
   - Delete module-level `None` assignments (lines 43-46)

2. **Simplify `main()`:**
   ```python
   def main():
       args = parse_args()
       config = BuildConfig.from_args(args)
       builder = Builder(config)
       return builder.run()
   ```

3. **Add `--config` CLI argument** — path to `build.conf` (defaults to `./build.conf`)

4. **Add `--version` CLI argument** — override VERSION file

5. **Add build timing** — track and print time per step and total

6. **Fix step numbering** — currently the printed step numbers don't match the comments

---

## Phase 3: Shared Shell Library (Eliminate Duplication)

**Problem:** The same logic is copy-pasted across 6 shell scripts. 19 hardcoded `cp` commands in entrypoint.sh. Identical .env parsing in 4 files.

### New file: `lib/frankenphp-common.sh`

Extract these 7 functions from the duplicate code:

| Function | Currently duplicated in | Lines saved |
|----------|------------------------|-------------|
| `load_env_file()` | cake.sh:24-36, queue-worker.sh:13-25, run.sh:76-93 | ~50 |
| `resolve_binary()` | cake.sh:12-19, run.sh:11-17 | ~20 |
| `extract_frankenphp_app()` | entrypoint.sh:84-137, run.sh:104-157 | ~100 |
| `copy_config_files()` | entrypoint.sh:142-182, run.sh:186-239 | ~80 |
| `validate_production_env()` | entrypoint.sh:18-77 (missing from run.sh!) | ~60 |
| `run_migrations()` | entrypoint.sh:185-225, run.sh:243-282 | ~70 |
| `run_seeders()` | entrypoint.sh:227-323, run.sh:284-386 | ~160 |

**Config copying redesign:** Instead of 19 hardcoded `cp` commands, use a glob:
```bash
copy_config_files() {
    local app_dir="$1"
    for example in "$app_dir"/config/*.example.php; do
        [ -f "$example" ] || continue
        local target="${example%.example.php}.php"
        [ -f "$target" ] && continue  # don't overwrite existing
        cp "$example" "$target"
    done
    # Same for plugins
    for plugin_dir in "$app_dir"/plugins/*/config; do
        [ -d "$plugin_dir" ] || continue
        for example in "$plugin_dir"/*.example.php; do
            [ -f "$example" ] || continue
            local target="${example%.example.php}.php"
            [ -f "$target" ] && continue
            cp "$example" "$target"
        done
    done
}
```

### Files to refactor

| File | Before | After |
|------|--------|-------|
| `orangescrum-cloud/entrypoint.sh` | 373 lines | ~50 lines (source lib, call functions) |
| `orangescrum-cloud-native/run.sh` | 449 lines | ~70 lines |
| `orangescrum-cloud-common/helpers/cake.sh` | 39 lines | ~10 lines |
| `orangescrum-cloud-common/helpers/queue-worker.sh` | 282 lines | 260 lines (only env loading changes) |

### Shipping the library in dist packages

- `orangescrum-cloud/Dockerfile` — add `COPY ./lib /orangescrum-app/lib`
- `orangescrum-cloud-docker/build.sh` — add `cp -r "$COMMON_DIR/../lib" "$OUTPUT_DIR/lib"`
- `orangescrum-cloud-native/build.sh` — same
- entrypoint.sh sources `/orangescrum-app/lib/frankenphp-common.sh`
- run.sh sources `./lib/frankenphp-common.sh`

---

## Phase 4: Harden FrankenPHP Extraction

**Problem:** The biggest hack — starting the HTTP server, polling `/tmp/frankenphp_*` with sleep loops, handling crashes, cron re-finding the dir every 30 min.

### 4A. Redesign `extract_frankenphp_app()` in `lib/frankenphp-common.sh`

Key improvements over current implementation:
- **Configurable timeout** via `FRANKENPHP_EXTRACT_TIMEOUT` env var (default 60s, up from 30s)
- **Content verification** — check for `webroot/index.php` AND `vendor/autoload.php` to confirm full extraction
- **Explicit error return codes** — return 1 on failure instead of continuing with empty var
- **Stable sentinel file** — write extracted path to `/tmp/.frankenphp_app_path` for cron/helpers to read

### 4B. Fix cron job

Change `orangescrum-cloud-common/config/cron/recurring_task_cron_franken` from:
```bash
EXTRACTED_APP=$(find /tmp -name "frankenphp_*" ...)  # race condition
```
To:
```bash
[ -f /tmp/.frankenphp_app_path ] && EXTRACTED_APP=$(cat /tmp/.frankenphp_app_path) && ...
```

### 4C. Fix queue worker extraction

In entrypoint.sh, when `QUEUE_WORKER=true`:
- Try `php-cli -r 'echo "ok";'` first to trigger extraction without HTTP server
- If that doesn't extract to `/tmp`, fall back to current HTTP-start-and-kill approach
- Either way, use the robust `extract_frankenphp_app()` from shared lib

---

## Phase 5: Parameterize All Hardcoded Values

### 5A. Fix dangerous .env.example

`orangescrum-cloud-docker/.env.example:14` has:
```
SECURITY_SALT=365d69a31aa12630170a659a76ccbf1726a7c4a65efa339675cc69decd8a72ae
```
This looks real. Users deploy with it. Change to `__CHANGE_THIS_TO_RANDOM_STRING__` (matches the common .env.example).

Also fix `DB_PASSWORD=postgres` → `DB_PASSWORD=changeme_in_production`.

### 5B. Consolidate to single .env.example

The common `.env.example` is the source of truth (has safe placeholders). Delete the docker-specific and native-specific copies. Both `build.sh` scripts copy from common instead.

### 5C. Parameterize Dockerfile

```dockerfile
ARG UID=1000
ARG GID=1000
```
Pass from docker-compose or build.conf.

### 5D. Parameterize image names in docker-compose files

Use `${BASE_IMAGE_NAME:-orangescrum-cloud-base}:latest` pattern.

### 5E. Parameterize systemd service files

Replace hardcoded `/opt/application` with `@@INSTALL_DIR@@`. Add an `install-service` helper that substitutes the actual path with `sed`.

### 5F. Runtime PHP overrides

Create `apply_php_overrides()` in the shared lib that writes a `/tmp/php-overrides/99-overrides.ini` from env vars (`PHP_MEMORY_LIMIT`, `PHP_UPLOAD_MAX_FILESIZE`, etc.) and sets `PHP_INI_SCAN_DIR`.

### 5G. Fix stale path references

- `run.sh:31` says `cd ../durango-builder` — should say `cd ../cloud-builder`

---

## Phase 6: Binary Validation + Build Metadata + Checksums

### 6A. Binary validation in `Builder`

After extraction, verify:
1. File size > 50MB (sanity check)
2. ELF magic bytes (`\x7fELF`)
3. `file` command shows "statically linked"
4. Quick smoke: `./osv4-prod version` (with timeout)

### 6B. SHA256 checksums

Both build.sh scripts generate `.sha256` files alongside the binary.

### 6C. Machine-readable build manifest

Replace `.build-manifest.txt` with `build-manifest.json`:
```json
{
  "version": "v26.1.1",
  "git_sha": "abc123...",
  "build_timestamp": "2026-03-29T14:30:00Z",
  "frankenphp_version": "1.11.1",
  "php_version": "8.3",
  "binary_sha256": "...",
  "binary_size_bytes": 356000000
}
```

### 6D. Add `--verify` flag

`python3 build.py --verify dist/20260329/dist-docker` — reads manifest, recomputes SHA, reports pass/fail.

### 6E. Dist structure verification

After building, verify all expected files exist in both dist packages.

---

## Error Handling (applies across all phases)

- `entrypoint.sh` and `run.sh`: change `set +e` to `set -euo pipefail` with explicit `|| true` on commands allowed to fail
- `build.py`: wrap each step with timing + error context (step name in exception message)
- Binary extraction: return error code instead of continuing with empty `EXTRACTED_APP`
- Migration failures: log clearly but don't block startup (current behavior is correct, just needs better logging)

---

## Implementation Order

```
Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6
 (config)  (build.py)  (shell lib)  (extraction)  (params)  (validation)
```

Each phase is independently testable. Phase 1+2 are the foundation. Phase 3+4 are the biggest risk reduction. Phase 5+6 are hardening.

---

## New files created

| File | Purpose |
|------|---------|
| `VERSION` | Canonical version string |
| `build.conf` | All build parameters (INI format) |
| `lib/__init__.py` | Python package marker |
| `lib/config.py` | BuildConfig dataclass + manifest generation |
| `lib/config.sh` | Shell config reader |
| `lib/frankenphp-common.sh` | 7 shared shell functions (~300 lines, replacing ~540 duplicated lines) |

## Files significantly modified

| File | Current lines | Estimated after |
|------|--------------|-----------------|
| `build.py` | 738 | ~500 (class-based, no globals) |
| `orangescrum-cloud/entrypoint.sh` | 373 | ~50 |
| `orangescrum-cloud-native/run.sh` | 449 | ~70 |

## Files deleted

| File | Reason |
|------|--------|
| `orangescrum-cloud-docker/.env.example` | Replaced by common/.env.example |
| `orangescrum-cloud-native/.env.example` | Replaced by common/.env.example |

---

## Verification

After implementation, test the full pipeline:

1. `python3 build.py --check` — pre-flight passes
2. `python3 build.py --skip-deploy` — builds binary + both dist packages
3. Verify `dist/{timestamp}/dist-docker/build-manifest.json` exists with correct SHA
4. Verify `dist/{timestamp}/dist-docker/orangescrum-app/osv4-prod.sha256` matches
5. `python3 build.py --verify dist/{timestamp}/dist-docker` — passes
6. `cd dist/{timestamp}/dist-docker && docker compose up -d` — container starts, health check passes
7. `docker compose logs orangescrum-app` — no extraction errors, configs copied, migrations run
8. `curl http://localhost:8080/healthz` — returns "ok"
9. `cd dist/{timestamp}/dist-native && ./run.sh` — binary starts, same verification
