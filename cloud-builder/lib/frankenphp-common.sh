#!/bin/bash
# Shared functions for FrankenPHP Docker entrypoint and Native runner.
# Source this file — do not execute directly.
#
# Provides:
#   load_env_file           — parse .env into exported vars
#   resolve_binary          — find the FrankenPHP binary
#   validate_production_env — check security-critical env vars
#   extract_frankenphp_app  — start binary, wait for extraction, verify
#   copy_config_files       — glob-based config template activation
#   run_migrations          — CakePHP migrations + plugins
#   run_seeders             — auto-detect + seed + reset sequences
#   apply_php_overrides     — write runtime PHP INI overrides

# ---------------------------------------------------------------------------
# load_env_file [path]
# Parse a .env file and export all KEY=VALUE pairs. Works in bash and zsh.
# ---------------------------------------------------------------------------
load_env_file() {
    local env_file="${1:-.env}"
    [ -f "$env_file" ] || return 0

    while IFS= read -r line || [ -n "$line" ]; do
        # Skip empty lines and comments
        case "$line" in
            ""|\#*|[[:space:]]*\#*) continue ;;
        esac
        # Match KEY=VALUE (portable: no BASH_REMATCH)
        local key="${line%%=*}"
        local value="${line#*=}"
        # Skip lines without =
        [ "$key" = "$line" ] && continue
        # Trim leading whitespace from key
        key="${key#"${key%%[![:space:]]*}"}"
        # Strip surrounding quotes from value
        case "$value" in
            \"*\") value="${value#\"}"; value="${value%\"}" ;;
            \'*\') value="${value#\'}"; value="${value%\'}" ;;
        esac
        export "$key=$value"
    done < "$env_file"
}

# ---------------------------------------------------------------------------
# resolve_binary
# Prints the path to the FrankenPHP binary. Exits 1 if not found.
# ---------------------------------------------------------------------------
resolve_binary() {
    local candidates=(
        "./bin/orangescrum"
        "./orangescrum-app/osv4-prod"
        "/orangescrum-app/osv4-prod"
    )
    for bin in "${candidates[@]}"; do
        if [ -f "$bin" ]; then
            # Return absolute path so it works after cd to extracted app dir
            echo "$(cd "$(dirname "$bin")" && pwd)/$(basename "$bin")"
            return 0
        fi
    done
    echo "[ERROR] FrankenPHP binary not found" >&2
    return 1
}

# ---------------------------------------------------------------------------
# validate_production_env
# Checks security-critical environment variables. Exits on fatal issues.
# ---------------------------------------------------------------------------
validate_production_env() {
    local errors=0

    echo "Validating production environment..."

    # Fatal: insecure defaults
    if [ "${SECURITY_SALT:-}" = "__CHANGE_THIS_TO_RANDOM_STRING__" ]; then
        echo "  [FATAL] SECURITY_SALT is still the placeholder value"
        echo "    Fix: openssl rand -base64 32"
        errors=$((errors + 1))
    fi
    if [ "${DB_PASSWORD:-}" = "changeme_in_production" ]; then
        echo "  [FATAL] DB_PASSWORD is still the placeholder value"
        echo "    Fix: openssl rand -base64 24"
        errors=$((errors + 1))
    fi
    if [ "${V4_ROUTING_ENABLED:-}" = "true" ] && [ "${V2_ROUTING_API_KEY:-}" = "your-secure-api-key-here-change-this" ]; then
        echo "  [FATAL] V2_ROUTING_API_KEY is still the placeholder value"
        errors=$((errors + 1))
    fi

    # Fatal: required vars missing
    if [ -z "${SECURITY_SALT:-}" ]; then
        echo "  [FATAL] SECURITY_SALT is not set"
        errors=$((errors + 1))
    fi
    if [ -z "${DB_PASSWORD:-}" ]; then
        echo "  [FATAL] DB_PASSWORD is not set"
        errors=$((errors + 1))
    fi

    [ $errors -gt 0 ] && { echo "  $errors fatal error(s). Fix .env before deploying."; exit 1; }

    # Warnings
    [ "${#SECURITY_SALT}" -lt 32 ] 2>/dev/null && \
        echo "  [WARN] SECURITY_SALT shorter than 32 chars (current: ${#SECURITY_SALT})"
    [ "${#DB_PASSWORD}" -lt 16 ] 2>/dev/null && \
        echo "  [WARN] DB_PASSWORD shorter than 16 chars (current: ${#DB_PASSWORD})"
    [ "${DEBUG:-}" = "true" ] && \
        echo "  [WARN] DEBUG=true — should be false in production"

    echo "  [OK] Environment validation passed"
}

# ---------------------------------------------------------------------------
# extract_frankenphp_app BINARY_CMD...
#
# Starts the binary, waits for extraction to /tmp/frankenphp_*/, verifies
# completeness, handles the expected crash-restart cycle, writes a sentinel
# file for cron.
#
# Sets globals: EXTRACTED_APP, FRANKENPHP_PID
# Returns: 0 on success, 1 on failure
# ---------------------------------------------------------------------------
extract_frankenphp_app() {
    local max_wait="${FRANKENPHP_EXTRACT_TIMEOUT:-60}"

    # Clean old extraction directories
    find /tmp -maxdepth 1 -name "frankenphp_*" -type d -exec rm -rf {} + 2>/dev/null || true

    # Start the binary in background
    echo "  Starting FrankenPHP..."
    "$@" &
    FRANKENPHP_PID=$!

    # Poll for extraction directory + verify key files exist
    echo "  Waiting for app extraction (timeout: ${max_wait}s)..."
    local elapsed=0
    EXTRACTED_APP=""
    while [ "$elapsed" -lt "$max_wait" ]; do
        EXTRACTED_APP=$(find /tmp -maxdepth 1 -name "frankenphp_*" -type d 2>/dev/null | head -1)
        if [ -n "$EXTRACTED_APP" ] && \
           [ -f "$EXTRACTED_APP/webroot/index.php" ] && \
           [ -f "$EXTRACTED_APP/vendor/autoload.php" ]; then
            break
        fi
        sleep 1
        elapsed=$((elapsed + 1))
    done

    if [ -z "$EXTRACTED_APP" ]; then
        echo "  [ERROR] Extraction timed out after ${max_wait}s"
        kill "$FRANKENPHP_PID" 2>/dev/null || true
        return 1
    fi
    echo "  [OK] Extracted to: $EXTRACTED_APP"

    # Handle the expected crash-and-restart (FrankenPHP may crash after extraction)
    sleep 2
    if ! kill -0 "$FRANKENPHP_PID" 2>/dev/null; then
        echo "  [INFO] FrankenPHP stopped after extraction (restarting)..."
        "$@" &
        FRANKENPHP_PID=$!
        sleep 2
        if ! kill -0 "$FRANKENPHP_PID" 2>/dev/null; then
            echo "  [ERROR] FrankenPHP failed to restart"
            return 1
        fi
    fi

    # Write sentinel file so cron and helpers can find the extracted path
    echo "$EXTRACTED_APP" > /tmp/.frankenphp_app_path

    # Support DB password from Docker secrets file
    if [ -n "${DB_PASSWORD_FILE:-}" ] && [ -f "${DB_PASSWORD_FILE:-}" ]; then
        DB_PASSWORD="$(cat "$DB_PASSWORD_FILE")"
        export DB_PASSWORD
    fi

    echo "  [OK] FrankenPHP ready (PID: $FRANKENPHP_PID)"
    return 0
}

# ---------------------------------------------------------------------------
# copy_config_files APP_DIR
# Glob-based: activates all *.example.php → *.php (skips if .php exists).
# Handles both config/ and plugins/*/config/.
# ---------------------------------------------------------------------------
copy_config_files() {
    local app_dir="$1"
    [ -d "$app_dir/config" ] || return 0

    echo "Setting up configuration files..."
    local count=0

    # Main config directory
    for example in "$app_dir"/config/*.example.php; do
        [ -f "$example" ] || continue
        local target="${example%.example.php}.php"
        [ -f "$target" ] && continue
        cp "$example" "$target" && count=$((count + 1))
    done

    # Plugin config directories
    for plugin_dir in "$app_dir"/plugins/*/config; do
        [ -d "$plugin_dir" ] || continue
        for example in "$plugin_dir"/*.example.php; do
            [ -f "$example" ] || continue
            local target="${example%.example.php}.php"
            [ -f "$target" ] && continue
            cp "$example" "$target" && count=$((count + 1))
        done
    done

    echo "  [OK] Activated $count config file(s)"
}

# ---------------------------------------------------------------------------
# init_database BINARY APP_DIR
# Uses the CakePHP InitDatabaseCommand which handles:
#   - Migrations (main + plugins)
#   - Identity column conversion
#   - Seeders (with auto-detection)
#   - Sequence reset
# This replaces the old shell-based run_migrations + run_seeders.
# ---------------------------------------------------------------------------
init_database() {
    local binary="$1"
    local app_dir="$2"

    [ -n "${DB_HOST:-}" ] || { echo "  [SKIP] Database init (DB_HOST not set)"; return 0; }
    [ -d "$app_dir" ] || return 0

    cd "$app_dir"

    # Build command flags
    local flags="-y"

    if [ "${SKIP_MIGRATIONS:-}" = "true" ] || [ "${RUN_MIGRATIONS:-}" = "false" ]; then
        flags="$flags --skip-migrations"
    fi

    if [ "${SKIP_SEEDERS:-}" = "true" ] || [ "${RUN_SEEDERS:-}" = "false" ]; then
        flags="$flags --skip-seeders"
    elif [ "${RUN_SEEDERS:-auto}" != "false" ]; then
        flags="$flags --seed"
    fi

    echo "Running database initialization..."
    # shellcheck disable=SC2086
    "$binary" php-cli bin/cake.php init_database $flags 2>&1 || \
        echo "  [WARN] init_database returned non-zero exit"

    cd /
}

# ---------------------------------------------------------------------------
# apply_php_overrides
# Writes runtime PHP INI overrides from env vars (PHP_MEMORY_LIMIT, etc.)
# ---------------------------------------------------------------------------
apply_php_overrides() {
    local any_override=""
    [ -n "${PHP_MEMORY_LIMIT:-}" ] && any_override="1"
    [ -n "${PHP_POST_MAX_SIZE:-}" ] && any_override="1"
    [ -n "${PHP_UPLOAD_MAX_FILESIZE:-}" ] && any_override="1"
    [ -n "${PHP_MAX_EXECUTION_TIME:-}" ] && any_override="1"

    [ -n "$any_override" ] || return 0

    local override_dir="/tmp/php-overrides"
    mkdir -p "$override_dir"

    {
        [ -n "${PHP_MEMORY_LIMIT:-}" ] && echo "memory_limit = $PHP_MEMORY_LIMIT"
        [ -n "${PHP_POST_MAX_SIZE:-}" ] && echo "post_max_size = $PHP_POST_MAX_SIZE"
        [ -n "${PHP_UPLOAD_MAX_FILESIZE:-}" ] && echo "upload_max_filesize = $PHP_UPLOAD_MAX_FILESIZE"
        [ -n "${PHP_MAX_EXECUTION_TIME:-}" ] && echo "max_execution_time = $PHP_MAX_EXECUTION_TIME"
    } > "$override_dir/99-overrides.ini"

    export PHP_INI_SCAN_DIR=":$override_dir"
    echo "  [OK] PHP overrides applied from environment"
}
