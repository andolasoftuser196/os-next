#!/bin/bash
# Don't exit on errors - we want to handle them gracefully
set +e

# OrangeScrum V4 Development Entrypoint
# This entrypoint:
# 1. Validates development environment variables
# 2. Copies example configuration files
# 3. Runs database migrations and seeding (optional)
# 4. Starts cron daemon for recurring tasks
# 5. Launches Apache web server

echo "Starting OrangeScrum V4 Development Environment..."

APP_DIR="/var/www/html"

# ============================================
# Development Environment Validation
# ============================================
echo "Validating development environment..."

# Check if app directory exists
if [ ! -d "$APP_DIR" ]; then
    echo "❌ FATAL ERROR: Application directory not found at $APP_DIR"
    echo "   Ensure the volume is properly mounted."
    exit 1
fi

# Warn about insecure default values (non-fatal in dev)
if [ "$SECURITY_SALT" = "__CHANGE_THIS_TO_RANDOM_STRING__" ]; then
    echo "⚠ WARNING: SECURITY_SALT is using the default value!"
    echo "   For production, generate with: openssl rand -base64 32"
fi

if [ "$DB_PASSWORD" = "changeme_in_production" ]; then
    echo "⚠ WARNING: DB_PASSWORD is using the default value!"
    echo "   For production, generate with: openssl rand -base64 24"
fi

if [ "$V4_ROUTING_ENABLED" = "true" ] && [ "$V2_ROUTING_API_KEY" = "your-secure-api-key-here-change-this" ]; then
    echo "⚠ WARNING: V2_ROUTING_API_KEY is using the default value!"
    echo "   For production, generate with: openssl rand -base64 32"
fi

# Validate required variables are set
if [ -z "$SECURITY_SALT" ]; then
    echo "❌ FATAL ERROR: SECURITY_SALT environment variable is required!"
    echo "   Generate with: openssl rand -base64 32"
    exit 1
fi

if [ -z "$DB_PASSWORD" ]; then
    echo "⚠ WARNING: DB_PASSWORD environment variable is not set!"
    echo "   Using empty password for development."
fi

# Development mode notification
if [ "$DEBUG" = "true" ]; then
    echo "✓ Running in DEBUG mode (development)"
else
    echo "⚠ INFO: DEBUG=false - Set DEBUG=true for development"
fi

echo "✓ Environment validation completed"

# ============================================
# Database Initialization
# ============================================
if [ -n "$DB_HOST" ]; then
    echo "Initializing PostgreSQL database..."
    
    # Wait for PostgreSQL to be ready
    max_attempts=30
    attempt=1
    echo "Waiting for PostgreSQL to be ready..."
    while [ $attempt -le $max_attempts ]; do
        if pg_isready -h "$DB_HOST" -p "${DB_PORT:-5432}" -U postgres > /dev/null 2>&1; then
            echo "✓ PostgreSQL is ready"
            break
        fi
        if [ $attempt -eq $max_attempts ]; then
            echo "⚠ PostgreSQL did not become ready in time, continuing anyway..."
            break
        fi
        sleep 2
        attempt=$((attempt + 1))
    done
    
    # Check if database user exists
    DB_USER_EXISTS=$(PGPASSWORD="${POSTGRES_PASSWORD:-postgres}" psql -h "$DB_HOST" -p "${DB_PORT:-5432}" -U postgres -tc "SELECT 1 FROM pg_user WHERE usename = '$DB_USERNAME';" 2>/dev/null | xargs || echo "")
    
    if [ -z "$DB_USER_EXISTS" ]; then
        echo "Creating PostgreSQL user '$DB_USERNAME'..."
        PGPASSWORD="${POSTGRES_PASSWORD:-postgres}" psql -h "$DB_HOST" -p "${DB_PORT:-5432}" -U postgres -c "CREATE USER $DB_USERNAME WITH PASSWORD '$DB_PASSWORD';" 2>/dev/null || true
    fi
    
    # Check if database exists
    DB_EXISTS=$(PGPASSWORD="${POSTGRES_PASSWORD:-postgres}" psql -h "$DB_HOST" -p "${DB_PORT:-5432}" -U postgres -tc "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME';" 2>/dev/null | xargs || echo "")
    
    if [ -z "$DB_EXISTS" ]; then
        echo "Creating PostgreSQL database '$DB_NAME'..."
        PGPASSWORD="${POSTGRES_PASSWORD:-postgres}" psql -h "$DB_HOST" -p "${DB_PORT:-5432}" -U postgres -c "CREATE DATABASE $DB_NAME OWNER $DB_USERNAME;" 2>/dev/null || true
    fi
    
    # Grant privileges
    PGPASSWORD="${POSTGRES_PASSWORD:-postgres}" psql -h "$DB_HOST" -p "${DB_PORT:-5432}" -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USERNAME;" 2>/dev/null || true
    PGPASSWORD="${POSTGRES_PASSWORD:-postgres}" psql -h "$DB_HOST" -p "${DB_PORT:-5432}" -U postgres -d "$DB_NAME" -c "GRANT ALL ON SCHEMA public TO $DB_USERNAME;" 2>/dev/null || true
    
    echo "✓ PostgreSQL database setup completed"
