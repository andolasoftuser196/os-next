#!/bin/bash
set -uo pipefail

# FrankenPHP Docker Entrypoint
# Sources the shared library for all heavy lifting.
# This file should stay short — all logic lives in lib/frankenphp-common.sh.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source shared library (shipped in Docker image at /orangescrum-app/lib/)
LIB="${SCRIPT_DIR}/lib/frankenphp-common.sh"
[ -f "$LIB" ] || LIB="/orangescrum-app/lib/frankenphp-common.sh"
source "$LIB"

echo "Starting OrangeScrum with FrankenPHP..."

# 1. Validate environment
validate_production_env

# 2. Apply runtime PHP overrides (from PHP_MEMORY_LIMIT, etc.)
apply_php_overrides

# 3. Start FrankenPHP and extract embedded app
extract_frankenphp_app "$@" || exit 1

# 4. Activate config templates
copy_config_files "$EXTRACTED_APP"

# 5. Run database migrations
run_migrations "/orangescrum-app/osv4-prod" "$EXTRACTED_APP"

# 6. Run seeders (auto-detect by default)
run_seeders "/orangescrum-app/osv4-prod" "$EXTRACTED_APP"

echo "[OK] Application is ready!"

# 7. Queue worker or server mode
if [ "${QUEUE_WORKER:-}" = "true" ]; then
    echo "Running as queue worker..."
    kill "$FRANKENPHP_PID" 2>/dev/null || true
    wait "$FRANKENPHP_PID" 2>/dev/null || true

    cd "$EXTRACTED_APP"
    exec /orangescrum-app/osv4-prod php-cli bin/cake.php queue worker \
        --max-runtime="${WORKER_MAX_RUNTIME:-1800}" \
        --verbose
else
    # Start cron for recurring tasks
    if command -v crond >/dev/null 2>&1; then
        crond -f -l 2 &
        echo "[OK] Cron daemon started"
    fi

    # Wait for FrankenPHP server
    wait "$FRANKENPHP_PID"
    exit $?
fi
