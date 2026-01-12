#!/bin/bash

# Development Deployment Script
# Verifies configuration and deploys all services

# Removed set -e to prevent script from exiting on minor errors

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# Change to script directory
cd "$(dirname "$0")"

print_header "Development Deployment - Verification & Launch"

# 1. Check prerequisites
print_info "Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed"
    exit 1
fi
print_success "Docker installed: $(docker --version | cut -d' ' -f3 | tr -d ',')"

if ! command -v docker compose &> /dev/null; then
    print_error "Docker Compose is not installed"
    exit 1
fi
print_success "Docker Compose installed: $(docker compose version --short)"

if ! docker info &> /dev/null; then
    print_error "Docker daemon is not running"
    exit 1
fi
print_success "Docker daemon is running"

# 2. Check required files
print_info "Checking required files..."

REQUIRED_FILES=(
    "docker-compose.yml"
    "Dockerfile"
    ".env"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        print_error "Missing required file: $file"
        exit 1
    fi
    print_success "Found: $file"
done

# 3. Check environment file
if [ ! -f "os-v4/.env" ]; then
    print_warning "Missing os-v4/.env - V4 app may not start properly"
fi

# 4. Detect domain from docker-compose.yml
DOMAIN=$(grep -oP 'v4\.\K[a-z0-9.-]+\.[a-z]+' docker-compose.yml | head -1 || echo "unknown")
print_info "Detected domain: $DOMAIN"

# 5. Check SSL certificates
if [ -f "certs/${DOMAIN}.crt" ]; then
    print_success "SSL certificate found: certs/${DOMAIN}.crt"
else
    print_warning "SSL certificate not found for $DOMAIN"
    read -p "Generate SSL certificate now? [y/N]: " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        ./generate-certs.sh
    else
        print_error "SSL certificate required. Run: ./generate-certs.sh"
        exit 1
    fi
fi

# 6. Validate docker-compose.yml
print_info "Validating docker-compose configuration..."
if docker compose config --quiet; then
    print_success "Docker Compose configuration is valid"
else
    print_error "Docker Compose configuration is invalid"
    exit 1
fi

# 7. Check if services are already running
if docker compose ps --services --filter "status=running" | grep -q .; then
    print_warning "Some services are already running"
    read -p "Restart all services? [y/N]: " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Stopping existing services..."
        docker compose down
    else
        print_info "Skipping deployment. Services already running."
        docker compose ps
        exit 0
    fi
fi

# 8. Check for docker-compose.override.yml
if [ -f "docker-compose.override.yml" ]; then
    print_success "Using docker-compose.override.yml for port mappings"
else
    print_warning "No docker-compose.override.yml found (using defaults)"
fi

# 9. Start services (Docker will handle pulling/building as needed)
print_header "Starting Services"
docker compose up -d

# 10. Wait for services to be healthy
print_info "Waiting for services to start (15 seconds)..."
sleep 15

# 11. Check service status
print_header "Service Status"
docker compose ps --format "table {{.Name}}\t{{.Status}}" | head -15

# 12. Check health status
print_info "Checking service health..."

HEALTHY=0
UNHEALTHY=0

for service in $(docker compose ps --services 2>/dev/null); do
    STATUS=$(docker compose ps "$service" --format "{{.Status}}" 2>/dev/null || echo "unknown")
    if echo "$STATUS" | grep -qi "healthy"; then
        print_success "$service: healthy"
        ((HEALTHY++)) || true
    elif echo "$STATUS" | grep -qi "unhealthy"; then
        print_error "$service: unhealthy"
        ((UNHEALTHY++)) || true
    elif echo "$STATUS" | grep -qi "Up"; then
        print_success "$service: running"
        ((HEALTHY++)) || true
    else
        print_warning "$service: $STATUS"
    fi
done

# 13. Get LAN IP
LAN_IP=$(hostname -I | awk '{print $1}')

# 14. Display access information
print_header "Deployment Complete!"

echo -e "${GREEN}✅ Services Started: $HEALTHY${NC}"
if [ $UNHEALTHY -gt 0 ]; then
    echo -e "${RED}❌ Unhealthy Services: $UNHEALTHY${NC}"
fi

echo -e "\n${BLUE}📋 Access Points:${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "🌐 V2 (Orangescrum):  ${GREEN}https://app.${DOMAIN}${NC}"
echo -e "🚀 V4 (Durango):      ${GREEN}https://v4.${DOMAIN}${NC}"
echo -e "📧 MailHog:           ${GREEN}https://mail.${DOMAIN}${NC}"
echo -e "📦 MinIO API:         ${GREEN}https://storage.${DOMAIN}${NC}"
echo -e "🖥️  MinIO Console:     ${GREEN}https://console.${DOMAIN}${NC}"
echo -e "📊 Traefik Dashboard: ${GREEN}http://localhost:8080${NC}"
echo -e "🔍 Selenium Browser:  ${GREEN}http://localhost:7900${NC} (noVNC)"

if [ -f ".env" ]; then
    HTTP_PORT=$(grep "^TRAEFIK_HTTP_PORT=" .env 2>/dev/null | cut -d'=' -f2 || echo "80")
    HTTPS_PORT=$(grep "^TRAEFIK_HTTPS_PORT=" .env 2>/dev/null | cut -d'=' -f2 || echo "443")
    
    if [ "$HTTP_PORT" != "80" ] || [ "$HTTPS_PORT" != "443" ]; then
        echo -e "\n${YELLOW}⚠ Custom Traefik Ports:${NC}"
        echo "  HTTP: $HTTP_PORT, HTTPS: $HTTPS_PORT"
    fi
fi

echo -e "\n${BLUE}🔌 Direct Database Access (127.0.0.1):${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "🐬 MySQL:             ${GREEN}localhost:3307${NC}"
echo -e "🐘 PostgreSQL:        ${GREEN}localhost:5433${NC}"
echo -e "🔴 Redis:             ${GREEN}localhost:6380${NC}"
echo -e "📦 MinIO API:         ${GREEN}localhost:9000${NC}"
echo -e "🖥️  MinIO Console:     ${GREEN}localhost:9001${NC}"
echo -e "⚡ Memcached (V4):    ${GREEN}localhost:11212${NC}"
echo -e "⚡ Memcached (V2):    ${GREEN}localhost:11213${NC}"

echo -e "\n${BLUE}🚀 Chrome Launchers:${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "Linux:   ${GREEN}launchers/linux-${DOMAIN}-{local|lan}.desktop${NC}"
echo -e "Windows: ${GREEN}launchers/windows-${DOMAIN}-{local|lan}.bat${NC}"

echo -e "\n${BLUE}🔑 Default Credentials:${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "MinIO:  ${GREEN}minioadmin / minioadmin${NC}"

echo -e "\n${BLUE}💡 Useful Commands:${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  View logs:        docker compose logs -f [service]"
echo "  Stop services:    docker compose down"
echo "  Restart service:  docker compose restart [service]"
echo "  Execute command:  docker compose exec [service] [command]"
echo ""
