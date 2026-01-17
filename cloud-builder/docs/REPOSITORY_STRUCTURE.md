# OrangeScrum Cloud Builder - Repository Structure

Build system for creating static FrankenPHP binaries with embedded OrangeScrum application.

## Directory Structure

```txt
cloud-builder/
├── build.py                        # Main build orchestration script
├── build.py.old                    # Legacy build script (deprecated)
├── deploy.sh                       # Full stack deployment script
├── requirements.txt                # Python dependencies (docker package)
│
├── builder/                        # Docker build context for FrankenPHP
│   ├── base-build.Dockerfile      # Stage 1: Builds FrankenPHP base (slow, cached)
│   ├── app-embed.Dockerfile       # Stage 2: Embeds app into binary (fast)
│   ├── docker-compose.yaml        # Build orchestration (used by build.py)
│   ├── Caddyfile                  # Caddy web server configuration
│   ├── php.ini                    # PHP configuration
│   └── package/                   # TEMP: App source copied here for Docker context
│       └── .gitkeep               # (directory ignored, only .gitkeep tracked)
│
├── orangescrum-cloud/              # Source folder with build scripts
│   ├── build-docker.sh            # Assembles Docker deployment package
│   ├── build-native.sh            # Assembles Native deployment package
│   ├── dist-docker.sh             # Creates distribution tarball (Docker)
│   ├── dist-native.sh             # Creates distribution tarball (Native)
│   ├── dist-all.sh                # Creates both distribution tarballs
│   ├── clean.sh                   # Cleanup script
│   ├── Dockerfile                 # Docker-specific container file
│   ├── docker-compose.yaml        # Docker-specific orchestration
│   ├── docker-compose.services.yml # Infrastructure services (Postgres, Redis, etc)
│   ├── entrypoint.sh              # Docker-specific entrypoint
│   ├── run.sh                     # Native deployment runner
│   ├── run.sh                     # Alternative native runner
│   ├── package.sh                 # Native packaging script
│   ├── caddy.sh                   # Caddy helper script
│   ├── cake.sh                    # CakePHP CLI wrapper
│   ├── queue-worker.sh            # Queue worker wrapper
│   ├── validate-env.sh            # Environment validator
│   ├── .dockerignore              # Docker build exclusions
│   ├── .env                       # Environment config (generated)
│   ├── .env.docker                # Docker-specific env template
│   ├── .env.example               # Environment template
│   └── .env.full.example          # Complete env reference
│
├── orangescrum-cloud-common/       # Common shared files (source of truth)
│   ├── orangescrum-app/           # FrankenPHP binary location
│   │   └── osv4-prod              # Static binary (~340 MB, built by build.py)
│   ├── config/                    # Configuration file templates
│   │   ├── cache_*.example.php   # Cache configurations
│   │   ├── storage.example.php   # S3 storage config
│   │   ├── smtp.example.php      # Email config
│   │   ├── queue.example.php     # Queue config
│   │   ├── apache/               # Apache configs (if needed)
│   │   ├── cron/                 # Cron job configs
│   │   └── plugins/              # Plugin configs
│   ├── docs/                      # Shared documentation
│   │   ├── DEPLOYMENT.md
│   │   ├── ENVIRONMENT_CONFIGURATION.md
│   │   ├── PRODUCTION_DEPLOYMENT_DOCKER.md
│   │   ├── PRODUCTION_DEPLOYMENT_NATIVE.md
│   │   └── ...
│   ├── helpers/                   # Shared helper scripts
│   ├── .env.example               # Base environment template
│   ├── .env.full.example          # Complete configuration reference
│   ├── CONFIGS.md                 # Configuration documentation
│   └── README.md                  # Common files documentation
│
├── orangescrum-cloud-docker/       # Docker deployment source
│   ├── build.sh                   # Assembles dist-docker/ package from common
│   ├── Dockerfile                 # Docker-specific (copied from orangescrum-cloud/)
│   ├── docker-compose.yaml        # Docker orchestration (copied)
│   ├── docker-compose.services.yml # Infrastructure services (copied)
│   ├── entrypoint.sh              # Docker entrypoint (copied)
│   ├── .dockerignore              # Docker build exclusions (copied)
│   ├── .env.example               # Environment template (copied)
│   ├── config/                    # Config files (copied from common)
│   ├── docs/                      # Documentation (copied from common)
│   ├── helpers/                   # Helper scripts (copied from common)
│   ├── orangescrum-app/           # Binary directory
│   │   └── osv4-prod              # (copied from common)
│   ├── CONFIGS.md                 # (copied from common)
│   └── README.md                  # Docker deployment guide
│
├── orangescrum-cloud-native/       # Native deployment source
│   ├── build.sh                   # Assembles dist-native/ package from common
│   ├── run.sh                     # Native runner
│   ├── run.sh                     # Alternative runner (copied)
│   ├── package.sh                 # Packaging script (copied)
│   ├── caddy.sh                   # Caddy helper (copied)
│   ├── .env.example               # Environment template (copied)
│   ├── .env.full.example          # Full env reference (copied)
│   ├── config/                    # Config files (copied from common)
│   ├── docs/                      # Documentation (copied from common)
│   ├── helpers/                   # Helper scripts (copied from common)
│   ├── orangescrum-app/           # Binary directory
│   │   └── osv4-prod              # (copied from common)
│   ├── CONFIGS.md                 # (copied from common)
│   ├── README.md                  # Native deployment guide
│   └── systemd/                   # Systemd service files (native-specific)
│
├── dist-docker/                    # Docker deployment package (auto-generated)
│   ├── Dockerfile                 # Docker-specific container file
│   ├── docker-compose.yaml        # Application orchestration
│   ├── docker-compose.services.yml # Infrastructure services
│   ├── entrypoint.sh              # Container startup script
│   ├── .dockerignore              # Docker build exclusions
│   ├── .env                       # Environment config (to be configured)
│   ├── .env.example               # Environment template
│   ├── config/                    # Configuration templates
│   ├── docs/                      # Documentation
│   ├── helpers/                   # Helper scripts (cake.sh, queue-worker.sh, etc)
│   ├── orangescrum-app/           # Binary directory
│   │   └── osv4-prod              # FrankenPHP binary (~340 MB)
│   ├── CONFIGS.md                 # Configuration documentation
│   └── README.md                  # Deployment instructions
│
├── dist-native/                    # Native deployment package (auto-generated)
│   ├── run.sh                     # Native runner script
│   ├── run.sh                     # Alternative runner
│   ├── package.sh                 # Packaging script
│   ├── caddy.sh                   # Caddy helper
│   ├── .env.example               # Environment template
│   ├── .env.full.example          # Complete env reference
│   ├── config/                    # Configuration templates
│   ├── docs/                      # Documentation
│   ├── helpers/                   # Helper scripts
│   ├── orangescrum-app/           # Binary directory
│   │   └── osv4-prod              # FrankenPHP binary (~340 MB)
│   ├── systemd/                   # Systemd service files
│   ├── CONFIGS.md                 # Configuration documentation
│   └── README.md                  # Deployment instructions
│
└── docs/                           # Build system documentation
    ├── FRANKENPHP_CLI_BEHAVIOR.md
    ├── GIT_SETUP_GUIDE.md
    ├── QUICK_REFERENCE.md
    ├── README.md
    ├── REDIS_QUEUE_SETUP.md
    └── REPOSITORY_STRUCTURE.md     # This file
```

