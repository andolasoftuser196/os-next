#!/bin/bash
# Build Docker Deployment Package
# This script assembles a production-ready Docker deployment from common and Docker-specific files
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILDER_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Load version and build config from single source of truth
source "$BUILDER_ROOT/lib/config.sh"
load_version
load_build_conf

COMMON_DIR="$BUILDER_ROOT/orangescrum-cloud-common"
DOCKER_SOURCE="$SCRIPT_DIR"
OUTPUT_DIR="${DIST_DOCKER_DIR:-$BUILDER_ROOT/dist-docker}"
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

# Copy shared library
mkdir -p "$OUTPUT_DIR/lib"
cp "$BUILDER_ROOT/lib/frankenphp-common.sh" "$OUTPUT_DIR/lib/"
echo "  [OK] lib/frankenphp-common.sh"

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
