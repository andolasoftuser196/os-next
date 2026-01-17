#!/bin/bash
# Package Native deployment for production distribution
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VERSION="${VERSION:-v26.1.1}"
# Use exported timestamp if available, otherwise create new one
TIMESTAMP="${TIMESTAMP:-$(date +%Y%m%d_%H%M%S)}"
DIST_DIR="../dist/${TIMESTAMP}"
PACKAGE_NAME="orangescrum-native-${VERSION}-${TIMESTAMP}"
SOURCE_DIR="../orangescrum-cloud-native"
# Binary name configuration (default: orangescrum, but can be osv4-prod for prod compatibility)
BINARY_NAME="${BINARY_NAME:-orangescrum}"
SOURCE_BINARY_NAME="osv4-prod"

echo "=========================================="
echo "Package Native Deployment for Distribution"
echo "=========================================="
echo "Version: $VERSION"
echo "Timestamp: $TIMESTAMP"
echo ""

# Check if source exists
if [ ! -d "$SOURCE_DIR" ]; then
    echo "❌ Error: $SOURCE_DIR not found"
    echo "   Run: ./build-native.sh first"
    exit 1
fi

# Check if binary exists
if [ ! -f "$SOURCE_DIR/orangescrum-app/$SOURCE_BINARY_NAME" ]; then
    echo "❌ Error: Binary not found in $SOURCE_DIR/orangescrum-app/$SOURCE_BINARY_NAME"
    echo "   Run: cd .. && python build.py"
    exit 1
fi

# Create dist directory
echo "Creating distribution directory..."
mkdir -p "$DIST_DIR"

# Create package directory
PACKAGE_DIR="$DIST_DIR/$PACKAGE_NAME"
mkdir -p "$PACKAGE_DIR"

echo "Packaging Native deployment..."