## Build Process Flow

### Overview

The build system uses a **two-stage approach** for optimal build times:

1. **Stage 1 (Slow, Cached)**: Build base FrankenPHP binary with all PHP extensions
2. **Stage 2 (Fast)**: Embed application source code into the binary

```txt
┌─────────────────────────────────────────────────────────────────┐
│ Source: ../apps/orangescrum-v4 (separate directory)             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ git archive / tar
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ builder/package/ (TEMP)                                         │
│ - Extracted source code from orangescrum-v4                     │
│ - Complete CakePHP application structure                        │
│ - Configuration overrides from orangescrum-cloud-common/config/ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ docker build
                              ▼
                  ┌───────────┴───────────┐
                  │                       │
                  ▼                       ▼
┌─────────────────────────────┐  ┌──────────────────────────────┐
│ Stage 1: Base Build         │  │ Stage 2: App Embed           │
│ (base-build.Dockerfile)     │  │ (app-embed.Dockerfile)       │
│ - Build from source (30min) │  │ - Embed app code (2min)      │
│ - Static PHP + Extensions   │  │ - Creates final binary       │
│ - Caddy web server          │  │                              │
│ Image: orangescrum-cloud-base    │  │ Container: app-builder           │
└─────────────────────────────┘  └──────────────────────────────┘
                                            │
                                            │ extract binary
                                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ orangescrum-cloud-common/orangescrum-app/osv4-prod              │
│ - Static binary (~340 MB)                                       │
│ - Self-contained: PHP + Caddy + App                             │
│ - Ready for deployment                                          │
└─────────────────────────────────────────────────────────────────┘
                                            │
                                            │ run build scripts
                                            ▼
                  ┌───────────┴───────────────────────┐
                  │                                   │
                  ▼                                   ▼
┌─────────────────────────────┐  ┌──────────────────────────────┐
│ Docker Deployment           │  │ Native Deployment            │
│ (orangescrum-cloud-docker/) │  │ (orangescrum-cloud-native/)  │
│ - build.sh assembles        │  │ - build.sh assembles         │
│ - Copies from common        │  │ - Copies from common         │
│ - Docker-specific files     │  │ - Native-specific files      │
│ - Output: dist-docker/      │  │ - Output: dist-native/       │
└─────────────────────────────┘  └──────────────────────────────┘
```

