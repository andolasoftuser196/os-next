# OrangeScrum V4 FrankenPHP Cloud Builder

Build system for creating a standalone FrankenPHP binary of OrangeScrum V4 for cloud deployment.

---

## What This Does

This builder creates a **single static binary** containing:

- FrankenPHP web server
- PHP 8.3 runtime
- OrangeScrum V4 application code

The resulting binary is self-contained and can be deployed to any cloud platform without requiring PHP installation or a separate web server.

---

## Project Structure

```
cloud-builder/
├── build.py                        # Main build orchestrator
├── builder/                        # FrankenPHP build environment
│   ├── base-build.Dockerfile      # Stage 1: FrankenPHP base (cached)
│   ├── app-embed.Dockerfile       # Stage 2: Embed app (fast)
│   └── docker-compose.yaml        # Build orchestration
│
├── orangescrum-cloud/              # Source folder with build scripts
│   ├── build-docker.sh            # Build Docker deployment package
│   ├── build-native.sh            # Build Native deployment package
│   ├── dist-docker.sh             # Create distribution tarball (Docker)
│   ├── dist-native.sh             # Create distribution tarball (Native)
│   └── ...deployment-specific files...
│
├── orangescrum-cloud-common/       # Common shared files
│   ├── orangescrum-app/           # FrankenPHP binary (built)
│   │   └── osv4-prod              # Static binary (~340 MB)
│   ├── config/                    # Configuration templates
│   ├── docs/                      # Shared documentation
│   └── helpers/                   # Helper scripts
│
├── orangescrum-cloud-docker/       # Docker deployment source
│   ├── build.sh                   # Assembles Docker package
│   ├── Dockerfile                 # Docker-specific
│   ├── docker-compose.yaml        # Docker orchestration
│   └── ...copied from common...
│
├── orangescrum-cloud-native/       # Native deployment source
│   ├── build.sh                   # Assembles Native package
│   ├── run.sh                     # Native deployment runner
│   └── ...copied from common...
│
├── dist-docker/                    # Docker deployment package (built)
└── dist-native/                    # Native deployment package (built)
```

---

## Architecture

### Source Application

- **OrangeScrum V4** from `../apps/orangescrum-v4` (PHP 8.3 + PostgreSQL)

### Build Process

1. Archives the application code from `../apps/orangescrum-v4`
2. Embeds it into FrankenPHP using multi-stage Docker build
3. Produces a standalone binary at `orangescrum-cloud-common/orangescrum-app/osv4-prod` (~340 MB)
4. Runs build scripts to create deployment packages at `dist-docker/` and `dist-native/`

### External Dependencies

- **PostgreSQL Database**: Must be provided externally (see `.env` configuration)
- **Redis**: Optional, for caching and queue (can use file-based cache)
- **S3 Storage**: Optional, for file storage (MinIO or AWS S3)

---

## Quick Start

### Prerequisites

```bash
# Check Docker
docker --version          # Need 24.0+
docker compose version    # Need v2.0+

# Check Python  
python3 --version         # Need 3.8+

# Install Docker Python SDK
pip install docker
```

### Step 1: Prepare Application Code

Ensure OrangeScrum V4 application exists:

```bash
ls ../apps/orangescrum-v4
# Should contain: index.php, config/, src/, webroot/, etc.
```

### Step 2: Build FrankenPHP Binary & Deployment Packages

```bash
cd cloud-builder

# First build (builds base image + app, ~10-15 minutes)
python3 build.py

# Subsequent builds (only rebuilds app, ~2-3 minutes)
python3 build.py

# This creates:
# - orangescrum-cloud-common/orangescrum-app/osv4-prod (binary)
# - dist-docker/ (Docker deployment package)
# - dist-native/ (Native deployment package)
```

### Step 3: Choose Deployment Type

Choose between Docker or Native deployment:

#### Option A: Docker Deployment (Recommended)

```bash
cd dist-docker

# Copy example environment file
cp .env.example .env

# Edit .env to configure database, security, etc.
nano .env

# Start infrastructure services (PostgreSQL, Redis, MinIO, MailHog)
docker-compose -f docker-compose.services.yml up -d

# Start the application
docker compose up -d

# View logs
docker compose logs -f orangescrum-app
```

See [dist-docker/README.md](dist-docker/README.md) for complete Docker deployment guide.

#### Option B: Native Deployment (Direct System Execution)

```bash
cd dist-native

# Copy example environment file
cp .env.example .env

# Edit .env to configure database, security, etc.
nano .env

# Validate configuration
./validate-env.sh

# Run application (foreground)
./run.sh

# Or run as daemon
DAEMON=true ./run.sh &
```

See [dist-native/README.md](dist-native/README.md) for complete native deployment guide.

