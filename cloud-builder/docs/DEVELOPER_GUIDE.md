# Developer Guide — OrangeScrum FrankenPHP Cloud Builder

## Quick Reference

```bash
# Pre-flight check
python3 build.py --check

# Full build (produces dist-docker/ + dist-native/)
python3 build.py --skip-deploy

# Rebuild after code change (base image cached, ~3 min)
python3 build.py --skip-deploy

# Force rebuild FrankenPHP base (~30 min)
python3 build.py --skip-deploy --rebuild-base

# Verify a built dist package
python3 build.py --verify dist/20260329_143000/dist-docker

# Deploy latest build locally
./deploy.sh
./deploy.sh ps
./deploy.sh logs -f
```

---

## How the Build Works

The builder produces a **single static binary (~340 MB)** containing FrankenPHP + PHP 8.3 + Caddy + the entire OrangeScrum application + all Composer dependencies. No PHP, Apache, or nginx needed on the target host.

### Build Pipeline

```
python3 build.py --skip-deploy

  Step 1: Prepare package directory
           git archive HEAD → builder/package/

  Step 2: Archive application source
           ../apps/orangescrum-v4 → builder/repo.tar

  Step 3: Extract to package directory
           repo.tar → builder/package/

  Step 4: Copy configuration overrides
           orangescrum-cloud-common/config/*.example.php → builder/package/config/

  Step 5: Ensure FrankenPHP base image            ← SLOW (~30 min, first time only)
           base-build.Dockerfile → orangescrum-cloud-base:latest
           Compiles PHP 8.3 from source with 44 extensions

  Step 6: Embed application into FrankenPHP        ← ~2 min
           app-embed.Dockerfile (2-stage):
             Stage 1: composer install + dump-autoload
             Stage 2: embed app into static binary

  Step 7: Extract binary
           docker create + docker cp → orangescrum-cloud-common/orangescrum-app/osv4-prod

  Step 8: Validate binary
           ELF check, size check, static linking verification

  Step 9: Build deployment packages
           orangescrum-cloud-docker/build.sh → dist/{timestamp}/dist-docker/
           orangescrum-cloud-native/build.sh → dist/{timestamp}/dist-native/

  Step 10: Write manifests and checksums
            build-manifest.json + *.sha256

  Step 11: Clean up builder
  Step 12: Prune old builds (keeps latest 3)
```

### First Build vs Subsequent Builds

| | First Build | After Base Cached |
|---|---|---|
| Base image compilation | ~30 min | Skipped |
| App embedding | ~2 min | ~2 min |
| Binary extraction + packaging | ~1 min | ~1 min |
| **Total** | **~35 min** | **~3 min** |

The base image only needs rebuilding when:

- Upgrading FrankenPHP version (`build.conf: frankenphp_version`)
- Changing PHP version (`build.conf: php_version`)
- Adding/removing PHP extensions (`build.conf: [php_extensions] list`)

---

## Project Structure

