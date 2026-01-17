#!/bin/bash
# Package Docker deployment for production distribution
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VERSION="${VERSION:-v26.1.1}"
# Use exported timestamp if available, otherwise create new one
TIMESTAMP="${TIMESTAMP:-$(date +%Y%m%d_%H%M%S)}"
DIST_DIR="../dist/${TIMESTAMP}"
PACKAGE_NAME="orangescrum-docker-${VERSION}-${TIMESTAMP}"
SOURCE_DIR="../orangescrum-cloud-docker"

echo "=========================================="
echo "Package Docker Deployment for Distribution"
echo "=========================================="
echo "Version: $VERSION"
echo "Timestamp: $TIMESTAMP"
echo ""

# Check if source exists
if [ ! -d "$SOURCE_DIR" ]; then
    echo "[ERROR] Error: $SOURCE_DIR not found"
    echo "   Run: ./build-docker.sh first"
    exit 1
fi

# Check if binary exists
if [ ! -f "$SOURCE_DIR/orangescrum-app/osv4-prod" ]; then
    echo "[ERROR] Error: Binary not found in $SOURCE_DIR/orangescrum-app/osv4-prod"
    echo "   Run: cd .. && python build.py"
    exit 1
fi

# Create dist directory
echo "Creating distribution directory..."
mkdir -p "$DIST_DIR"

# Create package directory
PACKAGE_DIR="$DIST_DIR/$PACKAGE_NAME"
mkdir -p "$PACKAGE_DIR"

echo "Packaging Docker deployment..."

# Copy all files from docker deployment
echo "  [OK] Copying deployment files"
cp -r "$SOURCE_DIR"/* "$PACKAGE_DIR/"

# Create deployment instructions
cat > "$PACKAGE_DIR/DEPLOYMENT_INSTRUCTIONS.md" << 'EOF'
# OrangeScrum Docker Deployment Package

## Quick Start

### 1. Extract Package

```bash
tar -xzf orangescrum-docker-*.tar.gz
cd orangescrum-docker-*
```

### 2. Configure Environment

```bash
# Copy and edit environment file
cp .env.example .env
nano .env

# Required settings:
# - DB_HOST, DB_USERNAME, DB_PASSWORD, DB_NAME
# - SECURITY_SALT (generate with: openssl rand -base64 32)
# - FULL_BASE_URL
```

### 3. Start Infrastructure Services

```bash
# Start PostgreSQL, Redis, MinIO, MailHog
docker-compose -f docker-compose.services.yml up -d

# Verify services
docker-compose -f docker-compose.services.yml ps
```

### 4. Deploy Application

```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f orangescrum-app

# Check health
docker-compose ps
```

### 5. Access Application

```
http://localhost:8080
```

## Production Deployment

See `docs/PRODUCTION_DEPLOYMENT_DOCKER.md` for:
- SSL/TLS configuration
- Reverse proxy setup
- External database configuration
- Monitoring and backups
- Security hardening

## Package Contents

- `Dockerfile` - Container image definition
- `docker-compose.yaml` - Application orchestration
- `docker-compose.services.yml` - Infrastructure services
- `entrypoint.sh` - Container startup script
- `config/` - Configuration templates
- `docs/` - Full documentation
- `orangescrum-app/osv4-prod` - FrankenPHP binary (372MB)

## Support

- Configuration: See `CONFIGS.md`
- Production setup: See `docs/PRODUCTION_DEPLOYMENT_DOCKER.md`
- Validation: Run `./validate-env.sh`

## Package Information

- Type: Docker Deployment
- Build Date: $(date)
- Version: $VERSION
EOF

# Create archive
echo ""
echo "Creating tarball..."
cd "$DIST_DIR"
tar -czf "${PACKAGE_NAME}.tar.gz" "$PACKAGE_NAME"

# Calculate size and checksum
SIZE=$(du -h "${PACKAGE_NAME}.tar.gz" | cut -f1)
CHECKSUM=$(sha256sum "${PACKAGE_NAME}.tar.gz" | cut -d' ' -f1)

# Create manifest
cat > "${PACKAGE_NAME}.manifest.txt" << MANIFEST
OrangeScrum Docker Deployment Package
=====================================

Package: ${PACKAGE_NAME}.tar.gz
Type: Docker Deployment
Version: $VERSION
Build Date: $(date)
Build Timestamp: $TIMESTAMP

Package Details
--------------
Size: $SIZE
SHA256: $CHECKSUM

Contents
--------
- FrankenPHP static binary (osv4-prod)
- Docker Compose configuration
- Infrastructure services (PostgreSQL, Redis, MinIO, MailHog)
- Configuration templates
- Complete documentation

Deployment
----------
1. Extract: tar -xzf ${PACKAGE_NAME}.tar.gz
2. Configure: cd ${PACKAGE_NAME} && cp .env.example .env && nano .env
3. Deploy: docker-compose -f docker-compose.services.yml up -d && docker-compose up -d

Documentation
-------------
See DEPLOYMENT_INSTRUCTIONS.md in the package
See docs/PRODUCTION_DEPLOYMENT_DOCKER.md for production setup
MANIFEST

# Cleanup temporary directory
rm -rf "$PACKAGE_NAME"

echo ""
echo "=========================================="
echo "[OK] Docker package created successfully!"
echo "=========================================="
echo ""
echo "Location: $DIST_DIR/"
echo "Package: ${PACKAGE_NAME}.tar.gz"
echo "Size: $SIZE"
echo "SHA256: $CHECKSUM"
echo ""
echo "Files created:"
echo "  - ${PACKAGE_NAME}.tar.gz"
echo "  - ${PACKAGE_NAME}.manifest.txt"
echo ""