## File Categories

### Tracked Files (Committed to Git)

**Build System:**
- Scripts: `build.py`, `deploy.sh`, `*.sh`
- Dockerfiles: `builder/*.Dockerfile`
- Configs: `docker-compose.yaml`, `php.ini`, etc.
- Documentation: `*.md` files

**Source Files:**
- `orangescrum-cloud/` - Build scripts and source templates
- `orangescrum-cloud-common/` - Shared configuration (structure only, no binary)
- `orangescrum-cloud-docker/` - Docker source (structure only)
- `orangescrum-cloud-native/` - Native source (structure only)

### Generated Files (Not Committed)

**Build Artifacts:**
- `orangescrum-cloud-common/orangescrum-app/osv4-prod` - FrankenPHP binary
- `builder/package/` - Temporary extraction directory
- `dist-docker/` - Docker deployment package (built by build.py)
- `dist-native/` - Native deployment package (built by build.py)

**Configuration:**
- `.env` files (except `.env.example`)
- Docker volumes and container data

## Workflow

### Initial Build

```bash
cd cloud-builder
python3 build.py
```

**What happens:**
1. Archives `../apps/orangescrum-v4` application
2. Extracts to `builder/package/`
3. Copies config overrides from `orangescrum-cloud-common/config/`
4. Builds FrankenPHP base image (if needed, ~30 min)
5. Embeds app into FrankenPHP binary (~2 min)
6. Extracts binary to `orangescrum-cloud-common/orangescrum-app/osv4-prod`
7. Runs `orangescrum-cloud-docker/build.sh` → creates `dist-docker/`
8. Runs `orangescrum-cloud-native/build.sh` → creates `dist-native/`

### Subsequent Builds (Code Changes)

```bash
python3 build.py
# Base image is cached, only app embedding runs (~2 min)
```

### Rebuild Deployment Packages Only

```bash
# If you've updated common files but not the binary
cd orangescrum-cloud-docker
./build.sh

cd ../orangescrum-cloud-native
./build.sh
```

## Key Concepts

### Source of Truth

- **Common Files**: `orangescrum-cloud-common/` contains shared files
- **Build Scripts**: `orangescrum-cloud/` contains build orchestration scripts
- **Deployment Sources**: `orangescrum-cloud-docker/` and `orangescrum-cloud-native/` contain deployment-specific files

### Auto-Generated Folders

- `dist-docker/` and `dist-native/` are **built by build.py**
- Never edit these directly; rebuild from sources instead
- Safe to delete and rebuild at any time