```
cloud-builder/
├── build.py                         # Build orchestrator (Builder class)
├── build.conf                       # All build parameters (single source of truth)
├── VERSION                          # Version string (v26.1.1)
├── deploy.sh                        # Deploy wrapper for dist packages
│
├── lib/                             # Shared libraries
│   ├── __init__.py                  # Python package
│   ├── config.py                    # BuildConfig dataclass
│   ├── config.sh                    # Shell config reader
│   └── frankenphp-common.sh         # 8 shared shell functions
│
├── builder/                         # FrankenPHP compilation
│   ├── base-build.Dockerfile        # Stage 1: compile PHP + FrankenPHP
│   ├── app-embed.Dockerfile         # Stage 2: embed app into binary
│   ├── docker-compose.yaml          # Build services
│   ├── Caddyfile                    # Embedded web server config
│   ├── php.ini                      # Embedded PHP config
│   └── .dockerignore
│
├── orangescrum-cloud/               # Docker runtime image source
│   ├── Dockerfile                   # Alpine + binary + cron
│   ├── docker-compose.yaml          # App + queue worker services
│   ├── entrypoint.sh               # Container startup (sources lib)
│   └── config/                      # Config templates (from common)
│
├── orangescrum-cloud-common/        # Shared files (source of truth)
│   ├── config/                      # All .example.php templates
│   ├── helpers/                     # cake.sh, queue-worker.sh, validate-env.sh
│   ├── docs/                        # Production deployment guides
│   ├── .env.example                 # Environment template (safe placeholders)
│   └── .env.full.example            # Complete env reference
│
├── orangescrum-cloud-docker/        # Docker dist package source
│   ├── build.sh                     # Assembles dist-docker/
│   ├── Dockerfile                   # Identical to orangescrum-cloud/Dockerfile
│   ├── docker-compose.yaml          # App + queue worker
│   ├── docker-compose.services.yml  # PostgreSQL, Redis, MinIO, MailHog
│   ├── entrypoint.sh               # Identical to orangescrum-cloud/entrypoint.sh
│   └── .env.example                 # Docker-specific env defaults
│
├── orangescrum-cloud-native/        # Native dist package source
│   ├── build.sh                     # Assembles dist-native/
│   ├── run.sh                       # Binary bootstrap (sources lib)
│   ├── caddy.sh                     # CLI wrapper
│   ├── package.sh                   # Create distributable tarball
│   └── systemd/                     # Service templates (@@INSTALL_DIR@@)
│
└── dist/                            # Build output (gitignored)
    └── {timestamp}/
        ├── dist-docker/             # Ready-to-deploy Docker package
        └── dist-native/             # Ready-to-deploy native package
```

### Three-Tier Architecture

| Tier | Location | Role |
|------|----------|------|
| Common | `orangescrum-cloud-common/` | Configs, helpers, docs, binary — single source of truth |
| Source | `orangescrum-cloud-docker/`, `orangescrum-cloud-native/` | Deployment-specific files + `build.sh` assemblers |
| Output | `dist/{timestamp}/` | Complete, self-contained deployment packages |

---

## Configuration System

### build.conf — Build Parameters

All build-time settings. Never hardcoded in scripts.

```ini
[build]
frankenphp_version = 1.11.1
php_version = 8.3
base_image_name = orangescrum-cloud-base
app_image_name = orangescrum-cloud-app
no_compress = 1
app_source = ../apps/orangescrum-v4
dist_keep_count = 3
binary_name = osv4-prod

[runtime]
uid = 1000
gid = 1000

[php_extensions]
list = bcmath,calendar,ctype,curl,dom,...
```

### VERSION — Single Version Source

```
v26.1.1
```

Read by: `build.py`, `build.sh` (docker), `build.sh` (native), `package.sh`

### How Config Flows

```
build.conf + VERSION
    │
    ├── Python: lib/config.py → BuildConfig dataclass → build.py
    │
    └── Shell: lib/config.sh → load_version() + load_build_conf() → *.sh scripts
```

Environment variables override `build.conf` values (for CI/CD):

```bash
FRANKENPHP_VERSION=1.12.0 python3 build.py --skip-deploy
```

---

## Shared Shell Library

`lib/frankenphp-common.sh` provides 8 functions used by both Docker and Native deployments:

| Function | Purpose |
|----------|---------|
| `load_env_file [path]` | Parse .env into exported vars |
| `resolve_binary` | Find the FrankenPHP binary |
| `validate_production_env` | Check security-critical env vars (exits on fatal) |
| `extract_frankenphp_app CMD...` | Start binary, wait for extraction, verify, write sentinel |
| `copy_config_files APP_DIR` | Glob-based .example.php → .php activation |
| `run_migrations BINARY APP_DIR` | CakePHP migrations + plugin migrations |
| `run_seeders BINARY APP_DIR` | Auto-detect + seed + reset sequences |
| `apply_php_overrides` | Write runtime PHP INI from env vars |

### Adding a New Function

1. Add the function to `lib/frankenphp-common.sh`
2. Source it in entrypoint.sh / run.sh (already sourced)
3. It's automatically available in both Docker and Native deployments

---

## Embedded Configs

### Caddyfile (builder/Caddyfile)

Embedded in the binary. Controls HTTP routing:

- Static file caching (30-day immutable for CSS/JS/images)
- Security headers (X-Content-Type-Options, X-Frame-Options, HSTS)
- `/healthz` — Caddy-native health endpoint (no PHP)
- `php_server` — CakePHP dynamic routing

