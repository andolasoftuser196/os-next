# Durango Builder - FrankenPHP Build System

Build system for creating static FrankenPHP binaries with embedded OrangeScrum application.

## 📁 Repository Structure

```txt
durango-builder/
├── build.py                    # Main build script (optimized two-stage build)
├── build_optimized.py          # Alternate/verbose build script (two-stage build)
├── backup_volumes.sh           # Script to backup Docker volumes
│
├── builder/                    # Docker build context for FrankenPHP
│   ├── base-build.Dockerfile       # Stage 1: Builds FrankenPHP base (slow, cached)
│   ├── app-embed.Dockerfile        # Stage 2: Embeds app into binary (fast)
│   ├── docker-compose.yaml   # Two-stage build compose file
│   ├── package/                    # TEMP: App source copied here for Docker context
│   │   └── .gitkeep                   # (directory ignored, only .gitkeep tracked)
│   └── BUILD_OPTIMIZATION.md       # Build optimization documentation
│
├── package/                    # TEMP: Git archive extraction target
│   └── .gitkeep                   # (directory ignored, only .gitkeep tracked)
│
├── orangescrum-ee/             # 🚀 DEPLOYMENT FOLDER (distribution package)
│   ├── docker-compose.yaml         # Production deployment compose file
│   ├── Dockerfile                  # Runtime container (Alpine + binary)
│   ├── entrypoint.sh              # Container entrypoint with migrations & seeds
│   ├── .env.example               # Environment configuration template
│   ├── .env.test-*                # Test environment configurations
│   └── orangescrum-app/           # Binary output directory
│       └── orangescrum-ee         # ⚠️ IGNORED - Built binary (150+ MB)
│
├── backups/                    # TEMP: Docker volume backups
│   └── (ignored)
│
└── docs/                       # Documentation
    ├── DATABASE_TESTING.md
    ├── PERSISTENCE_SOLUTION.md
    ├── PRODUCTION_DEPLOYMENT.md
    ├── VOLUME_SAFETY.md
    ├── README_OLD.md
    └── README.md
```

## 🔄 Build Process Flow

### Overview

The build system uses a **two-stage approach** for optimal build times:

1. **Stage 1 (Slow, Cached)**: Build base FrankenPHP binary with all PHP extensions
2. **Stage 2 (Fast)**: Embed application source code into the binary

