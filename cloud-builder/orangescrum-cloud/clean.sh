#!/bin/bash
# Clean/Reset auto-generated deployment folders
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

DOCKER_DIR="../orangescrum-cloud-docker"
NATIVE_DIR="../orangescrum-cloud-native"

echo "=========================================="
echo "Clean Auto-Generated Deployment Folders"
echo "=========================================="
echo ""

# Check what will be removed
if [ -d "$DOCKER_DIR" ]; then
    echo "Will remove: $DOCKER_DIR"
    DOCKER_EXISTS=true
else
    echo "Not found: $DOCKER_DIR (already clean)"
    DOCKER_EXISTS=false
fi

if [ -d "$NATIVE_DIR" ]; then
    echo "Will remove: $NATIVE_DIR"
    NATIVE_EXISTS=true
else
    echo "Not found: $NATIVE_DIR (already clean)"
    NATIVE_EXISTS=false
fi

if [ "$DOCKER_EXISTS" = false ] && [ "$NATIVE_EXISTS" = false ]; then
    echo ""
    echo "[OK] Nothing to clean - deployment folders don't exist"
    exit 0
fi

echo ""
read -p "Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled"
    exit 0
fi

# Remove folders
if [ "$DOCKER_EXISTS" = true ]; then
    echo "Removing $DOCKER_DIR..."
    rm -rf "$DOCKER_DIR"
    echo "  [OK] Removed"
fi

if [ "$NATIVE_EXISTS" = true ]; then
    echo "Removing $NATIVE_DIR..."
    rm -rf "$NATIVE_DIR"
    echo "  [OK] Removed"
fi

echo ""
echo "=========================================="
echo "[OK] Cleanup complete!"
echo "=========================================="
echo ""
echo "To rebuild:"
echo "  ./build-docker.sh    # Rebuild Docker deployment"
echo "  ./build-native.sh    # Rebuild Native deployment"
echo ""
echo "Or rebuild everything:"
echo "  cd .. && python build.py"
echo ""