else
    echo "⚠ DB_HOST not set, skipping database initialization"
fi

# ============================================
# Setup Configuration Files
# ============================================
echo "Setting up configuration files..."

# Export DB password if provided via file
if [ -n "$DB_PASSWORD_FILE" ] && [ -f "$DB_PASSWORD_FILE" ]; then
    export DB_PASSWORD=$(cat "$DB_PASSWORD_FILE")
fi

cd "$APP_DIR"

# Copy Redis cache configuration (default for production)
if [ ! -f "$APP_DIR/config/cache_redis.php" ] && [ -f "$APP_DIR/config/cache_redis.example.php" ]; then
    cp "$APP_DIR/config/cache_redis.example.php" "$APP_DIR/config/cache_redis.php"
    echo "  ✓ Redis cache configuration ready"
else
    echo "  ℹ Redis cache configuration already exists or example not found"
fi

# Copy queue configuration
if [ ! -f "$APP_DIR/config/queue.php" ] && [ -f "$APP_DIR/config/queue.example.php" ]; then
    cp "$APP_DIR/config/queue.example.php" "$APP_DIR/config/queue.php"
    echo "  ✓ Queue configuration ready"
else
    echo "  ℹ Queue configuration already exists or example not found"
fi

# Copy SendGrid email configuration
if [ ! -f "$APP_DIR/config/sendgrid.php" ] && [ -f "$APP_DIR/config/sendgrid.example.php" ]; then
    cp "$APP_DIR/config/sendgrid.example.php" "$APP_DIR/config/sendgrid.php"
    echo "  ✓ SendGrid email configuration ready"
else
    echo "  ℹ SendGrid configuration already exists or example not found"
fi

# Copy S3 storage configuration
if [ ! -f "$APP_DIR/config/storage.php" ] && [ -f "$APP_DIR/config/storage.example.php" ]; then
    cp "$APP_DIR/config/storage.example.php" "$APP_DIR/config/storage.php"
    echo "  ✓ S3 storage configuration ready"
else
    echo "  ℹ S3 storage configuration already exists or example not found"
fi

# Copy Google reCAPTCHA configuration
if [ ! -f "$APP_DIR/config/recaptcha.php" ] && [ -f "$APP_DIR/config/recaptcha.example.php" ]; then
    cp "$APP_DIR/config/recaptcha.example.php" "$APP_DIR/config/recaptcha.php"
    echo "  ✓ Google reCAPTCHA configuration ready"
else
    echo "  ℹ reCAPTCHA configuration already exists or example not found"
fi

# Copy Google OAuth configuration
if [ ! -f "$APP_DIR/config/google_oauth.php" ] && [ -f "$APP_DIR/config/google_oauth.example.php" ]; then
    cp "$APP_DIR/config/google_oauth.example.php" "$APP_DIR/config/google_oauth.php"
    echo "  ✓ Google OAuth configuration ready"
else
    echo "  ℹ Google OAuth configuration already exists or example not found"
fi

# Copy V2 routing configuration
if [ ! -f "$APP_DIR/config/v2_routing.php" ] && [ -f "$APP_DIR/config/v2_routing.example.php" ]; then
    cp "$APP_DIR/config/v2_routing.example.php" "$APP_DIR/config/v2_routing.php"
    echo "  ✓ V2 routing configuration ready"
else
    echo "  ℹ V2 routing configuration already exists or example not found"
fi

# Set proper permissions for development
echo "Setting permissions..."
chown -R www-data:www-data "$APP_DIR/tmp" "$APP_DIR/logs" 2>/dev/null || true
chmod -R 777 "$APP_DIR/tmp" "$APP_DIR/logs" 2>/dev/null || true
echo "  ✓ Permissions updated"

