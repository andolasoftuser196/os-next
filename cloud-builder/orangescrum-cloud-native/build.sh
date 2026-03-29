#!/bin/bash
# Build Native Deployment Package
# This script assembles a production-ready Native binary deployment from common and Native-specific files
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILDER_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Load version and build config from single source of truth
source "$BUILDER_ROOT/lib/config.sh"
load_version
load_build_conf

COMMON_DIR="$BUILDER_ROOT/orangescrum-cloud-common"
NATIVE_SOURCE="$SCRIPT_DIR"
OUTPUT_DIR="${DIST_NATIVE_DIR:-$BUILDER_ROOT/dist-native}"
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

# Copy shared library
mkdir -p "$OUTPUT_DIR/lib"
cp "$BUILDER_ROOT/lib/frankenphp-common.sh" "$OUTPUT_DIR/lib/"
echo "  [OK] lib/frankenphp-common.sh"

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

    # Symlink for backward compatibility (saves ~340MB vs full copy)
    ln -sf orangescrum "$OUTPUT_DIR/bin/osv4-prod"
    echo "  [OK] bin/osv4-prod -> orangescrum (symlink)"
else
    echo ""
    echo "[WARNING]  Skipping binary copy (not found)"
    mkdir -p "$OUTPUT_DIR/bin"
fi

# Copy QUICKSTART.md as README
echo ""
echo "Creating README.md..."
cp "$COMMON_DIR/docs/QUICKSTART.md" "$OUTPUT_DIR/README.md"
echo "  [OK] README.md (from QUICKSTART.md)"

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
