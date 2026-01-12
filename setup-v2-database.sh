#!/bin/bash

set -e

# Parse command line arguments
FORCE_RESET=false
if [[ "$1" == "--force" || "$1" == "--reset" ]]; then
    FORCE_RESET=true
fi

echo "=================================================="
echo "V2 Database Setup (MySQL - Orangescrum)"
echo "=================================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Load the env loader utility
source ./load-env.sh

# Load environment variables from os-v2/.env
ENV_FILE="os-v2/.env"
echo "Loading configuration from $ENV_FILE..."
if load_env "$ENV_FILE"; then
    echo -e "${GREEN}✓ Configuration loaded${NC}"
else
    echo -e "${RED}Error: Failed to load $ENV_FILE${NC}"
    echo "Please create $ENV_FILE with database configuration"
    exit 1
fi

# Set defaults if not defined in .env
DB_HOST=${DB_HOST:-mysql}
DB_NAME=${DB_NAME:-orangescrum}
DB_USER=${DB_USER:-osuser}
DB_PASSWORD=${DB_PASSWORD:-ospassword}
MYSQL_ROOT_PASSWORD=${MYSQL_ROOT_PASSWORD:-rootpassword}

echo "Database Configuration:"
echo "  Host: $DB_HOST"
echo "  Database: $DB_NAME"
echo "  User: $DB_USER"
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

echo "Step 1: Checking if MySQL container is running..."
check_container "mysql"
echo -e "${GREEN}✓ MySQL container is running${NC}"
echo ""

echo "Step 2: Waiting for MySQL to be ready..."
wait_for_db "mysql"
echo ""

echo "Step 3: Checking if database is already populated..."
EXISTING_TABLES=$(docker exec mysql mysql -uroot -p"$MYSQL_ROOT_PASSWORD" -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = '$DB_NAME';" 2>&1 | grep -v "Using a password" | tail -1)

if [ "$EXISTING_TABLES" -gt "0" ]; then
    if [ "$FORCE_RESET" = true ]; then
        echo -e "${YELLOW}⚠ Force reset enabled: Dropping and recreating database${NC}"
        docker exec mysql mysql -uroot -p"$MYSQL_ROOT_PASSWORD" -e "DROP DATABASE IF EXISTS $DB_NAME; CREATE DATABASE $DB_NAME;" 2>&1 | grep -v "Using a password"
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
        echo -e "${YELLOW}Proceeding with import...${NC}"
    fi
fi
echo ""

echo "Step 4: Setting up MySQL database (V2 - Orangescrum)..."
if [ -f "os-v2/payzilla (6).sql" ]; then
    echo "Found MySQL dump file: os-v2/payzilla (6).sql"
    echo "Importing database (this may take a few minutes)..."
    
    if docker exec -i mysql mysql -uroot -p"$MYSQL_ROOT_PASSWORD" "$DB_NAME" < "os-v2/payzilla (6).sql" 2>&1 | grep -v "Using a password" > /dev/null; then
        # Verify import
        TABLE_COUNT=$(docker exec mysql mysql -uroot -p"$MYSQL_ROOT_PASSWORD" -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = '$DB_NAME';" 2>&1 | grep -v "Using a password" | tail -1)
        echo -e "${GREEN}✓ MySQL import complete. Tables imported: $TABLE_COUNT${NC}"
    else
        echo -e "${RED}✗ MySQL import failed${NC}"
        echo "Run manually: docker exec -i mysql mysql -uroot -p$MYSQL_ROOT_PASSWORD $DB_NAME < os-v2/payzilla\\ \\(6\\).sql"
        exit 1
    fi
else
    echo -e "${YELLOW}Warning: MySQL dump file not found at os-v2/payzilla (6).sql${NC}"
    echo "Please place your MySQL dump file there and run this script again."
    exit 1
fi
echo ""

echo "=================================================="
echo "MySQL Database Status"
echo "=================================================="
echo ""

MYSQL_TABLES=$(docker exec mysql mysql -uroot -p"$MYSQL_ROOT_PASSWORD" -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = '$DB_NAME';" 2>&1 | grep -v "Using a password" | tail -1)
if [ "$MYSQL_TABLES" -gt "0" ]; then
    echo -e "Status: ${GREEN}✓ Ready${NC}"
    echo "Tables: $MYSQL_TABLES"
    echo "Database: $DB_NAME"
    echo "User: $DB_USER"
    echo "Password: $DB_PASSWORD"
    echo "Port: 3307 (host) / 3306 (container)"
else
    echo -e "Status: ${RED}✗ Empty${NC}"
    echo "Please import a database dump"
    exit 1
fi
echo ""

echo "=================================================="
echo -e "${GREEN}V2 Database Setup Complete!${NC}"
echo "=================================================="
echo ""
echo "Access V2: https://app.ossiba.online"
echo ""