**Critical Settings (both deployments):**

- `DB_HOST`: Your PostgreSQL server (e.g., `localhost` or `192.168.49.10`)
- `DB_NAME`: `orangescrum`
- `DB_USERNAME`: `postgres` or `orangescrum`
- `DB_PASSWORD`: Use a strong password!
- `SECURITY_SALT`: Generate with `openssl rand -base64 32`

The application will be available at `http://localhost:8080` (or configured port).

---

## Build Options

### Rebuild Base Image

Force rebuild of the FrankenPHP base image (slow, only needed for dependency changes):

```bash
python3 build.py --rebuild-base
```

### Build Only (Skip Deployment)

Build the binary without deploying:

```bash
python3 build.py --skip-deploy
```

The binary will be at `orangescrum-cloud-common/orangescrum-app/osv4-prod`.

### Clean Build

Clean package directory before building:

```bash
python3 build.py --clean
```

---

## Deployment Architecture

### Deployment Options

This builder supports two deployment methods:

1. **Docker Deployment** (`dist-docker/`)
   - Containerized deployment with Docker Compose
   - Includes infrastructure services (PostgreSQL, Redis, MinIO)
   - Easy orchestration and scaling
   - Recommended for most users
   - Built from `orangescrum-cloud-docker/`

2. **Native Deployment** (`dist-native/`)
   - Direct system execution without containers
   - Better performance, lower overhead
   - Requires manual service configuration
   - Ideal for production servers with existing infrastructure
   - Built from `orangescrum-cloud-native/`

### Local Development

**Docker:**
- Use `dist-docker/docker-compose.yaml`
- Includes local PostgreSQL, Redis, MinIO, and MailHog
- Exposes port 8080 by default

**Native:**
- Use `dist-native/run.sh`
- Requires external PostgreSQL, Redis (optional), and S3 (optional)
- Exposes port 8080 by default

### Production Deployment

The FrankenPHP binary can be deployed to:

- **Cloud Platforms**: AWS, Google Cloud, Azure, DigitalOcean
- **Container Platforms**: Kubernetes, Docker Swarm, ECS
- **Serverless**: Cloud Run, Lambda (with container support)
- **VPS/Bare Metal**: Any Linux server (native deployment)

**Production Guides:**
- Docker: [orangescrum-cloud-common/docs/PRODUCTION_DEPLOYMENT_DOCKER.md](orangescrum-cloud-common/docs/PRODUCTION_DEPLOYMENT_DOCKER.md)
- Native: [orangescrum-cloud-common/docs/PRODUCTION_DEPLOYMENT_NATIVE.md](orangescrum-cloud-common/docs/PRODUCTION_DEPLOYMENT_NATIVE.md)

### Environment Variables

Required:

- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USERNAME`, `DB_PASSWORD`
- `SECURITY_SALT`

Optional:

- `REDIS_HOST`, `REDIS_PORT` (caching/queue)
- `STORAGE_ENDPOINT`, `STORAGE_ACCESS_KEY`, `STORAGE_SECRET_KEY` (S3)
- `EMAIL_API_KEY`, `FROM_EMAIL` (SendGrid email)
- `FULL_BASE_URL` (application URL)

See `.env.example` files in deployment packages for complete lists.

---

## How The Build System Works

### Build Flow

```
1. Source Code (../apps/orangescrum-v4)
   ↓ git archive
2. Extract → builder/package/
   ↓ docker build (base-build.Dockerfile)
3. FrankenPHP Base Image (cached) ~30 min first time
   ↓ docker build (app-embed.Dockerfile)
4. FrankenPHP Binary → orangescrum-cloud-common/orangescrum-app/osv4-prod ~2 min
   ↓ run build scripts
5. Deployment Packages:
   - orangescrum-cloud-docker/build.sh → dist-docker/
   - orangescrum-cloud-native/build.sh → dist-native/
```

### Directory Relationships

```
cloud-builder/
│
├── orangescrum-cloud/              ← Source scripts (build-docker.sh, build-native.sh)
│
├── orangescrum-cloud-common/       ← Shared files + binary
│   └── orangescrum-app/osv4-prod  ← Built by build.py
│
├── orangescrum-cloud-docker/       ← Docker source (Dockerfile, compose files)
│   └── build.sh                    ← Assembles dist-docker/ package
│
├── orangescrum-cloud-native/       ← Native source (run scripts)
│   └── build.sh                    ← Assembles dist-native/ package
│
├── dist-docker/                    ← Ready-to-deploy Docker package
│   └── orangescrum-app/osv4-prod  ← Copied from common
│
└── dist-native/                    ← Ready-to-deploy Native package
    └── orangescrum-app/osv4-prod  ← Copied from common
