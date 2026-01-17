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

## Architecture

### Source Application

- **OrangeScrum V4** from `../apps/orangescrum-v4` (PHP 8.3 + PostgreSQL)

### Build Process

1. Archives the application code
2. Embeds it into FrankenPHP using multi-stage Docker build
3. Produces a standalone `orangescrum-cloud` binary (~340 MB)
4. Optionally deploys using `orangescrum-cloud/docker-compose.yaml`

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

### Step 2: Build FrankenPHP Binary

```bash
cd cloud-builder

# First build (builds base image + app, ~10-15 minutes)
python3 build.py

# Subsequent builds (only rebuilds app, ~2-3 minutes)
python3 build.py
```

### Step 3: Choose Deployment Type

Choose between Docker or Native deployment:

#### Option A: Docker Deployment (Recommended)

```bash
cd orangescrum-cloud-docker

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

📘 See [orangescrum-cloud-docker/README.md](orangescrum-cloud-docker/README.md) for complete Docker deployment guide.

#### Option B: Native Deployment (Direct System Execution)

```bash
cd orangescrum-cloud-native

# Copy example environment file
cp .env.example .env

# Edit .env to configure database, security, etc.
nano .env

# Validate configuration
./validate-env.sh

# Run application (foreground)
./run-native.sh

# Or run as daemon
DAEMON=true ./run-native.sh &
```

📘 See [orangescrum-cloud-native/README.md](orangescrum-cloud-native/README.md) for complete native deployment guide.

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

The binary will be at `orangescrum-cloud/orangescrum-app/orangescrum-cloud`.

### Clean Build

Clean package directory before building:

```bash
python3 build.py --clean
```

---

## Deployment Architecture

### Deployment Options

This builder supports two deployment methods:

1. **🐳 Docker Deployment** (`orangescrum-cloud-docker/`)
   - Containerized deployment with Docker Compose
   - Includes infrastructure services (PostgreSQL, Redis, MinIO)
   - Easy orchestration and scaling
   - Recommended for most users
   - See [orangescrum-cloud-docker/README.md](orangescrum-cloud-docker/README.md)

2. **🖥️ Native Deployment** (`orangescrum-cloud-native/`)
   - Direct system execution without containers
   - Better performance, lower overhead
   - Requires manual service configuration
   - Ideal for production servers with existing infrastructure
   - See [orangescrum-cloud-native/README.md](orangescrum-cloud-native/README.md)

### Local Development

**Docker:**
- Use `orangescrum-cloud-docker/docker-compose.yaml`
- Includes local PostgreSQL, Redis, MinIO, and MailHog
- Exposes port 8080 by default

**Native:**
- Use `orangescrum-cloud-native/run-native.sh`
- Requires external PostgreSQL, Redis (optional), and S3 (optional)
- Exposes port 8080 by default

### Production Deployment

The FrankenPHP binary can be deployed to:

- **Cloud Platforms**: AWS, Google Cloud, Azure, DigitalOcean
- **Container Platforms**: Kubernetes, Docker Swarm, ECS
- **Serverless**: Cloud Run, Lambda (with container support)
- **VPS/Bare Metal**: Any Linux server (native deployment)

📘 **Production Guides:**
- Docker: [orangescrum-cloud-docker/docs/PRODUCTION_DEPLOYMENT_DOCKER.md](orangescrum-cloud-docker/docs/PRODUCTION_DEPLOYMENT_DOCKER.md)
- Native: [orangescrum-cloud-native/docs/PRODUCTION_DEPLOYMENT_NATIVE.md](orangescrum-cloud-native/docs/PRODUCTION_DEPLOYMENT_NATIVE.md)

### Environment Variables

Required:

- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USERNAME`, `DB_PASSWORD`
- `SECURITY_SALT`

Optional:

- `REDIS_HOST`, `REDIS_PORT` (caching/queue)
- `STORAGE_ENDPOINT`, `STORAGE_ACCESS_KEY`, `STORAGE_SECRET_KEY` (S3)
- `EMAIL_API_KEY`, `FROM_EMAIL` (SendGrid email)
- `FULL_BASE_URL` (application URL)

---

## File Structure

