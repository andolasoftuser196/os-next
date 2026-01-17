#!/bin/bash
# Build Docker Deployment Package
# This script assembles a production-ready Docker deployment from common and Docker-specific files
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILDER_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
COMMON_DIR="$BUILDER_ROOT/orangescrum-cloud-common"
DOCKER_SOURCE="$SCRIPT_DIR"
OUTPUT_DIR="${DIST_DOCKER_DIR:-$BUILDER_ROOT/dist-docker}"
VERSION="${VERSION:-v26.1.1}"
TIMESTAMP="${BUILD_TIMESTAMP:-$(date +%Y%m%d_%H%M%S)}"

echo "=========================================="
echo "Building Docker Deployment Package"
echo "=========================================="
echo "Version: $VERSION"
echo "Timestamp: $TIMESTAMP"
echo "Output: $OUTPUT_DIR"
echo ""

# Validate common files exist
if [ ! -d "$COMMON_DIR" ]; then
    echo "[ERROR] Error: Common files not found at $COMMON_DIR"
    echo "   Expected: orangescrum-cloud-common/"
    exit 1
fi

# Check for binary
BINARY="$COMMON_DIR/orangescrum-app/osv4-prod"
if [ ! -f "$BINARY" ]; then
    echo "[WARNING]  Warning: FrankenPHP binary not found at $BINARY"
    echo "   Run: cd $BUILDER_ROOT && python build.py"
    echo "   Continuing without binary (will need to be added later)..."
    BINARY_EXISTS=false
else
    BINARY_EXISTS=true
    BINARY_SIZE=$(du -h "$BINARY" | cut -f1)
    echo "[OK] Binary found: $BINARY ($BINARY_SIZE)"
fi

