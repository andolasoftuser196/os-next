#!/bin/bash
# Production Environment Validator
# Validates that all required environment variables are set and secure
# Usage: ./validate-env.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ERRORS=0
WARNINGS=0

echo "=========================================="
echo "OrangeScrum Production Environment Validator"
echo "=========================================="
echo ""

# Load .env file if it exists
if [ ! -f ".env" ]; then
    echo -e "${RED}ERROR: .env file not found${NC}"
    echo "Run: cp .env.example .env"
    exit 1
fi

# Load environment variables
set -a
source .env
set +a

echo "Validating environment configuration..."
echo ""

# Function to check if variable is set and not default
check_required() {
    local var_name="$1"
    local var_value="${!var_name}"
    local default_value="$2"
    local description="$3"
    
    if [ -z "$var_value" ]; then
        echo -e "${RED}✗ CRITICAL: $var_name is not set${NC}"
        echo "  Description: $description"
        ERRORS=$((ERRORS + 1))
        return 1
    fi
    
    if [ -n "$default_value" ] && [ "$var_value" = "$default_value" ]; then
        echo -e "${RED}✗ CRITICAL: $var_name is still using default value${NC}"
        echo "  Current: $var_value"
        echo "  Description: $description"
        ERRORS=$((ERRORS + 1))
        return 1
    fi
    
    echo -e "${GREEN}✓ $var_name is configured${NC}"
    return 0
}

# Function to check optional but recommended
check_recommended() {
    local var_name="$1"
    local var_value="${!var_name}"
    local description="$2"
    
    if [ -z "$var_value" ]; then
        echo -e "${YELLOW}⚠ WARNING: $var_name is not set${NC}"
        echo "  Description: $description"
        WARNINGS=$((WARNINGS + 1))
        return 1
    fi
    
    echo -e "${GREEN}✓ $var_name is configured${NC}"
    return 0
}

# Function to validate value matches expected
check_value() {
    local var_name="$1"
    local var_value="${!var_name}"
    local expected="$2"
    local description="$3"
    
    if [ "$var_value" != "$expected" ]; then
        echo -e "${YELLOW}⚠ WARNING: $var_name should be '$expected' for production${NC}"
        echo "  Current: $var_value"
        echo "  Description: $description"
        WARNINGS=$((WARNINGS + 1))
        return 1
    fi
    
    echo -e "${GREEN}✓ $var_name is correctly set to '$expected'${NC}"
    return 0
}

echo "=== Critical Security Variables ==="
check_required "SECURITY_SALT" "__CHANGE_THIS_TO_RANDOM_STRING__" "Encryption key for sessions and passwords"
check_required "DB_PASSWORD" "changeme_in_production" "Database password"