# ============================================
# Database Migrations
# ============================================
# Run database migrations if DB_HOST is configured
# Set RUN_MIGRATIONS=false to skip
if [ -n "$DB_HOST" ] && [ "$RUN_MIGRATIONS" != "false" ]; then
    echo "==========================================="
    echo "Step 1: Running database migrations..."
    echo "==========================================="
    
    # Run main application migrations
    echo "  Running: bin/cake migrations migrate"
    php bin/cake.php migrations migrate 2>&1
    MIGRATE_EXIT=$?
    if [ $MIGRATE_EXIT -ne 0 ]; then
        echo "  ⚠ Migrations returned exit code $MIGRATE_EXIT, continuing..."
    else
        echo "  ✓ Main migrations completed successfully"
    fi
    
    # Run plugin migrations (only for plugins in plugins folder, not vendor)
    if [ -d "$APP_DIR/plugins" ]; then
        for plugin_dir in "$APP_DIR/plugins"/*/ ; do
            if [ -d "$plugin_dir" ]; then
                plugin_name=$(basename "$plugin_dir")
                echo "  Running: bin/cake migrations migrate -p ${plugin_name}"
                php bin/cake.php migrations migrate -p "$plugin_name" 2>&1
                PLUGIN_EXIT=$?
                if [ $PLUGIN_EXIT -ne 0 ]; then
                    echo "  ⚠ Plugin ${plugin_name} migrations returned exit code $PLUGIN_EXIT, continuing..."
                else
                    echo "  ✓ Plugin ${plugin_name} migrations completed successfully"
                fi
            fi
        done
    fi
    
    echo "==========================================="
    echo "✓ Migrations completed"
    echo "==========================================="
else
    echo "ℹ Skipping migrations (set RUN_MIGRATIONS=false to disable)"
fi

# ============================================
# Database Seeders
# ============================================
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
    if [ -n "$DB_HOST" ] && command -v psql >/dev/null 2>&1; then
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
if [ "$SHOULD_SEED" = "true" ] && [ -n "$DB_HOST" ]; then
    echo "==========================================="
    echo "Step 2: Preparing database for seeding..."
    echo "==========================================="
    
    # Check if psql is available
    if ! command -v psql >/dev/null 2>&1; then
        echo "  ⚠ psql not found, skipping SQL schema operations"
        echo "  Note: Identity column conversion and sequence reset require postgresql-client"
    fi
    
    # Step 1: Convert GENERATED ALWAYS to GENERATED BY DEFAULT (allow explicit IDs)
    if [ -f "$APP_DIR/config/schema/pg_config_1.sql" ] && command -v psql >/dev/null 2>&1; then
        echo "  Converting identity columns to GENERATED BY DEFAULT..."
        PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "${DB_PORT:-5432}" -U "$DB_USERNAME" -d "$DB_NAME" -f "$APP_DIR/config/schema/pg_config_1.sql" 2>&1 | grep -v "NOTICE:"
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
    SEED_OUTPUT=$(php bin/cake.php migrations seed 2>&1)
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
    if [ -f "$APP_DIR/config/schema/pg_config_2.sql" ] && command -v psql >/dev/null 2>&1; then
        echo "  Resetting sequences..."
        PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "${DB_PORT:-5432}" -U "$DB_USERNAME" -d "$DB_NAME" -f "$APP_DIR/config/schema/pg_config_2.sql" 2>&1 | grep -v "NOTICE:"
        SEQ_EXIT=$?
        if [ $SEQ_EXIT -ne 0 ]; then
            echo "  ⚠ Sequence reset completed with warnings"
        else
            echo "  ✓ Sequences reset successfully"
        fi
    fi
    
    echo "==========================================="
    echo "✓ Database seeding completed!"
    echo "==========================================="
else
    if [ "$SHOULD_SEED" = "false" ] && [ "$RUN_SEEDERS" != "false" ] && [ "$SKIP_SEEDERS" != "true" ]; then
        echo "ℹ Seeders skipped (database already initialized)"
    elif [ "$RUN_SEEDERS" = "false" ] || [ "$SKIP_SEEDERS" = "true" ]; then
        echo "ℹ Seeders disabled via environment variable"
    elif [ -z "$DB_HOST" ]; then
        echo "⚠ Cannot run seeders (DB_HOST not set)"
    else
        echo "ℹ Seeders not required (set RUN_SEEDERS=true to force, RUN_SEEDERS=auto for auto-detection)"
    fi
fi

# ============================================
# Start Services
# ============================================
# Start cron daemon if available (for recurring tasks)
if command -v cron >/dev/null 2>&1; then
    echo "Starting cron daemon for recurring tasks..."
    cron
    echo "✓ Cron daemon started"
elif command -v crond >/dev/null 2>&1; then
    echo "Starting cron daemon for recurring tasks..."
    crond -f -l 2 &
    CRON_PID=$!
    echo "✓ Cron daemon started (PID: $CRON_PID)"
else
    echo "⚠ Cron not available in this container"
fi

echo "✓ Development environment is ready!"
echo ""
echo "==========================================="
echo "OrangeScrum V4 Development Server"
echo "==========================================="
echo "App Directory: $APP_DIR"
echo "Database: $DB_HOST:${DB_PORT:-5432}/$DB_NAME"
echo "Debug Mode: ${DEBUG:-false}"
echo "==========================================="
echo ""

# Start Apache in foreground
echo "Starting Apache web server..."
exec apache2ctl -D FOREGROUND
