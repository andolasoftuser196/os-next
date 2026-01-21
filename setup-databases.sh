#!/bin/bash

set -e

# Parse command line arguments
FORCE_RESET=false
if [[ "$1" == "--force" || "$1" == "--reset" ]]; then
    FORCE_RESET=true
fi

echo "=================================================="
echo "Database Setup Script - V4 (PostgreSQL)"
echo "=================================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Load the env loader utility
source ./load-env.sh

# Load environment variables from os-v4/.env
ENV_FILE="os-v4/.env"
echo "Loading configuration from $ENV_FILE..."
if load_env "$ENV_FILE"; then
    echo -e "${GREEN}✓ Configuration loaded${NC}"
else
    echo -e "${YELLOW}Warning: Could not load $ENV_FILE, using defaults${NC}"
fi

# Set defaults if not defined in .env
POSTGRES_HOST=${POSTGRES_HOST:-postgres16}
POSTGRES_DB=${POSTGRES_DB:-durango}
POSTGRES_USER=${POSTGRES_USER:-postgres}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-postgres}

echo "Database Configuration:"
echo "  Host: $POSTGRES_HOST"
echo "  Database: $POSTGRES_DB"
echo "  User: $POSTGRES_USER"
echo ""

# Function to check if container is running
check_container() {
    if ! docker ps --format '{{.Names}}' | grep -q "^$1$"; then
        echo -e "${RED}Error: Container $1 is not running${NC}"
        echo "Please start services first: docker compose up -d"
        exit 1
    fi
}

# Function to wait for database to be ready
wait_for_db() {
    local container=$1
    local max_attempts=30
    local attempt=1
    
    echo -e "${YELLOW}Waiting for $container to be ready...${NC}"
    
    while [ $attempt -le $max_attempts ]; do
        if docker compose ps $container | grep -q "healthy"; then
            echo -e "${GREEN}$container is ready!${NC}"
            return 0
        fi
        echo "Attempt $attempt/$max_attempts..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo -e "${RED}Error: $container did not become ready in time${NC}"
    exit 1
}

echo "Step 1: Checking if containers are running..."
check_container "postgres16"
check_container "durango-pg"
echo -e "${GREEN}✓ All containers are running${NC}"
echo ""

echo "Step 2: Waiting for databases to be ready..."
wait_for_db "postgres16"
echo ""

echo "Step 3: Checking if database is already populated..."
EXISTING_TABLES=$(docker exec postgres16 psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | xargs || echo "0")

if [ "$EXISTING_TABLES" -gt "0" ]; then
    if [ "$FORCE_RESET" = true ]; then
        echo -e "${YELLOW}⚠ Force reset enabled: Dropping and recreating database${NC}"
        docker exec postgres16 psql -U "$POSTGRES_USER" -c "DROP DATABASE IF EXISTS $POSTGRES_DB;" 2>/dev/null || true
        docker exec postgres16 psql -U "$POSTGRES_USER" -c "CREATE DATABASE $POSTGRES_DB;"
        echo -e "${GREEN}✓ Database reset complete${NC}"
    else
        echo -e "${YELLOW}⚠ Warning: Database already contains $EXISTING_TABLES tables${NC}"
        read -p "Do you want to continue? This may cause errors or data loss. [y/N]: " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Operation cancelled."
            echo "Tip: Use --force flag to reset database automatically"
            exit 0
        fi
        echo -e "${YELLOW}Proceeding with setup...${NC}"
    fi
fi
echo ""

echo "Step 4: Setting up PostgreSQL database (V4 - Durango)..."

# Check if there's a PostgreSQL dump
if [ -f "apps/durango-pg/durango.sql" ]; then
    echo "Found PostgreSQL dump file: apps/durango-pg/durango.sql"
    echo "Importing database..."
    docker exec -i postgres16 psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" < apps/durango-pg/durango.sql
    
    # Verify import
    TABLE_COUNT=$(docker exec postgres16 psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" | sed -n 3p | xargs)
    echo -e "${GREEN}✓ PostgreSQL import complete. Tables imported: $TABLE_COUNT${NC}"
elif docker exec durango-pg test -f bin/cake.php; then
    echo "No PostgreSQL dump found, running CakePHP InitDatabase command..."
    echo "This will run migrations and seed the database with initial data."
    echo ""
    
    # Run the init_database command with --seed flag (will ask for confirmation)
    if docker exec -i durango-pg php bin/cake.php init_database --seed; then
        TABLE_COUNT=$(docker exec postgres16 psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" | sed -n 3p | xargs)
        echo -e "${GREEN}✓ Database initialization complete. Tables created: $TABLE_COUNT${NC}"
    else
        echo -e "${YELLOW}Warning: Database initialization encountered issues${NC}"
        echo "You may need to run it manually: docker exec durango-pg php bin/cake.php init_database --seed"
    fi
else
    echo -e "${YELLOW}Warning: No PostgreSQL dump found and no migrations available${NC}"
    echo "Options:"
    echo "  1. Place a PostgreSQL dump at: apps/durango-pg/durango.sql"
    echo "  2. Run database setup manually: docker exec durango-pg php bin/cake.php init_database --seed"
fi
echo ""

echo "=================================================="
echo "Database Setup Summary"
echo "=================================================="
echo ""

# MySQL Status
echo "MySQL (V2 - Orangescrum):"
echo -e "  Status: ${YELLOW}Not set up by this script${NC}"
echo "  Run: ./setup-v2-database.sh"
echo ""

# PostgreSQL Status
echo "PostgreSQL (V4 - Durango):"
PG_TABLES=$(docker exec postgres16 psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" | sed -n 3p | xargs)
if [ "$PG_TABLES" -gt "0" ]; then
    echo -e "  Status: ${GREEN}✓ Ready${NC}"
    echo "  Tables: $PG_TABLES"
    echo "  Database: $POSTGRES_DB"
    echo "  User: $POSTGRES_USER"
    echo "  Password: $POSTGRES_PASSWORD"
    echo "  Port: 5433 (host) / 5432 (container)"
else
    echo -e "  Status: ${RED}✗ Empty${NC}"
    echo "  Please import a database dump or run migrations"
fi
echo ""

echo "=================================================="
echo -e "${GREEN}Setup Complete!${NC}"
echo "=================================================="
echo ""
echo "Next steps:"
echo "  - Setup V2 database: ./setup-v2-database.sh"
echo "  - Access V2: https://app.ossiba.online"
echo "  - Access V4: https://v4.ossiba.online"
echo "  - MailHog: https://mail.ossiba.online"
echo ""
