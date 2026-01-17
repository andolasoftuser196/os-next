#!/bin/bash
# Package both Docker and Native deployments for distribution
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VERSION="${VERSION:-v26.1.1}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DIST_DIR="../dist/${TIMESTAMP}"

echo "=========================================="
echo "Package All Deployments for Distribution"
echo "=========================================="
echo "Version: $VERSION"
echo "Timestamp: $TIMESTAMP"
echo "Dist: $DIST_DIR"
echo ""

# Create dist directory upfront
mkdir -p "$DIST_DIR"

# Ensure deployment folders are built
if [ ! -d "../orangescrum-cloud-docker" ]; then
    echo "Building Docker deployment..."
    ./build-docker.sh
    echo ""
fi

if [ ! -d "../orangescrum-cloud-native" ]; then
    echo "Building Native deployment..."
    ./build-native.sh
    echo ""
fi

# Package Docker (pass timestamp to avoid creating new one)
echo "=========================================="
echo "Packaging Docker Deployment..."
echo "=========================================="
export TIMESTAMP
./dist-docker.sh

echo ""
echo "=========================================="
echo "Packaging Native Deployment..."
echo "=========================================="
./dist-native.sh

# Create combined manifest
echo ""
echo "Creating distribution summary..."

# Resolve absolute path
DIST_DIR_ABS="$(cd "$SCRIPT_DIR" && cd "$DIST_DIR" && pwd)"
cd "$DIST_DIR_ABS"

cat > "README.txt" << EOF
OrangeScrum FrankenPHP Distribution Package
===========================================

Build Date: $(date)
Version: $VERSION
Timestamp: $TIMESTAMP

This distribution contains both deployment options:

1. Docker Deployment (orangescrum-docker-*.tar.gz)
   - Containerized deployment with Docker Compose
   - Includes infrastructure services
   - Easiest to deploy and manage
   - Recommended for most users

2. Native Deployment (orangescrum-native-*.tar.gz)
   - Direct system execution
   - Better performance
   - Requires manual service setup
   - Ideal for production servers

Choose the deployment that best fits your needs.

For more information, see the .manifest.txt files and
DEPLOYMENT_INSTRUCTIONS.md in each package.

Quick Start
-----------

Docker:
  tar -xzf orangescrum-docker-*.tar.gz
  cd orangescrum-docker-*
  cp .env.example .env && nano .env
  docker-compose -f docker-compose.services.yml up -d
  docker-compose up -d

Native:
  tar -xzf orangescrum-native-*.tar.gz
  cd orangescrum-native-*
  cp .env.example .env && nano .env
  ./validate-env.sh
  ./run-native.sh

EOF

echo ""
echo "=========================================="
echo "[OK] Distribution packages created!"
echo "=========================================="
echo ""
echo "Location: $DIST_DIR_ABS"
echo ""
ls -lh "$DIST_DIR_ABS"
echo ""
echo "Distribution includes:"
echo "  - Docker deployment package (.tar.gz + .manifest.txt)"
echo "  - Native deployment package (.tar.gz + .manifest.txt)"
echo "  - README.txt (distribution overview)"
echo ""
