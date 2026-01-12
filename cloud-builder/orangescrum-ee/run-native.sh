#!/bin/bash
# FrankenPHP Native Runner (No Docker)
# Run OrangeScrum as a standalone binary on the host system

set +e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Auto-detect binary path (deployment package vs source)
if [ -f "./bin/orangescrum" ]; then
    BINARY="./bin/orangescrum"
elif [ -f "./orangescrum-app/orangescrum-ee" ]; then
    BINARY="./orangescrum-app/orangescrum-ee"
else
    BINARY="./orangescrum-app/orangescrum-ee"  # fallback for error message
fi

ENV_FILE=".env"
PORT="${PORT:-8080}"
RUN_MIGRATIONS="${RUN_MIGRATIONS:-true}"
DAEMON="${DAEMON:-auto}"  # auto, true, false

echo "=========================================="
echo "OrangeScrum FrankenPHP Native Runner"
echo "=========================================="

# Check if binary exists
if [ ! -f "$BINARY" ]; then
    echo "❌ FrankenPHP binary not found: $BINARY"
    echo "   Run: cd ../durango-builder && python build.py --skip-deploy"
    exit 1
fi

# Load environment variables from .env
if [ -f "$ENV_FILE" ]; then
    echo "Loading environment from $ENV_FILE..."
    # Use a safer method that doesn't interpret special characters
    while IFS= read -r line || [ -n "$line" ]; do
        # Skip empty lines and comments
        [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
        # Export the variable (no shell expansion)
        if [[ "$line" =~ ^[[:space:]]*([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]]; then
            key="${BASH_REMATCH[1]}"
            value="${BASH_REMATCH[2]}"
            # Strip surrounding quotes if present
            if [[ "$value" =~ ^\"(.*)\"$ ]] || [[ "$value" =~ ^\'(.*)\'$ ]]; then
                value="${BASH_REMATCH[1]}"
            fi
            export "$key=$value"
        fi
    done < "$ENV_FILE"
    echo "  ✓ Environment loaded"
else
    echo "⚠ Warning: .env file not found, using system environment only"
fi

# Override FULL_BASE_URL if not set
if [ -z "$FULL_BASE_URL" ]; then
    export FULL_BASE_URL="http://localhost:${PORT}"
    echo "  Setting FULL_BASE_URL=${FULL_BASE_URL}"
fi

# Clean up old FrankenPHP extraction directories
echo ""
echo "Cleaning up old extraction directories..."
OLD_DIRS=$(find /tmp -maxdepth 1 -name "frankenphp_*" -type d 2>/dev/null)
if [ -n "$OLD_DIRS" ]; then
    echo "$OLD_DIRS" | while read dir; do
        rm -rf "$dir" && echo "  ✓ Removed: $dir"
    done
else
    echo "  ✓ No old directories to clean"
fi

# Start FrankenPHP in background to extract app
echo ""
echo "Starting FrankenPHP server on port ${PORT}..."
"$BINARY" php-server -r webroot -l "0.0.0.0:${PORT}" &
FRANKENPHP_PID=$!

echo "  ✓ FrankenPHP started (PID: $FRANKENPHP_PID)"

# Wait for app extraction
echo ""
echo "Waiting for embedded app extraction..."
EXTRACTED_APP=""
for i in {1..30}; do
    EXTRACTED_APP=$(find /tmp -maxdepth 1 -name "frankenphp_*" -type d 2>/dev/null | head -1)
    if [ -n "$EXTRACTED_APP" ]; then
        echo "  ✓ Found extracted app at: $EXTRACTED_APP"
        break
    fi
    sleep 1
done

if [ -z "$EXTRACTED_APP" ]; then
    echo "❌ Could not find extracted FrankenPHP app directory"
    kill $FRANKENPHP_PID 2>/dev/null
    exit 1
fi

# Wait a bit more for extraction to complete
sleep 3

# Check if FrankenPHP is still running (it may have crashed due to path mismatch)
if ! kill -0 $FRANKENPHP_PID 2>/dev/null; then
    echo ""
    echo "⚠ FrankenPHP crashed during extraction (expected with path mismatch)"
    echo "  Restarting with correct extraction path..."
    
    # Start again - this time it should use the existing extracted directory
    "$BINARY" php-server -r webroot -l "0.0.0.0:${PORT}" &
    FRANKENPHP_PID=$!
    echo "  ✓ FrankenPHP restarted (PID: $FRANKENPHP_PID)"
    sleep 2
fi

# Copy configuration files
echo ""
echo "Setting up configuration files..."
if [ -d "$EXTRACTED_APP/config" ]; then
    cp "$EXTRACTED_APP/config/app_local.example.php" "$EXTRACTED_APP/config/app_local.php" 2>/dev/null && echo "  ✓ app_local.php"
    cp "$EXTRACTED_APP/config/cache_redis.example.php" "$EXTRACTED_APP/config/cache_redis.php" 2>/dev/null && echo "  ✓ cache_redis.php"
    cp "$EXTRACTED_APP/config/queue.example.php" "$EXTRACTED_APP/config/queue.php" 2>/dev/null && echo "  ✓ queue.php"
    cp "$EXTRACTED_APP/config/sendgrid.example.php" "$EXTRACTED_APP/config/sendgrid.php" 2>/dev/null && echo "  ✓ sendgrid.php"
    cp "$EXTRACTED_APP/config/storage.example.php" "$EXTRACTED_APP/config/storage.php" 2>/dev/null && echo "  ✓ storage.php"
    cp "$EXTRACTED_APP/config/recaptcha.example.php" "$EXTRACTED_APP/config/recaptcha.php" 2>/dev/null && echo "  ✓ recaptcha.php"
    cp "$EXTRACTED_APP/config/google_oauth.example.php" "$EXTRACTED_APP/config/google_oauth.php" 2>/dev/null && echo "  ✓ google_oauth.php"
    cp "$EXTRACTED_APP/config/v2_routing.example.php" "$EXTRACTED_APP/config/v2_routing.php" 2>/dev/null && echo "  ✓ v2_routing.php"
fi

# Run database migrations if requested
if [ "$RUN_MIGRATIONS" = "true" ] && [ -n "$DB_HOST" ]; then
    echo ""
    echo "=========================================="
    echo "Running database migrations..."
    echo "=========================================="
    
    cd "$EXTRACTED_APP"
    
    # Main migrations
    echo "  Running: bin/cake migrations migrate"
    "$SCRIPT_DIR/$BINARY" php-cli bin/cake.php migrations migrate 2>&1
    MIGRATE_EXIT=$?
    if [ $MIGRATE_EXIT -ne 0 ]; then
        echo "  ⚠ Migrations returned exit code $MIGRATE_EXIT, continuing..."
    else
        echo "  ✓ Main migrations completed successfully"
    fi
    
    # Plugin migrations
    if [ -d "$EXTRACTED_APP/plugins" ]; then
        for plugin_dir in "$EXTRACTED_APP/plugins"/*/ ; do
            if [ -d "$plugin_dir" ]; then
                plugin_name=$(basename "$plugin_dir")
                echo "  Running: bin/cake migrations migrate -p ${plugin_name}"
                "$SCRIPT_DIR/$BINARY" php-cli bin/cake.php migrations migrate -p "$plugin_name" 2>&1
                PLUGIN_EXIT=$?
                if [ $PLUGIN_EXIT -ne 0 ]; then
                    echo "  ⚠ Plugin ${plugin_name} migrations returned exit code $PLUGIN_EXIT, continuing..."
                else
                    echo "  ✓ Plugin ${plugin_name} migrations completed successfully"
                fi
            fi
        done
    fi
    
    cd "$SCRIPT_DIR"
    echo "=========================================="
    echo "✓ Migrations completed"
    echo "=========================================="
fi

# Determine if we should run seeders
SHOULD_SEED="false"
if [ "$RUN_SEEDERS" = "true" ]; then
    # Explicit request to run seeders
    SHOULD_SEED="true"
elif [ "$RUN_SEEDERS" = "false" ] || [ "$SKIP_SEEDERS" = "true" ]; then
    # Explicitly disabled
    SHOULD_SEED="false"
elif [ "$RUN_SEEDERS" = "auto" ] || [ -z "$RUN_SEEDERS" ]; then
    # Auto-detect: check if database needs seeding (if actions table is empty)
    if [ -n "$DB_HOST" ] && [ -d "$EXTRACTED_APP" ] && command -v psql >/dev/null 2>&1; then
        echo ""
        echo "Checking if database needs seeding..."
        ACTION_COUNT=$(PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "${DB_PORT:-5432}" -U "$DB_USERNAME" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM actions;" 2>/dev/null | tr -d ' ')
        if [ -z "$ACTION_COUNT" ] || [ "$ACTION_COUNT" = "0" ]; then
            echo "  ℹ Database appears empty (no actions found), will run seeders"
            SHOULD_SEED="true"
        else
            echo "  ℹ Database already seeded ($ACTION_COUNT actions found), skipping seeders"
            SHOULD_SEED="false"
        fi
    fi
fi

# Run database seeders if determined necessary
if [ "$SHOULD_SEED" = "true" ] && [ -n "$DB_HOST" ] && [ -d "$EXTRACTED_APP" ]; then
    echo ""
    echo "=========================================="
    echo "Step 1: Preparing database for seeding..."
    echo "=========================================="
    
    # Check if psql is available
    if ! command -v psql >/dev/null 2>&1; then
        echo "  ⚠ psql not found, skipping SQL schema operations"
        echo "  Note: Identity column conversion and sequence reset require postgresql-client"
    fi
    
    cd "$EXTRACTED_APP"
    
    # Step 1: Convert GENERATED ALWAYS to GENERATED BY DEFAULT (allow explicit IDs)
    if [ -f "$EXTRACTED_APP/config/schema/pg_config_1.sql" ] && command -v psql >/dev/null 2>&1; then
        echo "  Converting identity columns to GENERATED BY DEFAULT..."
        PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "${DB_PORT:-5432}" -U "$DB_USERNAME" -d "$DB_NAME" -f "$EXTRACTED_APP/config/schema/pg_config_1.sql" 2>&1 | grep -v "NOTICE:"
        IDENTITY_EXIT=$?
        if [ $IDENTITY_EXIT -ne 0 ]; then
            echo "  ⚠ Identity conversion completed with warnings"
        else
            echo "  ✓ Identity columns converted successfully"
        fi
    fi
    
    echo "=========================================="
    echo "Step 2: Running seeders..."
    echo "=========================================="
    # Step 2: Run seeders
    echo "  Running: bin/cake migrations seed"
    SEED_OUTPUT=$("$SCRIPT_DIR/$BINARY" php-cli bin/cake.php migrations seed 2>&1)
    SEED_EXIT=$?
    echo "$SEED_OUTPUT"
    
    # Check for duplicate key errors (data already exists) - this is not a failure
    if echo "$SEED_OUTPUT" | grep -q "duplicate key\|23505"; then
        echo "  ✓ Seeders completed (existing data preserved)"
    elif [ $SEED_EXIT -eq 0 ]; then
        echo "  ✓ All seeders completed successfully"
    else
        echo "  ⚠ Seeders completed with warnings: exit code $SEED_EXIT"
    fi
    
    echo "=========================================="
    echo "Step 3: Resetting sequences..."
    echo "=========================================="
    # Step 3: Reset sequences to max(id) + 1
    if [ -f "$EXTRACTED_APP/config/schema/pg_config_2.sql" ] && command -v psql >/dev/null 2>&1; then
        echo "  Resetting sequences..."
        PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "${DB_PORT:-5432}" -U "$DB_USERNAME" -d "$DB_NAME" -f "$EXTRACTED_APP/config/schema/pg_config_2.sql" 2>&1 | grep -v "NOTICE:"
        SEQ_EXIT=$?
        if [ $SEQ_EXIT -ne 0 ]; then
            echo "  ⚠ Sequence reset completed with warnings"
        else
            echo "  ✓ Sequences reset successfully"
        fi
    fi
    
    cd "$SCRIPT_DIR"
    echo "=========================================="
    echo "✓ Database seeding completed!"
    echo "=========================================="
else
    if [ "$SHOULD_SEED" = "false" ] && [ "$RUN_SEEDERS" != "false" ] && [ "$SKIP_SEEDERS" != "true" ]; then
        echo ""
        echo "ℹ Seeders skipped (database already initialized)"
    elif [ "$RUN_SEEDERS" = "false" ] || [ "$SKIP_SEEDERS" = "true" ]; then
        echo ""
        echo "ℹ Seeders disabled via environment variable"
    elif [ -z "$DB_HOST" ] || [ ! -d "$EXTRACTED_APP" ]; then
        echo ""
        echo "⚠ Cannot run seeders (DB_HOST not set or app not extracted)"
    else
        echo ""
        echo "ℹ Seeders not required (set RUN_SEEDERS=true to force, RUN_SEEDERS=auto for auto-detection)"
    fi
fi

echo ""
echo "=========================================="
echo "✓ Application is ready!"
echo "=========================================="
echo ""
echo "  URL: ${FULL_BASE_URL}"
echo "  PID: $FRANKENPHP_PID"
echo "  App: $EXTRACTED_APP"
echo ""

# Determine if we should run in foreground or background
RUN_FOREGROUND="false"

if [ "$DAEMON" = "false" ]; then
    # Explicitly requested foreground mode
    RUN_FOREGROUND="true"
elif [ "$DAEMON" = "true" ]; then
    # Explicitly requested daemon mode
    RUN_FOREGROUND="false"
elif [ "$DAEMON" = "auto" ]; then
    # Auto-detect: run in foreground if terminal is interactive
    if [ -t 0 ]; then
        RUN_FOREGROUND="true"
    else
        RUN_FOREGROUND="false"
    fi
fi

if [ "$RUN_FOREGROUND" = "true" ]; then
    echo "Running in foreground mode (Press Ctrl+C to stop)"
    echo ""
    
    # Wait for FrankenPHP process
    wait $FRANKENPHP_PID
    EXIT_CODE=$?
    
    if [ $EXIT_CODE -ne 0 ]; then
        echo ""
        echo "⚠ FrankenPHP exited with code $EXIT_CODE"
        
        # Try to get logs
        if [ -d "$EXTRACTED_APP/logs" ]; then
            echo "Recent error logs:"
            tail -n 50 "$EXTRACTED_APP/logs/error.log" 2>/dev/null || echo "  No error log available"
        fi
        
        exit $EXIT_CODE
    fi
else
    echo "Running in daemon mode (background)"
    echo ""
    echo "To view logs:"
    echo "  tail -f $EXTRACTED_APP/logs/error.log"
    echo ""
    echo "To stop the server:"
    echo "  kill $FRANKENPHP_PID"
    echo ""
    echo "To check status:"
    echo "  curl ${FULL_BASE_URL}/home/healthcheck"
    echo ""
    
    # Save PID to file for easy management
    echo "$FRANKENPHP_PID" > "$SCRIPT_DIR/frankenphp.pid"
    echo "PID saved to: $SCRIPT_DIR/frankenphp.pid"
    echo ""
    
    # Exit successfully, leaving FrankenPHP running in background
    exit 0
fi