```
cloud-builder/
├── build.py                        # Main build script
├── builder/
│   ├── base-build.Dockerfile       # FrankenPHP base image
│   ├── app-embed.Dockerfile        # App embedding
│   └── docker-compose.yaml         # Builder services
├── orangescrum-cloud-docker/       # Docker deployment
│   ├── docker-compose.yaml         # Application orchestration
│   ├── docker-compose.services.yml # Infrastructure services
│   ├── Dockerfile                  # Production container
│   ├── entrypoint.sh               # Container startup
│   ├── .env.example                # Environment template
│   ├── config/                     # Configuration files
│   ├── docs/                       # Docker-specific docs
│   └── orangescrum-app/
│       └── osv4-prod               # Static binary (generated)
├── orangescrum-cloud-native/       # Native deployment
│   ├── run-native.sh               # Native runner script
│   ├── run.sh                      # Alternative runner
│   ├── .env.example                # Environment template
│   ├── validate-env.sh             # Configuration validator
│   ├── config/                     # Configuration files
│   ├── docs/                       # Native-specific docs
│   └── orangescrum-app/
│       └── osv4-prod               # Static binary (generated)
└── orangescrum-cloud/              # Legacy (deprecated)
    └── ...                         # Use -docker or -native instead
```

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

Check your `.env` file settings:

```bash
cd orangescrum-cloud
cat .env | grep DB_
```

Ensure PostgreSQL is accessible from the container (use `host.docker.internal` for localhost).

### Port Already in Use

Change the port in `.env`:

```bash
APP_PORT=8081
```

Then restart:

```bash
docker compose down
docker compose up -d
```

---

## Advanced Usage

### Custom Base Image

Override the base image:

```bash
export FRANKENPHP_BASE_IMAGE=my-custom-frankenphp:latest
python3 build.py
```

### Configuration Overrides

Place custom PHP config files in `orangescrum-cloud/config/`:

- `cache_redis.example.php` - Redis cache configuration
- `queue.example.php` - Queue configuration  
- `storage.example.php` - S3 storage configuration
- `sendgrid.example.php` - Email configuration

These will be copied to the package during build.

### Multi-Stage Production Build

The `orangescrum-cloud/Dockerfile` uses the generated binary:

```dockerfile
FROM alpine:latest
COPY orangescrum-app/orangescrum-cloud /usr/local/bin/
ENTRYPOINT ["/usr/local/bin/orangescrum-cloud"]
```

---

## Related Documentation

- Main Project: `../README.md` - Multi-application Docker setup
- FrankenPHP Docs: <https://frankenphp.dev/>
- OrangeScrum V4: `../apps/orangescrum-v4/`

---

## Support

For issues:

1. Check `docker compose logs orangescrum-app`
2. Verify database connectivity
3. Review `.env` configuration
4. Ensure all required environment variables are set

```

### OrangeScrum V4 (.env in os-v4/)

```bash
DB_HOST=postgres16
DB_NAME=orangescrum
DB_USERNAME=orangescrum
DB_PASSWORD=orangescrumpass
REDIS_HOST=redis-durango
QUEUE_URL=redis://redis-durango:6379/0
```

### OrangeScrum V2 (.env in os-v2/)

```bash
DB_HOST=mysql
DB_NAME=orangescrum
DB_USERNAME=osuser
DB_PASSWORD=ospassword
MEMCACHED_HOST=memcached-orangescrum:11211

```txt
╔══════════════════════════════════════════════════╗
║     OrangeScrum Full Stack Deployment Menu       ║
╚══════════════════════════════════════════════════╝

1. Deploy full stack
2. Stop all services
3. Start all services
4. Restart all services
5. Manage individual service
6. View service logs
7. Check service status
8. Run pre-deployment checks
9. Exit

Select an option (1-9):
```

**Most common tasks:**

- First time? → Choose option **1** (Deploy full stack)
- Need to check status? → Choose option **7**
- Something wrong? → Choose option **6** to view logs
- Daily startup? → Choose option **3** (Start all services)
- End of day? → Choose option **2** (Stop all services)

---

## Common Operations

### Check Service Status

```bash
./deploy.sh --status
```

**Example output:**

```txt
┌─────────────────────────┬─────────┬──────────┬────────────────┐
│ Container               │ Status  │ Health   │ Ports          │
├─────────────────────────┼─────────┼──────────┼────────────────┤
│ orangescrum-app         │ running │ healthy  │ 80->80         │
│ orangescrum-postgresdb  │ running │ healthy  │ 5433->5432     │
│ orangescrum-storage     │ running │ healthy  │ 9000,9090      │
│ orangescrum-reports     │ running │ healthy  │ 8088->8088     │
│ orangescrum-os-optimize │ running │ healthy  │ 9091->9091     │
└─────────────────────────┴─────────┴──────────┴────────────────┘
```

### View Logs (Debug Problems)