```txt
┌─────────────────────────────────────────────────────────────────┐
│ Source: durango-pg (separate repo)                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ git archive
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ package/ (TEMP)                                                 │
│ - Extracted source code from durango-pg                         │
│ - Complete CakePHP application structure                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ copy to Docker context
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ builder/package/ (TEMP)                                         │
│ - App source ready for Docker build                             │
│ - Used by app-embed.Dockerfile                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                  ┌───────────┴───────────┐
                  │                       │
                  ▼                       ▼
┌─────────────────────────────┐  ┌──────────────────────────────┐
│ Stage 1: Base Build         │  │ Stage 2: App Embed           │
│ - Build from source (30min) │  │ - Embed app code (2min)      │
│ - Static PHP + Extensions   │  │ - Creates final binary       │
│ - Caddy web server          │  │                              │
│ Image: orangescrum-cloud-base      │  │ Container: *-app-builder     │
└─────────────────────────────┘  └──────────────────────────────┘
                                            │
                                            │ extract binary
                                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ orangescrum-ee/orangescrum-app/orangescrum-ee                   │
│ - Static binary (150+ MB)                                       │
│ - Self-contained: PHP + Caddy + App                             │
│ - Ready for deployment                                          │
└─────────────────────────────────────────────────────────────────┘
                                            │
                                            │ docker build
                                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ DEPLOYMENT: orangescrum-ee/                                     │
│ - Alpine container + binary                                     │
│ - Entrypoint with migrations & seeds                            │
│ - Volume management for persistence                             │
│ - Multi-tenant database support                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### First-time Build (Slow ~30 min)

```bash
# Build everything from scratch
python3 build_optimized.py
```

### Subsequent Builds (Fast ~2 min)

```bash
# Skip base image rebuild, only embed new app code
python3 build_optimized.py --skip-base
```

### Force Rebuild Base Image

```bash
# Rebuild base image from scratch
python3 build_optimized.py --rebuild-base
```

## 📦 What Gets Committed vs Ignored

### ✅ Committed (Tracked by Git)

- Build scripts: `build_optimized.py`, `build.py`
- Docker configurations: `builder/*.Dockerfile`, `builder/*.yaml`
- Deployment package: `orangescrum-ee/` (structure only, not binary)
  - `docker-compose.yaml`
  - `Dockerfile`
  - `entrypoint.sh`
  - `.env.example`
- Documentation: All `.md` files
- Configuration templates
- `.gitkeep` files for temp directories

### ❌ Ignored (Not Tracked)

- Built binary: `orangescrum-ee/orangescrum-app/orangescrum-ee`
- Temporary source: `package/*` (except `.gitkeep`)
- Docker build context: `builder/package/*` (except `.gitkeep`)
- Build artifacts: `*.tar`, `repo.tar`
- Environment files: `.env`, `.env.*` (except examples)
- Backups: `backups/*`
- IDE files: `.vscode/`, `.idea/`
- Python cache: `__pycache__/`, `*.pyc`

## 🔧 Build System Components

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

- ✅ Automatic database migrations
- ✅ Intelligent seeding (idempotent)
- ✅ Volume persistence
- ✅ Multi-environment support
- ✅ External/bundled database options

## 🗄️ Database Seeding

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

## 🌍 Environment Configurations

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

## 🔍 Verification Commands

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

## 🛠️ Development Workflow

### Making Code Changes

1. Make changes in `durango-pg` repository
2. Commit changes
3. Run build:

   ```bash
   python3 build_optimized.py --skip-base
   ```

4. Test deployment

### Changing PHP Extensions

1. Modify `builder/base-build.Dockerfile`
2. Rebuild base image:

   ```bash
   python3 build_optimized.py --rebuild-base
   ```

### Updating Dependencies

1. Update `durango-pg/composer.json`
2. Run full build:

   ```bash
   python3 build_optimized.py
   ```

## 📊 Build Times

| Stage | First Build | Subsequent | Notes |
|-------|------------|------------|-------|
| Base Image | ~30 min | Skipped (cached) | Only when deps change |
| App Embed | ~2 min | ~2 min | Every code change |
| **Total** | **~32 min** | **~2 min** | Optimized workflow |

## 🔒 Production Deployment

See [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md) for:

- Security considerations
- Volume management
- Backup strategies
- Multi-tenant setup
- Database configuration

## 📝 Additional Documentation

- [BUILD_OPTIMIZATION.md](builder/BUILD_OPTIMIZATION.md) - Build system architecture
- [DATABASE_TESTING.md](DATABASE_TESTING.md) - Database testing strategies
- [PERSISTENCE_SOLUTION.md](PERSISTENCE_SOLUTION.md) - Data persistence approach
- [VOLUME_SAFETY.md](VOLUME_SAFETY.md) - Volume backup procedures

## 🤝 Contributing

When contributing to this build system:

1. **Never commit binaries**: The `orangescrum-ee` binary is ignored
2. **Keep temp dirs clean**: `package/` and `builder/package/` are auto-generated
3. **Test all environments**: Verify changes work with all `.env.test-*` configs
4. **Document changes**: Update relevant `.md` files
5. **Verify builds**: Run both full and incremental builds

## ⚠️ Important Notes

- **Binary Size**: The final binary is 150+ MB (PHP + Caddy + App)
- **Build Cache**: First build creates base image, reused for all future builds
- **Temp Directories**: `package/` and `builder/package/` can be deleted anytime
- **Deployment Only**: Only `orangescrum-ee/` folder is needed for deployment
- **Database**: Supports both external PostgreSQL and bundled option
- **Idempotent**: Safe to restart containers, migrations/seeds won't duplicate

## 🆘 Troubleshooting

### Build Fails

```bash
# Clean and rebuild
docker compose -f builder/docker-compose.yaml down
python3 build_optimized.py --rebuild-base
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

## 📄 License

See LICENSE file in the main repository.
