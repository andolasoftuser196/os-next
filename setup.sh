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

clear
echo -e "${BLUE}╔════════════════════════════════════════════════╗"
echo "║   OrangeScrum Docker - Full Setup             ║"
echo "╚════════════════════════════════════════════════╝${NC}"
echo ""
echo "Domain: ${YELLOW}${DOMAIN}${NC}"
echo ""

# Check prerequisites
echo -e "${BLUE}[1/6] Checking prerequisites...${NC}"

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
echo -e "${BLUE}[2/6] Verifying application directories...${NC}"

if [ ! -d "apps/durango-pg" ]; then
    echo -e "${RED}✗ apps/durango-pg not found${NC}"
    echo "Expected: apps/durango-pg/"
    exit 1
fi
echo -e "${GREEN}✓ apps/durango-pg exists${NC}"

if [ ! -d "apps/orangescrum" ]; then
    echo -e "${RED}✗ apps/orangescrum not found${NC}"
    echo "Expected: apps/orangescrum/"
    exit 1
fi
echo -e "${GREEN}✓ apps/orangescrum exists${NC}"

echo ""

# Setup Python venv
echo -e "${BLUE}[3/6] Setting up Python environment...${NC}"
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
echo -e "${BLUE}[4/6] Generating configurations for ${DOMAIN}...${NC}"
.venv/bin/python3 generate-config.py "${DOMAIN}" -y --apply-env
echo -e "${GREEN}✓ Configurations generated and .env files applied${NC}"

echo ""

# Generate SSL certificates
echo -e "${BLUE}[5/6] Generating SSL certificates...${NC}"
if [ -f "certs/${DOMAIN}.crt" ]; then
    echo -e "${YELLOW}Certificate exists, skipping...${NC}"
else
    ./generate-certs.sh > /dev/null 2>&1 || true
    echo -e "${GREEN}✓ SSL certificates generated${NC}"
fi

# Start services (build + up)
echo -e "${BLUE}[6/6] Building and starting services...${NC}"
docker compose up -d --build
echo -e "${GREEN}✓ Services started${NC}"

# Run database setup scripts (best-effort)
echo -e "${BLUE}Setting up databases...${NC}"
if [ -x "./setup-databases.sh" ]; then
    ./setup-databases.sh || echo "Warning: setup-databases.sh failed"
fi
if [ -x "./setup-v2-database.sh" ]; then
    ./setup-v2-database.sh || echo "Warning: setup-v2-database.sh failed"
fi

echo ""

# Final instructions
echo -e "${BLUE}[6/6] Setup complete!${NC}"
echo ""

# Get LAN IP
LAN_IP=$(hostname -I | awk '{print $1}')

echo -e "${GREEN}╔════════════════════════════════════════════════╗"
echo "║   Next Steps                                   ║"
echo "╚════════════════════════════════════════════════╝${NC}"
echo ""
echo "1. Start services:"
echo -e "   ${YELLOW}docker compose up -d${NC}"
echo ""
echo "2. Setup databases:"
echo -e "   ${YELLOW}# V2 Orangescrum (MySQL):${NC}"
echo -e "   ${YELLOW}./setup-v2-database.sh${NC}"
echo -e "   ${YELLOW}# V4 Durango PG (PostgreSQL):${NC}"
echo -e "   ${YELLOW}./setup-databases.sh${NC}"
echo ""
echo "3. Install Chrome launchers:"
echo -e "   ${YELLOW}# Linux:${NC}"
echo -e "   ${YELLOW}cp launchers/linux-${DOMAIN}-*.desktop ~/.local/share/applications/${NC}"
echo -e "   ${YELLOW}# Windows (WSL):${NC}"
echo -e "   ${YELLOW}# Use launchers/windows-${DOMAIN}-*.bat files${NC}"
echo ""
echo -e "${BLUE}Access URLs:${NC}"
echo "  V2 (Orangescrum):    https://app.${DOMAIN}"
echo "  V4 (OrangeScrum):    https://v4.${DOMAIN}"
echo "  V4 (Durango PG):     https://selfhosted.${DOMAIN}"
echo "  MailHog:             https://mail.${DOMAIN}"
echo "  MinIO API:           https://storage.${DOMAIN}"
echo "  MinIO Console:       https://console.${DOMAIN}"
echo "  Traefik Dashboard:   https://traefik.${DOMAIN}/dashboard/"
echo ""
echo -e "${BLUE}LAN Access:${NC}"
echo "  From other devices, use the LAN launcher (maps to ${LAN_IP})"
echo ""