```bash
# View logs for a specific service
./deploy.sh --logs orangescrum-app

# Follow logs in real-time (press Ctrl+C to stop)
./deploy.sh --logs orangescrum-app --follow
```

**Tip:** If something isn't working, check the logs first!

### Stop/Start/Restart Services

```bash
# Stop a specific service
./deploy.sh --stop-service orangescrum-app

# Start a specific service
./deploy.sh --start-service orangescrum-app

# Restart a specific service
./deploy.sh --restart-service orangescrum-app
```

### Stop Everything

```bash
# Stop all services
./deploy.sh --interactive
# Then choose option 2: Stop all services

# Or use command directly
docker compose -f orangescrum-cloud/docker-compose.yaml down
```

---

## Troubleshooting

### Problem: "Docker daemon is not accessible"

**What it means:** Docker isn't running.

**Fix:**

```bash
# Start Docker
sudo systemctl start docker

# Check status
sudo systemctl status docker

# Run checks again
./deploy.sh --check
```

---

### Problem: "Virtual environment not found"

**What it means:** You skipped the venv setup or deactivated it.

**Fix:**

```bash
# Create venv (if not exists)
python3 -m venv ../.venv

# Activate it
source ../.venv/bin/activate

# Install docker package
pip install docker

# Verify
python3 -c "import docker; print('Docker module installed')"
```

---

### Problem: "Port already in use"

**What it means:** Another service is using the same port.

**Example error:**

```txt
Error: Bind for 0.0.0.0:5432 failed: port is already allocated
```

**Good News:** The deploy script now automatically detects and handles port conflicts!

**Automatic Port Resolution (Default Behavior):**

The script will:

1. Check if ports are available before deployment
2. Automatically find alternative ports if blocked
3. Show you what ports are being used

```bash
# Deploy with automatic port resolution (default)
./deploy.sh

# Output will show:
# ⚠️  Some ports are already in use:
#    - APP_PORT: 8080
# Finding alternative ports...
#    ✓ APP_PORT: 8080 → 8081
```

**Manual Port Configuration:**

You can specify custom ports in three ways:

#### Option 1: Use .env file (Recommended)

```bash
cd orangescrum-cloud
cp .env.example .env
# Edit .env and set your custom ports:
# APP_PORT=3000
# PG_PORT=5434
# MINIO_API_PORT=9001
# etc...

./deploy.sh
```

#### Option 2: Command Line Arguments

```bash
./deploy.sh --app-port 3000 --pg-port 5434 --minio-port 9001 \
  --minio-console-port 9092 --reports-port 8089 --os-optimize-port 9093
```

#### Option 3: Let Script Auto-Resolve (Default)

Just run deployment - script finds available ports automatically!

**Disable Automatic Port Resolution:**

If you want the script to fail when ports are blocked (strict mode):

```bash
./deploy.sh --no-auto-port
```

**Check What's Using a Port:**

```bash
# Check what's using the port
sudo lsof -i :8080

# Or use netstat
netstat -tuln | grep 8080

# Kill process
sudo kill -9 <PID>
```

**Default Port Assignments:**

| Service | Default Port | Access URL |
|---------|-------------|------------|
| OrangeScrum App | 8080 | <http://localhost:8080> |

---

### Problem: Services won't start

**Symptoms:** Container status shows "exited" or "restarting"

**Fix:**

```bash
# Step 1: Check logs to see the error
./deploy.sh --logs orangescrum-app --follow

# Step 2: Common issues and fixes:

# If database connection error:
./deploy.sh --restart-service orangescrum-postgresdb
sleep 10
./deploy.sh --restart-service orangescrum-app

# If permission error:
docker exec orangescrum-app chown -R root:root /data
docker exec orangescrum-app chmod -R 755 /data

# If unknown error, try full restart:
./deploy.sh --interactive
# Choose option 4: Restart all services
```

---

### Problem: Pre-deployment checks fail

**What it means:** Something required for deployment is missing.

**Fix based on what's missing:**

```bash
# If "Docker daemon not running":
sudo systemctl start docker

# If "OS-Optimize image not found":
cd ../os-optimize
docker build -t orangescrum/os-optimize:latest .

# If "Repository not found":
cd ..
git clone <repository-url>

# If "FrankenPHP binary not found":
# Contact your team lead - binary needs to be built first
```

---

### Problem: "Can't access <http://localhost>"

**Symptoms:** Browser shows "Connection refused" or "This site can't be reached"

**Fix:**