# Check if SECURITY_SALT is strong enough (at least 32 characters)
if [ -n "$SECURITY_SALT" ] && [ "$SECURITY_SALT" != "__CHANGE_THIS_TO_RANDOM_STRING__" ]; then
    if [ ${#SECURITY_SALT} -lt 32 ]; then
        echo -e "${YELLOW}⚠ WARNING: SECURITY_SALT should be at least 32 characters${NC}"
        echo "  Current length: ${#SECURITY_SALT}"
        echo "  Generate with: openssl rand -base64 32"
        WARNINGS=$((WARNINGS + 1))
    fi
fi

# Check if DB_PASSWORD is strong enough (at least 16 characters)
if [ -n "$DB_PASSWORD" ] && [ "$DB_PASSWORD" != "changeme_in_production" ]; then
    if [ ${#DB_PASSWORD} -lt 16 ]; then
        echo -e "${YELLOW}⚠ WARNING: DB_PASSWORD should be at least 16 characters${NC}"
        echo "  Current length: ${#DB_PASSWORD}"
        echo "  Generate with: openssl rand -base64 24"
        WARNINGS=$((WARNINGS + 1))
    fi
fi

check_value "DEBUG" "false" "Debug mode must be disabled in production"

echo ""
echo "=== Database Configuration ==="
check_required "DB_HOST" "" "Database server hostname"
check_required "DB_PORT" "" "Database server port"
check_required "DB_USERNAME" "" "Database username"
check_required "DB_NAME" "" "Database name"

echo ""
echo "=== Redis Configuration ==="
check_required "REDIS_HOST" "" "Redis server hostname"
check_recommended "REDIS_PASSWORD" "Redis authentication password (highly recommended)"

# Check cache engine
if [ "$CACHE_ENGINE" = "redis" ]; then
    echo -e "${GREEN}✓ CACHE_ENGINE is set to 'redis' (recommended for production)${NC}"
else
    echo -e "${YELLOW}⚠ WARNING: CACHE_ENGINE is '$CACHE_ENGINE', 'redis' is recommended for production${NC}"
    WARNINGS=$((WARNINGS + 1))
fi

# Check queue engine
if [ "$QUEUE_ENGINE" = "redis" ]; then
    echo -e "${GREEN}✓ QUEUE_ENGINE is set to 'redis' (recommended for production)${NC}"
else
    echo -e "${YELLOW}⚠ WARNING: QUEUE_ENGINE is '$QUEUE_ENGINE', 'redis' is recommended for production${NC}"
    WARNINGS=$((WARNINGS + 1))
fi

echo ""
echo "=== Storage Configuration ==="
check_required "STORAGE_ENDPOINT" "" "S3-compatible storage endpoint"
check_required "STORAGE_ACCESS_KEY" "your-access-key" "S3 access key"
check_required "STORAGE_SECRET_KEY" "your-secret-key" "S3 secret key"
check_required "STORAGE_BUCKET" "" "S3 bucket name"
check_required "STORAGE_REGION" "" "S3 region"

echo ""
echo "=== Email Configuration ==="
if [ "$EMAIL_TRANSPORT" = "sendgrid" ]; then
    check_required "EMAIL_API_KEY" "" "SendGrid API key"
elif [ "$EMAIL_TRANSPORT" = "smtp" ]; then
    check_required "SMTP_HOST" "" "SMTP server hostname"
    check_required "SMTP_USERNAME" "" "SMTP username"
    check_required "SMTP_PASSWORD" "" "SMTP password"
else
    echo -e "${YELLOW}⚠ WARNING: EMAIL_TRANSPORT is '$EMAIL_TRANSPORT', should be 'sendgrid' or 'smtp'${NC}"
    WARNINGS=$((WARNINGS + 1))
fi

check_recommended "FROM_EMAIL" "Email address for outgoing emails"
check_recommended "NOTIFY_EMAIL" "Email address for system notifications"

echo ""
echo "=== Application Configuration ==="
check_recommended "FULL_BASE_URL" "Full URL of the application (e.g., https://app.example.com)"

# Check if running behind proxy
if [ "$APP_BIND_IP" = "0.0.0.0" ]; then
    echo -e "${YELLOW}⚠ WARNING: APP_BIND_IP is '0.0.0.0', consider '127.0.0.1' if behind reverse proxy${NC}"
    echo "  For direct internet exposure, ensure proper firewall rules are in place"
    WARNINGS=$((WARNINGS + 1))
fi

echo ""
echo "=== Session Configuration ==="
if [ "$SESSION_HANDLER" = "cache" ]; then
    echo -e "${GREEN}✓ SESSION_HANDLER is set to 'cache' (recommended for production)${NC}"
else
    echo -e "${YELLOW}⚠ WARNING: SESSION_HANDLER is '$SESSION_HANDLER', 'cache' is recommended for production${NC}"
    WARNINGS=$((WARNINGS + 1))
fi

echo ""
echo "=== V2 Routing Configuration (if enabled) ==="
if [ "$V4_ROUTING_ENABLED" = "true" ]; then
    check_required "V2_ROUTING_API_KEY" "your-secure-api-key-here-change-this" "API key for V2 routing"
    check_required "V2_BASE_URL" "" "Base URL for V2 application"
    check_required "V4_BASE_URL" "" "Base URL for V4 application"
    
    # Check if SSL verification is enabled
    if [ "$V2_ROUTING_SSL_VERIFY" != "true" ]; then
        echo -e "${YELLOW}⚠ WARNING: V2_ROUTING_SSL_VERIFY should be 'true' in production${NC}"
        WARNINGS=$((WARNINGS + 1))
    fi
fi

echo ""
echo "=== Optional Features ==="
if [ "$RECAPTCHA_ENABLED" = "true" ]; then
    check_required "RECAPTCHA_SITE_KEY" "" "reCAPTCHA site key"
    check_required "RECAPTCHA_SECRET_KEY" "" "reCAPTCHA secret key"
fi

if [ "$GOOGLE_OAUTH_ENABLED" = "true" ]; then
    check_required "GOOGLE_OAUTH_CLIENT_ID" "" "Google OAuth client ID"
    check_required "GOOGLE_OAUTH_CLIENT_SECRET" "" "Google OAuth client secret"
    check_required "GOOGLE_OAUTH_REDIRECT_URI" "" "Google OAuth redirect URI"
fi

echo ""
echo "=========================================="
echo "Validation Summary"
echo "=========================================="
echo ""

if [ $ERRORS -gt 0 ]; then
    echo -e "${RED}✗ VALIDATION FAILED${NC}"
    echo -e "${RED}  Critical Errors: $ERRORS${NC}"
    echo -e "${YELLOW}  Warnings: $WARNINGS${NC}"
    echo ""
    echo "Fix all critical errors before deploying to production!"
    exit 1
elif [ $WARNINGS -gt 0 ]; then
    echo -e "${YELLOW}⚠ VALIDATION PASSED WITH WARNINGS${NC}"
    echo -e "${GREEN}  Critical Errors: 0${NC}"
    echo -e "${YELLOW}  Warnings: $WARNINGS${NC}"
    echo ""
    echo "All critical checks passed, but please review warnings."
    echo "Continue deployment? (y/N)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo "Deployment cancelled."
        exit 1
    fi
else
    echo -e "${GREEN}✓ VALIDATION PASSED${NC}"
    echo -e "${GREEN}  All critical checks passed!${NC}"
    echo -e "${GREEN}  No warnings found.${NC}"
    echo ""
    echo "Environment is ready for production deployment."
fi

exit 0
