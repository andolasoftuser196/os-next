#!/bin/bash
set -uo pipefail

# FrankenPHP Native Runner (No Docker)
# Sources the shared library for all heavy lifting.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Source shared library
LIB="$SCRIPT_DIR/lib/frankenphp-common.sh"
[ -f "$LIB" ] || { echo "[ERROR] lib/frankenphp-common.sh not found"; exit 1; }
source "$LIB"

# Resolve binary
BINARY=$(resolve_binary) || exit 1

PORT="${PORT:-8080}"
DAEMON="${DAEMON:-auto}"

echo "=========================================="
echo "OrangeScrum FrankenPHP Native Runner"
echo "=========================================="
echo "  Binary: $BINARY"

# Check binary exists
if [ ! -f "$BINARY" ]; then
    echo "[ERROR] FrankenPHP binary not found: $BINARY"
    echo "  Run: cd ../cloud-builder && python3 build.py --skip-deploy"
    exit 1
fi

# Pre-flight checks
echo ""
echo "Pre-flight checks..."

# Check psql
if command -v psql >/dev/null 2>&1; then
    echo "  [OK] psql: $(psql --version 2>/dev/null | head -1)"
else
    echo "  [WARN] psql not found — seeders will not run automatically"
    echo "  Install: apt install postgresql-client"
fi

# Check app extraction directory
APP_PATH="${FRANKENPHP_APP_PATH:-/app}"
if [ -d "$APP_PATH" ] && [ -w "$APP_PATH" ]; then
    echo "  [OK] App path: $APP_PATH (writable)"
elif mkdir -p "$APP_PATH" 2>/dev/null; then
    echo "  [OK] App path: $APP_PATH (created)"
else
    echo "  [WARN] Cannot write to $APP_PATH — will fall back to /tmp"
    echo "  Fix: sudo mkdir -p $APP_PATH && sudo chown \$USER:\$USER $APP_PATH"
fi

# Load .env
load_env_file ".env"

# Set FULL_BASE_URL if not configured
if [ -z "${FULL_BASE_URL:-}" ]; then
    export FULL_BASE_URL="http://localhost:${PORT}"
fi

# Validate environment (same checks as Docker)
validate_production_env

# Apply runtime PHP overrides
apply_php_overrides

# Start FrankenPHP and extract app
echo ""
extract_frankenphp_app "$BINARY" php-server -r webroot -l "0.0.0.0:${PORT}" || exit 1

# Activate config templates
copy_config_files "$EXTRACTED_APP"

# Initialize database (migrations + seeders via CakePHP command)
init_database "$BINARY" "$EXTRACTED_APP"

echo ""
echo "=========================================="
echo "[OK] Application is ready!"
echo "=========================================="
echo "  URL: ${FULL_BASE_URL}"
echo "  PID: $FRANKENPHP_PID"
echo ""

# Foreground or daemon mode
if [ "$DAEMON" = "true" ]; then
    echo "Running in daemon mode (PID: $FRANKENPHP_PID)"
    echo "$FRANKENPHP_PID" > "$SCRIPT_DIR/frankenphp.pid"
elif [ "$DAEMON" = "false" ] || { [ "$DAEMON" = "auto" ] && [ -t 0 ]; }; then
    echo "Running in foreground (Ctrl+C to stop)"
    wait "$FRANKENPHP_PID"
    exit $?
else
    echo "Running in daemon mode (PID: $FRANKENPHP_PID)"
    echo "$FRANKENPHP_PID" > "$SCRIPT_DIR/frankenphp.pid"
fi