### php.ini (builder/php.ini)

Embedded in the binary. Production-optimized:

- `opcache.validate_timestamps = 0` — files never change in embedded binary
- `opcache.jit = 1255` + 64MB JIT buffer
- `session.save_handler = redis`
- `error_reporting = E_ALL & ~E_DEPRECATED & ~E_STRICT`

### Runtime PHP Overrides

Set env vars to override embedded php.ini values at runtime:

```bash
PHP_MEMORY_LIMIT=1G
PHP_UPLOAD_MAX_FILESIZE=200M
PHP_POST_MAX_SIZE=200M
PHP_MAX_EXECUTION_TIME=600
```

These are written to `/tmp/php-overrides/99-overrides.ini` by `apply_php_overrides()`.

---

## CLI Reference

```bash
python3 build.py [OPTIONS]

Build Control:
  --check              Pre-flight checks only
  --verify DIST_DIR    Verify a built dist package (checksums)
  --rebuild-base       Force recompile FrankenPHP base (~30 min)
  --skip-deploy        Build only, don't start containers
  --skip-archive       Reuse existing builder/package/
  --skip-base          Skip base image check
  --keep-package       Keep builder/package/ after build
  --clean              Clean package dir before building

Config:
  --config PATH        Path to build.conf (default: ./build.conf)
  --version VERSION    Override VERSION file

Deploy (when not using --skip-deploy):
  --env-file PATH      Path to .env file
  --app-port PORT      App port
  --app-bind-ip IP     App bind IP
  --db-host HOST       Database host
  --db-port PORT       Database port
  --db-username USER   Database user
  --db-password PASS   Database password
  --db-name NAME       Database name
```

---

## Making Changes

### Changing Application Code

```bash
cd ../apps/orangescrum-v4
# ... make changes ...
cd ../cloud-builder
python3 build.py --skip-deploy    # ~3 min (base cached)
```

### Changing PHP Extensions

1. Edit `build.conf` → `[php_extensions] list = ...`
2. Rebuild base: `python3 build.py --skip-deploy --rebuild-base`

### Changing FrankenPHP Version

1. Edit `build.conf` → `frankenphp_version = 1.12.0`
2. Rebuild base: `python3 build.py --skip-deploy --rebuild-base`

### Changing Caddyfile or php.ini

1. Edit `builder/Caddyfile` or `builder/php.ini`
2. Rebuild app: `python3 build.py --skip-deploy` (no base rebuild needed)

### Adding a Config Template

1. Add `yourconfig.example.php` to `orangescrum-cloud-common/config/`
2. The glob-based `copy_config_files()` will automatically activate it at runtime

### Bumping Version

1. Edit `VERSION` file
2. Run the build — version propagates everywhere automatically

---

## Build Artifacts

After a successful build:

```
dist/{timestamp}/
├── dist-docker/
│   ├── Dockerfile
│   ├── docker-compose.yaml
│   ├── docker-compose.services.yml
│   ├── entrypoint.sh
│   ├── .env.example
│   ├── lib/frankenphp-common.sh
│   ├── config/
│   ├── docs/
│   ├── helpers/
│   ├── orangescrum-app/
│   │   ├── osv4-prod              # ~340 MB static binary
│   │   └── osv4-prod.sha256
│   └── build-manifest.json
│
└── dist-native/
    ├── run.sh
    ├── caddy.sh
    ├── package.sh
    ├── .env.example
    ├── lib/frankenphp-common.sh
    ├── config/
    ├── docs/
    ├── helpers/
    ├── systemd/
    ├── bin/
    │   ├── orangescrum             # ~340 MB static binary
    │   ├── orangescrum.sha256
    │   └── osv4-prod -> orangescrum  (symlink)
    └── build-manifest.json
```

### build-manifest.json

```json
{
  "version": "v26.1.1",
  "git_sha": "c1d5c17c",
  "build_timestamp": "2026-03-29T14:30:00Z",
  "builder_host": "dev-machine",
  "frankenphp_version": "1.11.1",
  "php_version": "8.3",
  "binary_name": "osv4-prod",
  "binary_sha256": "a1b2c3d4...",
  "binary_size_bytes": 356000000
}
```