### Binary Location

The FrankenPHP binary lives in one place:
- `orangescrum-cloud-common/orangescrum-app/osv4-prod`

Build scripts copy it to deployment packages:
- `dist-docker/orangescrum-app/osv4-prod`
- `dist-native/orangescrum-app/osv4-prod`

└─────────────────────────────────────────────────────────────────┘
```

## Deployment Quick Start

### First-time Build (Slow ~30 min)

```bash
# Build everything from scratch
python3 build.py
```

### Subsequent Builds (Fast ~2 min)

```bash
# Skip base image rebuild, only embed new app code
python3 build.py --skip-base
```

### Force Rebuild Base Image

```bash
# Rebuild base image from scratch
python3 build.py --rebuild-base
```

## Package What Gets Committed vs Ignored

### [OK] Committed (Tracked by Git)

- Build scripts: `build.py`, `requirements.txt`
- Docker configurations: `builder/*.Dockerfile`, `builder/docker-compose.yaml`
- Deployment package: `orangescrum-ee/` (structure only, not binary)
  - `run.sh` - Binary runner script
  - `.env.example` - Configuration template
- Documentation: All `.md` files
- Configuration templates
- `.gitkeep` files for temp directories

### [ERROR] Ignored (Not Tracked)

- Built binary: `orangescrum-ee/orangescrum-app/orangescrum-ee`
- Temporary source: `package/*` (except `.gitkeep`)
- Docker build context: `builder/package/*` (except `.gitkeep`)
- Build artifacts: `*.tar`, `repo.tar`
- Environment files: `.env`, `.env.*` (except examples)
- Backups: `backups/*`
- IDE files: `.vscode/`, `.idea/`
- Python cache: `__pycache__/`, `*.pyc`

## Configuration Build System Components

### 1. Source Extraction (`package/`)

**Purpose**: Temporary directory for extracted source code from `durango-pg` repository.

**Process**:

1. Script runs `git archive` on `durango-pg`
2. Extracts to `package/`
3. Contains complete CakePHP application structure

**Lifecycle**: Created during build, can be deleted after

### 2. Docker Build Context (`builder/package/`)

**Purpose**: Copy of source code within Docker build context.

**Process**:

1. Contents of `package/` copied here
2. Used by `app-embed.Dockerfile` to embed into binary
3. Docker can access this directory during build

**Lifecycle**: Created during build, can be deleted after

### 3. Deployment Package (`orangescrum-ee/`)

**Purpose**: Final distribution package ready for deployment.

**Contains**:

- **Runtime container**: Minimal Alpine image with binary
- **Entrypoint script**: Handles initialization, migrations, seeding
- **Docker Compose**: Production deployment configuration
- **Binary**: `orangescrum-app/orangescrum-ee` (ignored, built separately)

**Features**:

- [OK] Automatic database migrations
- [OK] Intelligent seeding (idempotent)
- [OK] Volume persistence
- [OK] Multi-environment support
- [OK] External/bundled database options

## Database Database Seeding

The entrypoint script includes automatic database seeding with safeguards:

### Features

1. **Primary Key Configuration**:
   - Runs `pg_config_1.sql` before seeding (disables PK constraints)
   - Runs `pg_config_2.sql` after seeding (resets sequences)

2. **Idempotent Seeding**:
   - Checks if data exists before running seeds
   - Skips seeding if records found
   - Safe for container restarts

3. **Automatic Migrations**:
   - Runs main application migrations
   - Runs plugin migrations (Gitsync)
   - Creates schema dumps

### Configuration Files

Located in `durango-pg/config/schema/`:

- `pg_config_1.sql`: Changes identity columns to allow explicit IDs
- `pg_config_2.sql`: Resets sequences to correct next values

## Environment Environment Configurations

### Available Environments

1. **External Database (Host IP)**:

   ```bash
   # .env.test-external-hostip
   DB_HOST=192.168.2.132
   ```

2. **External Database (Container Network)**:

   ```bash
   # .env.test-external-container
   DB_HOST=durango-postgres-postgres-1
   ```

3. **External Database (Host Gateway)**:

   ```bash
   # .env.test-external-hostgateway
   DB_HOST=host.docker.internal
   ```

4. **Bundled Database**:

   ```bash
   # .env.test-bundled
   DB_HOST=orangescrum-db
   # Start with: --profile bundled-db
   ```

### Usage

```bash
# Start with specific environment
cd orangescrum-ee
docker compose --env-file .env.test-external-hostip up -d

# Bundled database
docker compose --env-file .env.test-bundled --profile bundled-db up -d
```

## Verification Verification Commands

### Check Binary

```bash
# Test binary
./orangescrum-ee/orangescrum-app/orangescrum-ee version
./orangescrum-ee/orangescrum-app/orangescrum-ee build-info
```

### Monitor Application

```bash
# View logs
docker logs orangescrum-multitenant-base-orangescrum-app-1 -f

# Check database
docker exec <container> psql -U postgres -d dbname -c "SELECT COUNT(*) FROM actions;"
```

### Test Seed Workflow

```bash
# Check if seeds ran
docker logs <container> | grep "Database seeding:"

# Verify sequences
docker exec <container> psql ... -c "SELECT nextval('actions_id_seq');"
```

## Development Development Workflow

### Making Code Changes

1. Make changes in `durango-pg` repository
2. Commit changes
3. Run build:

   ```bash
   python3 build.py --skip-base
   ```

4. Test deployment

### Changing PHP Extensions

1. Modify `builder/base-build.Dockerfile`
2. Rebuild base image:

   ```bash
   python3 build.py --rebuild-base
   ```

### Updating Dependencies

1. Update `durango-pg/composer.json`
2. Run full build:

   ```bash
   python3 build.py
   ```

## Stats Build Times

| Stage | First Build | Subsequent | Notes |
|-------|------------|------------|-------|
| Base Image | ~30 min | Skipped (cached) | Only when deps change |
| App Embed | ~2 min | ~2 min | Every code change |
| **Total** | **~32 min** | **~2 min** | Optimized workflow |

## Security Production Deployment

See [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md) for:

- Security considerations
- Volume management
- Backup strategies
- Multi-tenant setup
- Database configuration

## Documentation Additional Documentation

- [BUILD_OPTIMIZATION.md](builder/BUILD_OPTIMIZATION.md) - Build system architecture
- [DATABASE_TESTING.md](DATABASE_TESTING.md) - Database testing strategies
- [PERSISTENCE_SOLUTION.md](PERSISTENCE_SOLUTION.md) - Data persistence approach
- [VOLUME_SAFETY.md](VOLUME_SAFETY.md) - Volume backup procedures

## Contributing Contributing

When contributing to this build system:

1. **Never commit binaries**: The `orangescrum-ee` binary is ignored
2. **Keep temp dirs clean**: `package/` and `builder/package/` are auto-generated
3. **Test all environments**: Verify changes work with all `.env.test-*` configs
4. **Document changes**: Update relevant `.md` files
5. **Verify builds**: Run both full and incremental builds

## [WARNING] Important Notes

- **Binary Size**: The final binary is 150+ MB (PHP + Caddy + App)
- **Build Cache**: First build creates base image, reused for all future builds
- **Temp Directories**: `package/` and `builder/package/` can be deleted anytime
- **Deployment Only**: Only `orangescrum-ee/` folder is needed for deployment
- **Database**: Supports both external PostgreSQL and bundled option
- **Idempotent**: Safe to restart containers, migrations/seeds won't duplicate

## 🆘 Troubleshooting

### Build Fails

```bash
# Clean and rebuild (using build.py)
python3 build.py --rebuild-base
```

### Binary Not Working

```bash
# Check permissions
chmod +x orangescrum-ee/orangescrum-app/orangescrum-ee

# Test binary
./orangescrum-ee/orangescrum-app/orangescrum-ee version
```

### Seeds Not Running

```bash
# Check logs
docker logs <container> | grep -A 20 "Database seeding:"

# Manual seed check
docker exec <container> psql ... -c "SELECT COUNT(*) FROM actions;"
```

## License License

See LICENSE file in the main repository.
