#!/bin/bash
# Build Native Deployment Package
# This script assembles a production-ready Native binary deployment from common and Native-specific files
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILDER_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
COMMON_DIR="$BUILDER_ROOT/orangescrum-cloud-common"
NATIVE_SOURCE="$SCRIPT_DIR"
OUTPUT_DIR="${DIST_NATIVE_DIR:-$BUILDER_ROOT/dist-native}"
VERSION="${VERSION:-v26.1.1}"
TIMESTAMP="${BUILD_TIMESTAMP:-$(date +%Y%m%d_%H%M%S)}"

echo "=========================================="
echo "Building Native Deployment Package"
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

# Copy Native-specific files
echo ""
echo "Copying Native-specific files..."
cp "$NATIVE_SOURCE/run.sh" "$OUTPUT_DIR/"
chmod +x "$OUTPUT_DIR/run.sh"
echo "  [OK] run.sh"

cp "$NATIVE_SOURCE/package.sh" "$OUTPUT_DIR/"
chmod +x "$OUTPUT_DIR/package.sh"
echo "  [OK] package.sh"

if [ -f "$NATIVE_SOURCE/caddy.sh" ]; then
    cp "$NATIVE_SOURCE/caddy.sh" "$OUTPUT_DIR/"
    chmod +x "$OUTPUT_DIR/caddy.sh"
    echo "  [OK] caddy.sh"
fi

cp "$NATIVE_SOURCE/.env.example" "$OUTPUT_DIR/"
echo "  [OK] .env.example"

# Copy systemd service files if they exist
if [ -d "$NATIVE_SOURCE/systemd" ]; then
    cp -r "$NATIVE_SOURCE/systemd" "$OUTPUT_DIR/"
    echo "  [OK] systemd/"
fi

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
    mkdir -p "$OUTPUT_DIR/bin"
    cp "$BINARY" "$OUTPUT_DIR/bin/orangescrum"
    chmod +x "$OUTPUT_DIR/bin/orangescrum"
    echo "  [OK] bin/orangescrum ($BINARY_SIZE)"
    
    # Also copy as osv4-prod for compatibility
    cp "$BINARY" "$OUTPUT_DIR/bin/osv4-prod"
    chmod +x "$OUTPUT_DIR/bin/osv4-prod"
    echo "  [OK] bin/osv4-prod (symlink for compatibility)"
else
    echo ""
    echo "[WARNING]  Skipping binary copy (not found)"
    mkdir -p "$OUTPUT_DIR/bin"
fi

# Create Native-specific README
echo ""
echo "Creating README.md..."
cat > "$OUTPUT_DIR/README.md" << 'NATIVEREADME'
# OrangeScrum FrankenPHP - Native Binary Deployment

**Deployment Type:** Native FrankenPHP binary (no Docker)  
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
PORT=8080
```

### 2. Validate Configuration

```bash
./helpers/validate-env.sh
```

### 3. Run Application

**Development/Testing:**
```bash
./run.sh
```

**Production (systemd service):**
```bash
# Install service
sudo cp systemd/orangescrum.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable orangescrum
sudo systemctl start orangescrum

# Check status
sudo systemctl status orangescrum

# View logs
sudo journalctl -u orangescrum -f
```

### 4. Access Application

Default port: http://localhost:8080

For production, configure a reverse proxy (nginx/Apache) with SSL.

---

## Production Deployment

See [docs/PRODUCTION_DEPLOYMENT_NATIVE.md](docs/PRODUCTION_DEPLOYMENT_NATIVE.md) for complete production setup guide including:

- systemd service configuration
- Reverse proxy setup (nginx/Apache)
- SSL certificate configuration
- Queue worker setup
- Cron job configuration
- Log rotation
- Backup automation

---

## Running Components

### Main Application
```bash
# Direct execution
./bin/orangescrum php-server -r webroot -l 0.0.0.0:8080

# Using wrapper script
./run.sh

# systemd service
sudo systemctl start orangescrum
```

### Queue Worker
```bash
# Direct execution
./bin/orangescrum php-cli bin/cake.php queue worker --verbose

# Using wrapper script
./helpers/queue-worker.sh

# systemd service (if configured)
sudo systemctl start orangescrum-queue
```

### CakePHP Commands
```bash
# Using wrapper script
./helpers/cake.sh migrations status
./helpers/cake.sh cache clear_all

# Direct execution
./bin/orangescrum php-cli bin/cake.php migrations status
```

---

## Directory Structure

```
.
+-- bin/
|   +-- orangescrum              # FrankenPHP binary (main)
|   +-- osv4-prod                # Compatibility symlink
+-- run.sh                       # Start application
+-- package.sh                   # Package for distribution
+-- .env.example                 # Environment template
+-- config/                      # Configuration file templates
+-- docs/                        # Documentation
+-- helpers/                     # Helper scripts
|   +-- cake.sh                  # CakePHP CLI wrapper
|   +-- queue-worker.sh          # Queue worker wrapper
|   +-- validate-env.sh          # Environment validator
+-- systemd/                     # systemd service files
    +-- orangescrum.service
    +-- orangescrum-queue.service
```

---

## Deployment Checklist

- [ ] Extract package to `/opt/orangescrum`
- [ ] Create `.env` from `.env.example`
- [ ] Configure all required environment variables
- [ ] Run `./helpers/validate-env.sh`
- [ ] Set up PostgreSQL database
- [ ] Set up Redis cache
- [ ] Configure S3 bucket
- [ ] Install systemd services
- [ ] Configure nginx/Apache reverse proxy
- [ ] Set up SSL certificate (Let's Encrypt)
- [ ] Configure cron jobs for recurring tasks
- [ ] Set up log rotation
- [ ] Configure monitoring and backups

---

## Support

For issues and questions, see [docs/](docs/) directory for comprehensive documentation.

NATIVEREADME

echo "  [OK] README.md"

# Create manifest
echo ""
echo "Creating build manifest..."
cat > "$OUTPUT_DIR/.build-manifest.txt" << EOF
Build Manifest
==============
Type: Native Binary Deployment
Version: $VERSION
Timestamp: $TIMESTAMP
Built: $(date)
Binary: $([ "$BINARY_EXISTS" = true ] && echo "Included ($BINARY_SIZE)" || echo "Not included")
Builder: $(whoami)@$(hostname)

Files Included:
- Native: run.sh, package.sh, systemd/
- Common: config/, docs/, helpers/, CONFIGS.md
- Binary: bin/orangescrum (if built)
- Environment: .env.example

Next Steps:
1. Copy this folder to your server (e.g., /opt/orangescrum)
2. Configure .env file
3. Run: ./helpers/validate-env.sh
4. Deploy: ./run.sh (or install systemd service)

For production deployment, see: docs/PRODUCTION_DEPLOYMENT_NATIVE.md
EOF

echo "  [OK] .build-manifest.txt"

echo ""
echo "=========================================="
echo "Native Deployment Package Built"
echo "=========================================="
echo "Location: $OUTPUT_DIR"
echo ""
ls -lh "$OUTPUT_DIR" | tail -n +2 | awk '{print "  " $9}'
echo ""
echo "Next steps:"
echo "  1. Test the package: cd $OUTPUT_DIR"
echo "  2. Configure .env:   cp .env.example .env && nano .env"
echo "  3. Validate config:  ./helpers/validate-env.sh"
echo "  4. Deploy:           ./run.sh (or install systemd service)"
echo ""
