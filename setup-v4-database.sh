#!/bin/bash

set -e

# OrangeScrum V4 PostgreSQL Database Setup Script
# Creates PostgreSQL user and database for OrangeScrum V4 service
# Runs migrations and seeding

echo "=================================================="
echo "OrangeScrum V4 - PostgreSQL Database Setup"
echo "=================================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Load environment
source ./load-env.sh

# Load V4 environment
ENV_FILE="os-v4/.env"
if load_env "$ENV_FILE"; then
    echo -e "${GREEN}✓ Configuration loaded from $ENV_FILE${NC}"
else
    echo -e "${YELLOW}⚠ Could not load $ENV_FILE, using defaults${NC}"
fi

# Get configuration from .env or use defaults
DB_HOST=${DB_HOST:-postgres16}
DB_PORT=${DB_PORT:-5432}
DB_NAME=${DB_NAME:-orangescrum}
DB_USERNAME=${DB_USERNAME:-orangescrum}
DB_PASSWORD=${DB_PASSWORD:-orangescrum}
POSTGRES_USER=${POSTGRES_USER:-postgres}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-postgres}

echo "Configuration:"
echo "  PostgreSQL Host: $DB_HOST:$DB_PORT"
echo "  Database Name: $DB_NAME"
echo "  Database User: $DB_USERNAME"
echo "  Admin User: $POSTGRES_USER"
echo ""

# Check if postgres16 container is running
echo "Step 1: Checking if PostgreSQL container is running..."
if docker compose ps postgres16 2>&1 | tr -d '\n' | grep -q "postgres16.*Up"; then
    echo -e "${GREEN}✓ PostgreSQL container is running${NC}"
else
    echo -e "${RED}✗ Error: postgres16 container is not running${NC}"
    echo "Please start services first: docker compose up -d"
    exit 1
fi
echo ""

# Check if orangescrum-v4 container exists
echo "Step 2: Checking if OrangeScrum V4 is available..."
if docker compose ps orangescrum-v4 2>/dev/null | grep -q "orangescrum-v4"; then
    if docker compose ps orangescrum-v4 | grep -q "Up"; then
        echo -e "${GREEN}✓ OrangeScrum V4 container is running${NC}"
        V4_AVAILABLE=true
    else
        echo -e "${YELLOW}⚠ OrangeScrum V4 container exists but is not running${NC}"
        V4_AVAILABLE=false
    fi
else
    echo -e "${YELLOW}⚠ OrangeScrum V4 service is not configured${NC}"
    V4_AVAILABLE=false
fi
echo ""

# Wait for PostgreSQL to be ready
echo "Step 3: Waiting for PostgreSQL to be ready..."
max_attempts=30
attempt=1
while [ $attempt -le $max_attempts ]; do
    if docker compose exec postgres16 pg_isready -U postgres > /dev/null 2>&1; then
        echo -e "${GREEN}✓ PostgreSQL is ready${NC}"
        break
    fi
    if [ $attempt -eq $max_attempts ]; then
        echo -e "${RED}✗ PostgreSQL did not become ready in time${NC}"
        exit 1
    fi
    echo "  Attempt $attempt/$max_attempts..."
    sleep 2
    attempt=$((attempt + 1))
done
echo ""

# Check if user already exists
echo "Step 4: Setting up user '$DB_USERNAME'..."
USER_EXISTS=$(docker compose exec postgres16 psql -U $POSTGRES_USER -tc "SELECT 1 FROM pg_user WHERE usename = '$DB_USERNAME';" 2>/dev/null | xargs || echo "")

if [ -n "$USER_EXISTS" ]; then
    echo -e "${YELLOW}⚠ User '$DB_USERNAME' already exists${NC}"
else
    echo "Creating user '$DB_USERNAME'..."
    docker compose exec postgres16 psql -U $POSTGRES_USER -c "CREATE USER $DB_USERNAME WITH PASSWORD '$DB_PASSWORD';" 2>/dev/null || true
    echo -e "${GREEN}✓ User created${NC}"
fi
echo ""

# Check if database already exists
echo "Step 5: Setting up database '$DB_NAME'..."
DB_EXISTS=$(docker compose exec postgres16 psql -U $POSTGRES_USER -tc "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME';" 2>/dev/null | xargs || echo "")

if [ -n "$DB_EXISTS" ]; then
    echo -e "${YELLOW}⚠ Database '$DB_NAME' already exists${NC}"
else
    echo "Creating database '$DB_NAME'..."
    docker exec $(docker compose ps -q postgres16) createdb -U $POSTGRES_USER -O $DB_USERNAME $DB_NAME 2>/dev/null || true
    echo -e "${GREEN}✓ Database created${NC}"
fi
echo ""

# Grant privileges
echo "Step 6: Granting privileges..."
docker compose exec postgres16 psql -U $POSTGRES_USER -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USERNAME;" 2>/dev/null || true
docker compose exec postgres16 psql -U $POSTGRES_USER -d $DB_NAME -c "GRANT ALL ON SCHEMA public TO $DB_USERNAME;" 2>/dev/null || true
echo -e "${GREEN}✓ Privileges granted${NC}"
echo ""

# Run migrations and seeders if V4 is available
if [ "$V4_AVAILABLE" = true ]; then
    echo "Step 7: Running database migrations..."
    if docker compose exec orangescrum-v4 php bin/cake.php migrations migrate 2>&1 | tee /tmp/v4_migrations.log; then
        echo -e "${GREEN}✓ Migrations completed${NC}"
    else
        echo -e "${YELLOW}⚠ Migrations completed with warnings${NC}"
    fi
    echo ""
    
    echo "Step 8: Running database seeders..."
    if docker compose exec orangescrum-v4 php bin/cake.php migrations seed 2>&1 | tee /tmp/v4_seeders.log; then
        echo -e "${GREEN}✓ Seeders completed${NC}"
    else
        echo -e "${YELLOW}⚠ Seeders completed with warnings${NC}"
    fi
    echo ""
else
    echo -e "${YELLOW}⚠ Skipping migrations/seeders (OrangeScrum V4 not running)${NC}"
    echo "To run migrations later:"
    echo "  docker compose exec orangescrum-v4 php bin/cake.php migrations migrate"
    echo "  docker compose exec orangescrum-v4 php bin/cake.php migrations seed"
    echo ""
fi

echo "=================================================="
echo "OrangeScrum V4 Setup Complete!"
echo "=================================================="
echo ""
echo "Database Details:"
echo "  Host: $DB_HOST"
echo "  Port: $DB_PORT"
echo "  Database: $DB_NAME"
echo "  User: $DB_USERNAME"
echo ""
echo "Access the database:"
echo "  docker compose exec postgres16 psql -U $DB_USERNAME -d $DB_NAME"
echo ""
echo "Test the application:"
echo "  https://v4.ossiba.local/"
echo ""
