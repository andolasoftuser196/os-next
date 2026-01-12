#!/bin/bash
# Don't exit on errors - we want to handle them gracefully
set +e

# FrankenPHP Entrypoint (No Volume Persistence)
# This entrypoint:
# 1. Validates production-critical environment variables
# 2. Waits for FrankenPHP to extract the embedded app
# 3. Runs database migrations and seeding (optional)
# 4. Starts cron daemon for recurring tasks
# 5. Launches FrankenPHP server

echo "Starting OrangeScrum with FrankenPHP..."

# ============================================
# Production Security Validation
# ============================================
echo "Validating production environment..."

# Check for insecure default values (fail fast)
if [ "$SECURITY_SALT" = "__CHANGE_THIS_TO_RANDOM_STRING__" ]; then
    echo "❌ FATAL ERROR: SECURITY_SALT is still using the default value!"
    echo "   Generate a secure value with: openssl rand -base64 32"
    echo "   Set it in your .env file before deployment."
    exit 1
fi

if [ "$DB_PASSWORD" = "changeme_in_production" ]; then
    echo "❌ FATAL ERROR: DB_PASSWORD is still using the default value!"
    echo "   Generate a secure password with: openssl rand -base64 24"
    echo "   Set it in your .env file before deployment."
    exit 1
fi

if [ "$V4_ROUTING_ENABLED" = "true" ] && [ "$V2_ROUTING_API_KEY" = "your-secure-api-key-here-change-this" ]; then
    echo "❌ FATAL ERROR: V2_ROUTING_API_KEY is still using the default value!"
    echo "   Generate a secure key with: openssl rand -base64 32"
    echo "   Set it in your .env file before deployment."
    exit 1
fi

# Validate required variables are set
if [ -z "$SECURITY_SALT" ]; then
    echo "❌ FATAL ERROR: SECURITY_SALT environment variable is required!"
    echo "   Generate with: openssl rand -base64 32"
    exit 1
fi

if [ -z "$DB_PASSWORD" ]; then
    echo "❌ FATAL ERROR: DB_PASSWORD environment variable is required!"
    echo "   Set a strong password in your .env file."
    exit 1
fi

