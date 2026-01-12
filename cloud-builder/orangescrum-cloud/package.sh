#!/bin/bash
# Package OrangeScrum FrankenPHP for deployment
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PACKAGE_NAME="orangescrum-frankenphp"
VERSION="${VERSION:-v26.1.1}"
PACKAGE_DIR="${PACKAGE_NAME}-${VERSION}"
OUTPUT_FILE="${PACKAGE_NAME}-${VERSION}.tar.gz"
BINARY="./orangescrum-app/osv4-prod"

echo "=========================================="
echo "OrangeScrum FrankenPHP Package Builder"
echo "=========================================="
echo "Package: $OUTPUT_FILE"
echo ""

# Check binary
if [ ! -f "$BINARY" ]; then
    echo "❌ Binary not found: $BINARY"
    echo "   Run: cd ../durango-builder && python build.py --skip-deploy"
    exit 1
fi

# Create package
echo "Creating package..."
rm -rf "$PACKAGE_DIR"
mkdir -p "$PACKAGE_DIR"/{bin,config}

# Copy binary
echo "  ✓ Copying FrankenPHP binary"
cp "$BINARY" "$PACKAGE_DIR/bin/orangescrum"
chmod +x "$PACKAGE_DIR/bin/orangescrum"

# Copy configuration files
echo "  ✓ Copying configuration files"
if [ -d "./config" ]; then
    cp -r ./config/* "$PACKAGE_DIR/config/"
fi

# Copy scripts and docs
echo "  ✓ Copying scripts and documentation"
cp run-native.sh "$PACKAGE_DIR/run.sh"
chmod +x "$PACKAGE_DIR/run.sh"

if [ -f "cake.sh" ]; then
    cp cake.sh "$PACKAGE_DIR/cake.sh"
    chmod +x "$PACKAGE_DIR/cake.sh"
fi

if [ -f "queue-worker.sh" ]; then
    cp queue-worker.sh "$PACKAGE_DIR/queue-worker.sh"
    chmod +x "$PACKAGE_DIR/queue-worker.sh"
fi

if [ -f ".env.example" ]; then
    cp .env.example "$PACKAGE_DIR/.env.example"
fi

if [ -f "DEPLOYMENT.md" ]; then
    cp DEPLOYMENT.md "$PACKAGE_DIR/"
fi

if [ -f "ENVIRONMENT_CONFIGURATION.md" ]; then
    cp ENVIRONMENT_CONFIGURATION.md "$PACKAGE_DIR/"
fi

if [ -f "README.md" ]; then
    cp README.md "$PACKAGE_DIR/"
fi

# Archive
echo ""
echo "Creating tarball..."
tar -czf "$OUTPUT_FILE" "$PACKAGE_DIR"

# Calculate size and checksum
SIZE=$(du -h "$OUTPUT_FILE" | cut -f1)
CHECKSUM=$(sha256sum "$OUTPUT_FILE" | cut -d' ' -f1)

# Cleanup
rm -rf "$PACKAGE_DIR"

echo ""
echo "=========================================="
echo "✓ Package created successfully!"
echo "=========================================="
echo ""
echo "Package: $OUTPUT_FILE"
echo "Size: $SIZE"
echo "SHA256: $CHECKSUM"
echo ""
