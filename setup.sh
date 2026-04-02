#!/bin/bash
# One-command setup for OrangeScrum Docker
# Usage: ./setup.sh [domain]

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

DOMAIN="${1:-ossiba.local}"
export BUILDER_UID="${BUILDER_UID:-$(id -u)}"
export BUILDER_GID="${BUILDER_GID:-$(id -g)}"

clear
echo -e "${BLUE}╔════════════════════════════════════════════════╗"
echo "║   OrangeScrum Docker - Full Setup             ║"
echo "╚════════════════════════════════════════════════╝${NC}"
echo ""
echo "Domain: ${YELLOW}${DOMAIN}${NC}"
echo "Builder UID:GID: ${YELLOW}${BUILDER_UID}:${BUILDER_GID}${NC}"
echo ""

# Check prerequisites
echo -e "${BLUE}[1/8] Checking prerequisites...${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker not installed${NC}"
    echo "Install: curl -fsSL https://get.docker.com | sh"
    exit 1
fi
echo -e "${GREEN}✓ Docker installed$(docker --version | cut -d' ' -f3)${NC}"

if ! command -v docker compose &> /dev/null; then
    echo -e "${RED}✗ Docker Compose not installed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker Compose installed${NC}"

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python3 not installed${NC}"
    echo "Install: sudo apt install python3 python3-venv python3-pip"
    exit 1
fi
echo -e "${GREEN}✓ Python3 installed ($(python3 --version | cut -d' ' -f2))${NC}"

if ! command -v openssl &> /dev/null; then
    echo -e "${RED}✗ OpenSSL not installed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ OpenSSL installed${NC}"

echo ""

# Check application directories
echo -e "${BLUE}[2/8] Checking application directories...${NC}"

for app_dir in apps/orangescrum apps/durango-pg apps/orangescrum-v4; do
    if [ ! -d "$app_dir" ]; then
        echo -e "${YELLOW}⚠ $app_dir not found (will use empty directory)${NC}"
        mkdir -p "$app_dir"
    else
        echo -e "${GREEN}✓ $app_dir exists${NC}"
    fi
done

echo ""

# Setup Python venv
echo -e "${BLUE}[3/8] Setting up Python environment...${NC}"
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    .venv/bin/pip install --upgrade pip -q
    .venv/bin/pip install -r requirements.txt -q
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${GREEN}✓ Virtual environment exists${NC}"
fi

echo ""

# Generate configurations
echo -e "${BLUE}[4/8] Generating configurations for ${DOMAIN}...${NC}"
.venv/bin/python3 generate-config.py "${DOMAIN}" -y
echo -e "${GREEN}✓ Configurations generated${NC}"

echo ""

# Generate SSL certificates
echo -e "${BLUE}[5/8] Generating SSL certificates...${NC}"
if [ -f "certs/${DOMAIN}.crt" ]; then
    echo -e "${YELLOW}Certificate exists, skipping...${NC}"
else
    ./generate-certs.sh > /dev/null 2>&1 || true
    echo -e "${GREEN}✓ SSL certificates generated${NC}"
fi

# Build images
echo -e "${BLUE}[6/8] Building Docker images...${NC}"
if [ -f "./build-images.sh" ]; then
    chmod +x ./build-images.sh || true
    if ./build-images.sh all; then
        echo -e "${GREEN}✓ Images built${NC}"
    else
        echo -e "${YELLOW}build-images.sh failed; falling back to 'docker compose build'${NC}"
        docker compose build || true
    fi
else
    docker compose build || true
fi

# Start base services
echo -e "${BLUE}[7/8] Starting base services...${NC}"
docker compose up -d
echo -e "${GREEN}✓ Base services started (traefik, V2, databases, browser, dns)${NC}"

echo ""

# Create default instances
echo -e "${BLUE}[8/8] Creating default instances...${NC}"

# Wait for PostgreSQL to be ready
echo -e "${YELLOW}Waiting for PostgreSQL...${NC}"
for i in $(seq 1 30); do
    if docker compose exec -T postgres16 pg_isready -U postgres > /dev/null 2>&1; then
        echo -e "${GREEN}✓ PostgreSQL ready${NC}"
        break
    fi
    sleep 2
done

# Create default V4 instance
if [ -d "apps/orangescrum-v4" ]; then
    echo -e "${BLUE}Creating default V4 instance...${NC}"
    .venv/bin/python3 generate-config.py instance create --name v4-main --type v4 --subdomain v4 || echo -e "${YELLOW}V4 instance creation had warnings${NC}"
fi

# Create default selfhosted instance
if [ -d "apps/durango-pg" ]; then
    echo -e "${BLUE}Creating default selfhosted instance...${NC}"
    .venv/bin/python3 generate-config.py instance create --name sh-main --type selfhosted --subdomain selfhosted || echo -e "${YELLOW}Selfhosted instance creation had warnings${NC}"
fi

# Setup V2 database
if [ -x "./setup-v2-database.sh" ]; then
    echo -e "${BLUE}Setting up V2 database...${NC}"
    ./setup-v2-database.sh || echo -e "${YELLOW}V2 database setup had warnings${NC}"
fi

echo ""

# Final instructions
echo -e "${GREEN}╔════════════════════════════════════════════════╗"
echo "║   Setup Complete!                               ║"
echo "╚════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Access via VNC Browser:${NC}"
echo "  Open: http://localhost:3000"
echo ""
echo -e "${BLUE}URLs (inside VNC browser):${NC}"
echo "  V2 Landing:       https://www.${DOMAIN}"
echo "  V2 App:           https://app.${DOMAIN}"
echo "  V4 OrangeScrum:   https://v4.${DOMAIN}"
echo "  Selfhosted:       https://selfhosted.${DOMAIN}"
echo "  MailHog:          https://mail.${DOMAIN}"
echo "  Traefik:          https://traefik.${DOMAIN}"
echo ""
echo -e "${BLUE}Instance Management:${NC}"
echo "  List instances:    ./generate-config.py instance list"
echo "  Create V4:         ./generate-config.py instance create --name <name> --type v4 --subdomain <sub>"
echo "  Create Selfhosted: ./generate-config.py instance create --name <name> --type selfhosted --subdomain <sub>"
echo "  Destroy:           ./generate-config.py instance destroy --name <name> --drop-db"
echo "  DB migrations:     ./generate-config.py instance db-setup --name <name>"
echo ""