# Create output directory
echo ""
echo "Creating output directory..."
mkdir -p "$OUTPUT_DIR"
rm -rf "$OUTPUT_DIR"/*
echo "  [OK] $OUTPUT_DIR"

# Copy Docker-specific files
echo ""
echo "Copying Docker-specific files..."
cp "$DOCKER_SOURCE/Dockerfile" "$OUTPUT_DIR/"
echo "  [OK] Dockerfile"

cp "$DOCKER_SOURCE/docker-compose.yaml" "$OUTPUT_DIR/"
echo "  [OK] docker-compose.yaml"

cp "$DOCKER_SOURCE/docker-compose.services.yml" "$OUTPUT_DIR/"
echo "  [OK] docker-compose.services.yml"

cp "$DOCKER_SOURCE/entrypoint.sh" "$OUTPUT_DIR/"
chmod +x "$OUTPUT_DIR/entrypoint.sh"
echo "  [OK] entrypoint.sh"

if [ -f "$DOCKER_SOURCE/.dockerignore" ]; then
    cp "$DOCKER_SOURCE/.dockerignore" "$OUTPUT_DIR/"
    echo "  [OK] .dockerignore"
fi

cp "$DOCKER_SOURCE/.env.example" "$OUTPUT_DIR/"
echo "  [OK] .env.example"

# Copy common files
echo ""
echo "Copying common files..."

cp -r "$COMMON_DIR/config" "$OUTPUT_DIR/"
echo "  [OK] config/"

cp -r "$COMMON_DIR/docs" "$OUTPUT_DIR/"
echo "  [OK] docs/"

mkdir -p "$OUTPUT_DIR/helpers"
cp "$COMMON_DIR/helpers"/*.sh "$OUTPUT_DIR/helpers/"
chmod +x "$OUTPUT_DIR/helpers"/*.sh
echo "  [OK] helpers/"

cp "$COMMON_DIR/CONFIGS.md" "$OUTPUT_DIR/"
echo "  [OK] CONFIGS.md"

# Copy binary if it exists
if [ "$BINARY_EXISTS" = true ]; then
    echo ""
    echo "Copying FrankenPHP binary..."
    mkdir -p "$OUTPUT_DIR/orangescrum-app"
    cp "$BINARY" "$OUTPUT_DIR/orangescrum-app/"
    chmod +x "$OUTPUT_DIR/orangescrum-app/osv4-prod"
    echo "  [OK] osv4-prod ($BINARY_SIZE)"
else
    echo ""
    echo "[WARNING]  Skipping binary copy (not found)"
    mkdir -p "$OUTPUT_DIR/orangescrum-app"
fi

# Create Docker-specific README
echo ""
echo "Creating README.md..."
cat > "$OUTPUT_DIR/README.md" << 'DOCKERREADME'
# OrangeScrum FrankenPHP - Docker Deployment

**Deployment Type:** Docker with Docker Compose  
**FrankenPHP:** Static binary with embedded CakePHP 4 application  
**Infrastructure:** External PostgreSQL, Redis, and S3

---

## Quick Start

### 1. Configure Environment

```bash
cp .env.example .env
nano .env
```

**Required Settings:**
```bash
# Database (external PostgreSQL)
DB_HOST=your-postgres-server.example.com
DB_USERNAME=orangescrum
DB_PASSWORD=<generate-strong-password>
DB_NAME=orangescrum

# Redis (external)
REDIS_HOST=your-redis-server.example.com
REDIS_PORT=6379

# S3 Storage
STORAGE_ENDPOINT=https://s3.amazonaws.com
STORAGE_ACCESS_KEY=<your-access-key>
STORAGE_SECRET_KEY=<your-secret-key>
STORAGE_BUCKET=<your-bucket-name>

# Security
SECURITY_SALT=<generate-with: openssl rand -base64 32>

# Application
DEBUG=false
FULL_BASE_URL=https://your-domain.com
```

### 2. Validate Configuration

```bash
./helpers/validate-env.sh
```

### 3. Deploy Application

```bash
# Start main application
docker compose up -d orangescrum-app

# Optional: Start queue worker
docker compose --profile queue up -d queue-worker

# Check status
docker compose ps

# View logs
docker compose logs -f orangescrum-app
```

### 4. Access Application

Default port: http://localhost:8080

For production, configure a reverse proxy (nginx/Apache) with SSL.

---

## Production Deployment

See [docs/PRODUCTION_DEPLOYMENT_DOCKER.md](docs/PRODUCTION_DEPLOYMENT_DOCKER.md) for complete production setup guide including:

- Reverse proxy configuration (nginx/Apache)
- SSL certificate setup (Let's Encrypt)
- Firewall configuration
- Monitoring and backup setup
- Performance tuning

---

## Available Services

### Main Application
```bash
docker compose up -d orangescrum-app
```

### Queue Worker (Optional)
```bash
docker compose --profile queue up -d queue-worker
```

### Infrastructure (Development/Testing)
```bash
# PostgreSQL, Redis, MinIO, MailHog
docker compose -f docker-compose.services.yml up -d
```

---

## Useful Commands

```bash
# View logs
docker compose logs -f orangescrum-app
docker compose logs -f queue-worker

# Restart application
docker compose restart orangescrum-app

# Stop all services
docker compose down

# Run CakePHP commands
docker compose exec orangescrum-app /orangescrum-app/osv4-prod php-cli bin/cake.php migrations status

# Access container shell
docker compose exec orangescrum-app sh
```

---

## Directory Structure

```
.
+-- docker-compose.yaml          # Main application services
+-- docker-compose.services.yml  # Infrastructure services (dev/test)
+-- Dockerfile                   # Container image definition
+-- entrypoint.sh                # Container startup script
+-- .env.example                 # Environment template
+-- config/                      # Configuration file templates
+-- docs/                        # Documentation
+-- helpers/                     # Helper scripts
|   +-- cake.sh                  # CakePHP CLI wrapper
|   +-- queue-worker.sh          # Queue worker wrapper
|   +-- validate-env.sh          # Environment validator
+-- orangescrum-app/
    +-- osv4-prod                # FrankenPHP static binary
```

---

## Support

For issues and questions, see [docs/](docs/) directory for comprehensive documentation.

DOCKERREADME

echo "  [OK] README.md"

# Create manifest
echo ""
echo "Creating build manifest..."
cat > "$OUTPUT_DIR/.build-manifest.txt" << EOF
Build Manifest
==============
Type: Docker Deployment
Version: $VERSION
Timestamp: $TIMESTAMP
Built: $(date)
Binary: $([ "$BINARY_EXISTS" = true ] && echo "Included ($BINARY_SIZE)" || echo "Not included")
Builder: $(whoami)@$(hostname)

Files Included:
- Docker: Dockerfile, docker-compose.yaml, docker-compose.services.yml, entrypoint.sh
- Common: config/, docs/, helpers/, CONFIGS.md
- Binary: orangescrum-app/osv4-prod (if built)
- Environment: .env.example

Next Steps:
1. Copy this folder to your Docker host
2. Configure .env file
3. Run: ./helpers/validate-env.sh
4. Deploy: docker compose up -d

For production deployment, see: docs/PRODUCTION_DEPLOYMENT_DOCKER.md
EOF

echo "  [OK] .build-manifest.txt"

echo ""
echo "=========================================="
echo "Docker Deployment Package Built"
echo "=========================================="
echo "Location: $OUTPUT_DIR"
echo ""
ls -lh "$OUTPUT_DIR" | tail -n +2 | awk '{print "  " $9}'
echo ""
echo "Next steps:"
echo "  1. Test the package: cd $OUTPUT_DIR"
echo "  2. Configure .env:   cp .env.example .env && nano .env"
echo "  3. Validate config:  ./helpers/validate-env.sh"
echo "  4. Deploy:           docker compose up -d"
echo ""