```bash
# Step 1: Check if app is running
./deploy.sh --status

# Step 2: If app is running but can't access:
# The app might be bound to 192.168.2.132 only

# Option A: Access via IP
curl http://192.168.2.132

# Option B: Change binding in orangescrum-cloud/.env
# Set: APP_BIND_IP=127.0.0.1 (or 0.0.0.0)

# Step 3: Restart
./deploy.sh --restart-service orangescrum-app
```

---

### Problem: Need to start fresh

**When to use:** Everything is broken, want to reset completely.

**Nuclear option (deletes all data):**

```bash
# Stop and remove everything including volumes
docker compose -f orangescrum-cloud/docker-compose.yaml down -v

# Start fresh deployment
./deploy.sh
```

**WARNING:** This deletes all data, uploads, and databases!

---

## Installation Guide

### Install Docker (Ubuntu/Debian)

```bash
# Remove old versions
sudo apt-get remove docker docker-engine docker.io containerd runc

# Install Docker
curl -fsSL https://get.docker.com | sh

# Add your user to docker group (avoid sudo)
sudo usermod -aG docker $USER

# Log out and back in, then verify
docker --version
docker compose version
```

### Install Python & Git

```bash
# Install required packages
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv git

# Verify
python3 --version
git --version
```

---

## Available Services

| Service Name | Purpose | Default Port | Access |
|-------------|---------|--------------|--------|
| orangescrum-app | Main application | 8080 | <http://localhost:8080> |

---

## Daily Workflow

### Morning (Start Services)

```bash
cd durango-builder
source ../.venv/bin/activate
./deploy.sh --interactive
# Choose option 3: Start all services
```

### During Work (Check Status)

```bash
# Quick status check
./deploy.sh --status

# Watch logs while developing
./deploy.sh --logs orangescrum-app --follow
```

### Evening (Stop Services)

```bash
./deploy.sh --interactive
# Choose option 2: Stop all services
```

---

## Advanced Usage

### Custom Port Configuration

```bash
# Use custom ports
export APP_PORT=8080
export PG_PORT=5432
export MINIO_PORT=9000
export REPORTS_PORT=8088
export OS_OPTIMIZE_PORT=9091

./deploy.sh
```

### Skip Building Components

```bash
# Skip building OS-Optimize (use existing image)
./deploy.sh --skip-os-optimize

# Skip pre-deployment checks (not recommended)
./deploy.sh --skip-checks
```

### Build Without Deploying

```bash
# Only build images, don't start services
./deploy.sh --build-only
```

---

## Getting Help

### Show All Options

```bash
./deploy.sh --help
```

### Check What's Available

```bash
# List all running containers
docker ps

# List all containers (including stopped)
docker ps -a

# List all volumes
docker volume ls

# List all networks
docker network ls
```

### Ask for Help

When asking for help, provide:

1. **Output of checks:**

   ```bash
   ./deploy.sh --check
   ```

2. **Service status:**

   ```bash
   ./deploy.sh --status
   ```

3. **Relevant logs:**

   ```bash
   ./deploy.sh --logs <service-name> > error.log
   ```

---

## Additional Documentation

For advanced topics, see the `docs/` folder:

- **[Technical Architecture](docs/TECHNICAL_ARCHITECTURE.md)** - Deep dive into FrankenPHP, build system, and persistence
- **[Production Deployment](docs/PRODUCTION_DEPLOYMENT.md)** - Production server setup guide
- **[Database Testing](docs/DATABASE_TESTING.md)** - Database migration and testing
- **[Volume Safety](docs/VOLUME_SAFETY.md)** - Data persistence best practices
- **[Quick Reference](docs/QUICK_REFERENCE.md)** - Command cheat sheet

---

## Learning Resources

**New to Docker?**

- [Docker Getting Started](https://docs.docker.com/get-started/)
- [Docker Compose Tutorial](https://docs.docker.com/compose/gettingstarted/)

**New to Python?**

- [Python Virtual Environments Guide](https://docs.python.org/3/tutorial/venv.html)

**Understanding the Stack:**

- Read [Technical Architecture](docs/TECHNICAL_ARCHITECTURE.md) to learn how everything works

---

## Success Checklist

After deployment, verify:

- [ ] All services show "running" in `./deploy.sh --status`
- [ ] All services show "healthy" in status output
- [ ] Can access OrangeScrum at <http://192.168.2.132> or <http://localhost>
- [ ] Can access MinIO Console at <http://localhost:9090>
- [ ] No errors in logs: `./deploy.sh --logs orangescrum-app`

**If all checked, you're ready to go!**

---

## License

Enterprise Edition - Commercial License

---

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