```

### Making Changes

**To update shared files (config, docs, helpers):**
1. Edit in `orangescrum-cloud-common/`
2. Run `python3 build.py --skip-archive --skip-base` to rebuild packages

**To update Docker-specific files:**
1. Edit in `orangescrum-cloud-docker/`
2. Run `cd orangescrum-cloud-docker && ./build.sh`

**To update Native-specific files:**
1. Edit in `orangescrum-cloud-native/`
2. Run `cd orangescrum-cloud-native && ./build.sh`

---

## File Structure Reference

See [docs/REPOSITORY_STRUCTURE.md](docs/REPOSITORY_STRUCTURE.md) for detailed structure documentation.

---

## Troubleshooting

### Build Fails: "OrangeScrum V4 directory not found"

Ensure the application code exists:

```bash
ls ../apps/orangescrum-v4
```

### Binary Size Too Large

The binary is ~340 MB, which includes:

- FrankenPHP server
- PHP 8.3 runtime  
- All PHP extensions
- Application code

This is normal for a standalone binary.

### Database Connection Fails

Check your deployment package `.env` file:

```bash
cd dist-docker  # or dist-native
cat .env | grep DB_
```

Ensure PostgreSQL is accessible (use `host.docker.internal` for Docker on Mac/Windows).

### Port Already in Use

Change the port in `.env`:

```bash
APP_PORT=8081
```

Then restart the service.

---

## Advanced Usage

### Custom Base Image

Override the base image:

```bash
export FRANKENPHP_BASE_IMAGE=my-custom-frankenphp:latest
python3 build.py
```

### Configuration Overrides

Place custom PHP config files in `orangescrum-cloud-common/config/`:

- `cache_redis.example.php` - Redis cache configuration
- `queue.example.php` - Queue configuration  
- `storage.example.php` - S3 storage configuration
- `sendgrid.example.php` - Email configuration

These will be copied to deployment packages during build.

---

## Documentation

- [DEPLOYMENT_SEPARATION.md](DEPLOYMENT_SEPARATION.md) - Architecture & deployment separation explained
- [docs/REPOSITORY_STRUCTURE.md](docs/REPOSITORY_STRUCTURE.md) - Detailed directory structure
- [docs/QUICK_REFERENCE.md](docs/QUICK_REFERENCE.md) - Command quick reference
- [docs/README.md](docs/README.md) - Documentation index

---

## Support

For issues:

1. Check logs: `cd dist-docker && docker compose logs orangescrum-app`
2. Verify database connectivity
3. Review `.env` configuration in deployment package
4. Ensure all required environment variables are set

---

## Related Projects

- Main Workspace: `../README.md` - Multi-application Docker setup
- OrangeScrum V4: `../apps/orangescrum-v4/` - Source application
- FrankenPHP: <https://frankenphp.dev/> - PHP application server


## Quick Reference

**Print this for your desk:**

```txt
╔════════════════════════════════════════════════════════╗
║           ORANGESCRUM DEPLOYMENT CHEAT SHEET            ║
╠════════════════════════════════════════════════════════╣
║ Setup (First Time):                                    ║
║   cd durango-builder                                   ║
║   python3 -m venv ../.venv                             ║
║   source ../.venv/bin/activate                         ║
║   pip install docker                                   ║
╠════════════════════════════════════════════════════════╣
║ Daily Commands:                                        ║
║   ./deploy.sh --interactive    → Open menu             ║
║   ./deploy.sh --status        → Check status           ║
║   ./deploy.sh --check         → Run diagnostics        ║
║   ./deploy.sh --logs <name>   → View logs              ║
╠════════════════════════════════════════════════════════╣
║ Services:                                              ║
║   orangescrum-app         → Main app                   ║
║   orangescrum-postgresdb  → Database                   ║
║   orangescrum-storage     → MinIO files                ║
║   orangescrum-reports     → Superset                   ║
║   orangescrum-os-optimize → API                        ║
╠════════════════════════════════════════════════════════╣
║ Access:                                                ║
║   http://192.168.2.132     → OrangeScrum               ║
║   http://localhost:9090    → MinIO Console             ║
║   http://localhost:8088    → Reports                   ║
║   http://localhost:9091    → OS-Optimize               ║
╠════════════════════════════════════════════════════════╣
║ Emergency:                                             ║
║   1. Check logs: ./deploy.sh --logs <service>          ║
║   2. Restart all: Choose option 4 in interactive       ║
║   3. Nuclear reset: docker compose down -v             ║
╚════════════════════════════════════════════════════════╝
```

---

**Last Updated:** December 3, 2025

**Questions?** Check the [Technical Architecture](docs/TECHNICAL_ARCHITECTURE.md) or ask your team lead.