# Security length validation
if [ ${#SECURITY_SALT} -lt 32 ]; then
    echo "⚠ WARNING: SECURITY_SALT is shorter than recommended (current: ${#SECURITY_SALT}, recommended: 32+)"
    echo "   For production, use: openssl rand -base64 32"
fi

if [ ${#DB_PASSWORD} -lt 16 ]; then
    echo "⚠ WARNING: DB_PASSWORD is shorter than recommended (current: ${#DB_PASSWORD}, recommended: 16+)"
    echo "   For production, use: openssl rand -base64 24"
fi

# Production mode checks
if [ "$DEBUG" = "true" ]; then
    echo "⚠ WARNING: DEBUG=true is enabled! This should be 'false' in production."
    echo "   Debug mode may expose sensitive information."
fi

if [ "$APP_BIND_IP" = "0.0.0.0" ]; then
    echo "⚠ INFO: Application binding to 0.0.0.0 (all interfaces)"
    echo "   For reverse proxy deployments, consider APP_BIND_IP=127.0.0.1"
fi

echo "✓ Environment validation completed"

# ============================================
# Start FrankenPHP and Extract App
# ============================================

# Start FrankenPHP in background to let it extract the embedded app
"$@" &
FRANKENPHP_PID=$!

# Wait for FrankenPHP to extract the embedded app
echo "Waiting for embedded app extraction..."
EXTRACTED_APP=""
for i in {1..30}; do
    EXTRACTED_APP=$(find /tmp -maxdepth 1 -name "frankenphp_*" -type d 2>/dev/null | head -1)
    if [ -n "$EXTRACTED_APP" ]; then
        echo "Found extracted app at: $EXTRACTED_APP"
        break
    fi
    sleep 1
done

if [ -z "$EXTRACTED_APP" ]; then
    echo "ERROR: Could not find extracted FrankenPHP app directory"
    kill $FRANKENPHP_PID 2>/dev/null || true
    exit 1
fi

# Wait a bit more for extraction to complete
sleep 2

echo "✓ App extracted and ready"

# Export DB password if provided via file
if [ -n "$DB_PASSWORD_FILE" ] && [ -f "$DB_PASSWORD_FILE" ]; then
    export DB_PASSWORD=$(cat "$DB_PASSWORD_FILE")
fi

echo "✓ App extracted and ready"

# Export DB password if provided via file
if [ -n "$DB_PASSWORD_FILE" ] && [ -f "$DB_PASSWORD_FILE" ]; then
    export DB_PASSWORD=$(cat "$DB_PASSWORD_FILE")
fi

# Wait for extracted app and copy config files
if [ -n "$EXTRACTED_APP" ] && [ -d "$EXTRACTED_APP" ]; then
    echo "Setting up configuration files..."
    
    # Copy Redis cache configuration (default for production)
    cp "$EXTRACTED_APP/config/cache_redis.example.php" "$EXTRACTED_APP/config/cache_redis.php"
    echo "  ✓ Redis cache configuration ready"
    
    # Copy queue configuration
    cp "$EXTRACTED_APP/config/queue.example.php" "$EXTRACTED_APP/config/queue.php"
    echo "  ✓ Queue configuration ready"
    
    # Copy SendGrid email configuration
    cp "$EXTRACTED_APP/config/sendgrid.example.php" "$EXTRACTED_APP/config/sendgrid.php"
    echo "  ✓ SendGrid email configuration ready"
    
    # Copy S3 storage configuration
    cp "$EXTRACTED_APP/config/storage.example.php" "$EXTRACTED_APP/config/storage.php"
    echo "  ✓ S3 storage configuration ready"
    
    # Copy Google reCAPTCHA configuration
    cp "$EXTRACTED_APP/config/recaptcha.example.php" "$EXTRACTED_APP/config/recaptcha.php"
    echo "  ✓ Google reCAPTCHA configuration ready"
    
    # Copy Google OAuth configuration
    cp "$EXTRACTED_APP/config/google_oauth.example.php" "$EXTRACTED_APP/config/google_oauth.php"
    echo "  ✓ Google OAuth configuration ready"  
fi

# Run database migrations if DB_HOST is configured and SKIP_MIGRATIONS is not set
if [ -n "$DB_HOST" ] && [ -z "$SKIP_MIGRATIONS" ] && [ -d "$EXTRACTED_APP" ]; then
    echo "==========================================="
    echo "Step 1: Running database migrations..."
    echo "==========================================="
    
    cd "$EXTRACTED_APP"
    
    # Run main application migrations
    echo "  Running: bin/cake migrations migrate"
    /orangescrum-app/orangescrum-ee php-cli bin/cake.php migrations migrate 2>&1
    MIGRATE_EXIT=$?
    if [ $MIGRATE_EXIT -ne 0 ]; then
        echo "  ⚠ Migrations returned exit code $MIGRATE_EXIT, continuing..."
    else
        echo "  ✓ Main migrations completed successfully"
    fi
    
    # Run plugin migrations (only for plugins in plugins folder, not vendor)
    if [ -d "$EXTRACTED_APP/plugins" ]; then
        for plugin_dir in "$EXTRACTED_APP/plugins"/*/ ; do
            if [ -d "$plugin_dir" ]; then
                plugin_name=$(basename "$plugin_dir")
                echo "  Running: bin/cake migrations migrate -p ${plugin_name}"
                /orangescrum-app/orangescrum-ee php-cli bin/cake.php migrations migrate -p "$plugin_name" 2>&1
                PLUGIN_EXIT=$?
                if [ $PLUGIN_EXIT -ne 0 ]; then
                    echo "  ⚠ Plugin ${plugin_name} migrations returned exit code $PLUGIN_EXIT, continuing..."
                else
                    echo "  ✓ Plugin ${plugin_name} migrations completed successfully"
                fi
            fi
        done
    fi
    
    cd /
    echo "==========================================="
    echo "✓ Migrations completed"
    echo "==========================================="
else
    echo "⚠ Skipping migrations (DB_HOST not set or SKIP_MIGRATIONS=1)"
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
    echo "==========================================="
    echo "Step 2: Preparing database for seeding..."
    echo "==========================================="
    
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
    
    echo "==========================================="
    echo "Step 3: Running seeders..."
    echo "==========================================="
    # Step 2: Run seeders
    echo "  Running: bin/cake migrations seed"
    SEED_OUTPUT=$(/orangescrum-app/orangescrum-ee php-cli bin/cake.php migrations seed 2>&1)
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
    
    echo "==========================================="
    echo "Step 4: Resetting sequences..."
    echo "==========================================="
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
    
    cd /
    echo "==========================================="
    echo "✓ Database seeding completed!"
    echo "==========================================="
else
    if [ "$SHOULD_SEED" = "false" ] && [ "$RUN_SEEDERS" != "false" ] && [ "$SKIP_SEEDERS" != "true" ]; then
        echo "ℹ Seeders skipped (database already initialized)"
    elif [ "$RUN_SEEDERS" = "false" ] || [ "$SKIP_SEEDERS" = "true" ]; then
        echo "ℹ Seeders disabled via environment variable"
    elif [ -z "$DB_HOST" ] || [ ! -d "$EXTRACTED_APP" ]; then
        echo "⚠ Cannot run seeders (DB_HOST not set or app not extracted)"
    else
        echo "ℹ Seeders not required (set RUN_SEEDERS=true to force, RUN_SEEDERS=auto for auto-detection)"
    fi
fi

# Only start cron if not running as queue worker
if [ "$QUEUE_WORKER" != "true" ]; then
    echo "Starting cron daemon for recurring tasks..."
    crond -f -l 2 &
    CRON_PID=$!
    echo "✓ Cron daemon started (PID: $CRON_PID)"
fi

echo "✓ Application is ready!"

# Check if running as queue worker
if [ "$QUEUE_WORKER" = "true" ]; then
    echo "Running as queue worker..."
    
    # Kill the FrankenPHP server since we only need CLI
    kill $FRANKENPHP_PID 2>/dev/null || true
    
    # Wait for extracted app
    while [ -z "$EXTRACTED_APP" ]; do
        EXTRACTED_APP=$(find /tmp -maxdepth 1 -name "frankenphp_*" -type d 2>/dev/null | head -1)
        sleep 1
    done
    
    cd "$EXTRACTED_APP"
    
    # Run queue worker with configurable options
    echo "Starting queue worker..."
    exec /orangescrum-app/orangescrum-ee php-cli bin/cake.php queue worker \
        --max-runtime="${WORKER_MAX_RUNTIME:-1800}" \
        --sleep="${WORKER_SLEEP:-5}" \
        --verbose
else
    # Wait for FrankenPHP process and handle crashes
    wait $FRANKENPHP_PID
    EXIT_CODE=$?
    
    if [ $EXIT_CODE -ne 0 ]; then
        echo "⚠ FrankenPHP exited with code $EXIT_CODE"
        
        # Try to get logs from extracted app if available
        if [ -n "$EXTRACTED_APP" ] && [ -d "$EXTRACTED_APP/logs" ]; then
            echo "Recent error logs:"
            tail -n 50 "$EXTRACTED_APP/logs/error.log" 2>/dev/null || echo "  No error log available"
        fi
        
        # Exit with the same code to trigger container restart (if restart policy is set)
        exit $EXIT_CODE
    fi
fi