# Copy all files from native deployment
echo "  ✓ Copying deployment files"
cp -r "$SOURCE_DIR"/* "$PACKAGE_DIR/"

# Rename binary if needed
if [ "$BINARY_NAME" != "$SOURCE_BINARY_NAME" ]; then
    echo "  ✓ Renaming binary from '$SOURCE_BINARY_NAME' to '$BINARY_NAME'"
    mv "$PACKAGE_DIR/orangescrum-app/$SOURCE_BINARY_NAME" "$PACKAGE_DIR/orangescrum-app/$BINARY_NAME"
    chmod +x "$PACKAGE_DIR/orangescrum-app/$BINARY_NAME"
    
    # Update run scripts to use new binary name
    sed -i "s|orangescrum-app/$SOURCE_BINARY_NAME|orangescrum-app/$BINARY_NAME|g" "$PACKAGE_DIR/run-native.sh" 2>/dev/null || \
        sed -i '' "s|orangescrum-app/$SOURCE_BINARY_NAME|orangescrum-app/$BINARY_NAME|g" "$PACKAGE_DIR/run-native.sh"
    
    sed -i "s|orangescrum-app/$SOURCE_BINARY_NAME|orangescrum-app/$BINARY_NAME|g" "$PACKAGE_DIR/run.sh" 2>/dev/null || \
        sed -i '' "s|orangescrum-app/$SOURCE_BINARY_NAME|orangescrum-app/$BINARY_NAME|g" "$PACKAGE_DIR/run.sh"
else
    echo "  ✓ Keeping binary name as '$SOURCE_BINARY_NAME'"
    chmod +x "$PACKAGE_DIR/orangescrum-app/$BINARY_NAME"
fi

# Create deployment instructions
cat > "$PACKAGE_DIR/DEPLOYMENT_INSTRUCTIONS.md" << 'EOF'
# OrangeScrum Native Deployment Package

## Quick Start

### 1. Extract Package

```bash
tar -xzf orangescrum-native-*.tar.gz
cd orangescrum-native-*
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
# - External PostgreSQL, Redis, S3 connection details
```

### 3. Validate Configuration

```bash
./validate-env.sh
```

### 4. Run Application

```bash
# Development (foreground)
./run-native.sh

# Production (background daemon)
DAEMON=true ./run-native.sh &
```

### 5. Access Application

```
http://localhost:8080
```

## Production Deployment

### Install to System

```bash
# Create deployment directory
sudo mkdir -p /opt/orangescrum
sudo cp -r . /opt/orangescrum/
sudo chown -R orangescrum:orangescrum /opt/orangescrum

# Configure environment
cd /opt/orangescrum
sudo -u orangescrum nano .env
```

### Set Up Systemd Service

Create `/etc/systemd/system/orangescrum.service`:

```ini
[Unit]
Description=OrangeScrum FrankenPHP Application
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=orangescrum
Group=orangescrum
WorkingDirectory=/opt/orangescrum
EnvironmentFile=/opt/orangescrum/.env
ExecStart=/opt/orangescrum/orangescrum-app/orangescrum php-server --listen :8080
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable orangescrum
sudo systemctl start orangescrum
sudo systemctl status orangescrum
```

### Set Up Reverse Proxy

See `docs/PRODUCTION_DEPLOYMENT_NATIVE.md` for:
- Nginx/Caddy reverse proxy configuration
- SSL/TLS setup with Let's Encrypt
- Firewall configuration
- Queue worker setup
- Cron jobs for recurring tasks

## Package Contents

- \`orangescrum-app/$BINARY_NAME\` - FrankenPHP static binary (372MB)
- \`run-native.sh\` - Application runner
- \`config/\` - Configuration templates
- \`docs/\` - Full documentation
- Helper scripts: \`cake.sh\`, \`queue-worker.sh\`, \`validate-env.sh\`

## Support

- Configuration: See `CONFIGS.md`
- Production setup: See `docs/PRODUCTION_DEPLOYMENT_NATIVE.md`
- Validation: Run `./validate-env.sh`

## Package Information

- Type: Native Deployment
- Build Date: $(date)
- Version: $VERSION
- Binary: Self-contained FrankenPHP with PHP 8.3
EOF

# Create systemd service template
cat > "$PACKAGE_DIR/orangescrum.service" << EOF
[Unit]
Description=OrangeScrum FrankenPHP Application
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=orangescrum
Group=orangescrum
WorkingDirectory=/opt/orangescrum
EnvironmentFile=/opt/orangescrum/.env
ExecStart=/opt/orangescrum/orangescrum-app/$BINARY_NAME php-server --listen :8080
Restart=always
RestartSec=10

# Security
NoNewPrivileges=true
PrivateTmp=true

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=orangescrum

[Install]
WantedBy=multi-user.target
EOF

# Create queue worker service
cat > "$PACKAGE_DIR/orangescrum-queue.service" << 'EOF'
[Unit]
Description=OrangeScrum Queue Worker
After=network.target postgresql.service redis.service orangescrum.service

[Service]
Type=simple
User=orangescrum
Group=orangescrum
WorkingDirectory=/opt/orangescrum
EnvironmentFile=/opt/orangescrum/.env
ExecStart=/opt/orangescrum/queue-worker.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
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
OrangeScrum Native Deployment Package
=====================================

Package: ${PACKAGE_NAME}.tar.gz
Type: Native Deployment (Direct System Execution)
Version: $VERSION
Build Date: $(date)
Build Timestamp: $TIMESTAMP

Package Details
--------------
Size: $SIZE
SHA256: $CHECKSUM

Contents
--------
- FrankenPHP static binary ($BINARY_NAME)
- Native runner scripts
- Configuration templates
- Systemd service files
- Complete documentation

System Requirements
------------------
- Linux x86_64 (Ubuntu, Debian, CentOS, etc.)
- PostgreSQL client (psql)
- External PostgreSQL 12+, Redis, S3-compatible storage

Deployment
----------
1. Extract: tar -xzf ${PACKAGE_NAME}.tar.gz
2. Configure: cd ${PACKAGE_NAME} && cp .env.example .env && nano .env
3. Validate: ./validate-env.sh
4. Run: ./run-native.sh

Production Installation
----------------------
1. Extract to /opt/orangescrum
2. Configure .env
3. Install systemd service: sudo cp orangescrum.service /etc/systemd/system/
4. Enable and start: sudo systemctl enable orangescrum && sudo systemctl start orangescrum

Documentation
-------------
See DEPLOYMENT_INSTRUCTIONS.md in the package
See docs/PRODUCTION_DEPLOYMENT_NATIVE.md for production setup
MANIFEST

# Cleanup temporary directory
rm -rf "$PACKAGE_NAME"

echo ""
echo "=========================================="
echo "✓ Native package created successfully!"
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
