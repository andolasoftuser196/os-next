# OrangeScrum Cloud - Native Deployment Source

This directory contains **source files** for Native (non-Docker) deployment.

## Directory Structure

```
orangescrum-cloud-native/
+-- run.sh                       # Start application
+-- run.sh                       # Alternative runner
+-- package.sh                   # Package for distribution
+-- caddy.sh                     # Caddy wrapper (if exists)
+-- .env.example                 # Native environment template
+-- systemd/                     # systemd service files
|   +-- orangescrum.service      # Main application service
|   +-- orangescrum-queue.service # Queue worker service
+-- build.sh                     # Build deployment package
+-- README.md                    # This file
```

## Purpose

This folder contains Native deployment-specific files. The `build.sh` script combines these files with common files to create a deployment-ready package in `../dist-native/`.

## Building Deployment Package

```bash
# Build deployment package manually
./build.sh

# Output: ../dist-native/
```

Or use the main build system:

```bash
# Build everything (binary + deployments)
python build.py

# This will automatically run build.sh
```

## Build Output

The `build.sh` script creates a deployment package by combining:

**From this folder (Native-specific):**
- `run.sh` - Application launcher
- `run.sh` - Alternative launcher
- `package.sh` - Distribution packager
- `systemd/` - systemd service definitions
- `.env.example` - Environment template

**From `../orangescrum-cloud-common/` (shared):**
- `config/` - Configuration templates
- `docs/` - Documentation
- `helpers/` - Helper scripts
- `orangescrum-app/osv4-prod` - FrankenPHP binary (copied to `bin/orangescrum`)

**Output:** `../dist-native/` - Complete, ready-to-deploy package

## Deployment

The built package in `dist-native/` can be deployed immediately:

```bash
cd ../dist-native
cp .env.example .env
nano .env  # Configure settings
./helpers/validate-env.sh
./run.sh  # Development
# OR
sudo cp systemd/*.service /etc/systemd/system/
sudo systemctl enable orangescrum
sudo systemctl start orangescrum  # Production
```

See `../dist-native/README.md` and `../orangescrum-cloud-common/docs/PRODUCTION_DEPLOYMENT_NATIVE.md` for details.

## Development

To modify Native deployment:

1. Edit files in this folder
2. Rebuild: `./build.sh`
3. Test: `cd ../dist-native && ./run.sh`

## Production Configuration

- systemd service integration
- Dedicated queue worker service
- Security validation on startup
- External database/cache/storage integration
- Reduced resource overhead (no container layer)
- Direct systemd logging integration
- Native service management capabilities

## Binary Location

In the deployment package, the binary is renamed:
- Source: `orangescrum-cloud-common/orangescrum-app/osv4-prod`
- Deployed as: `bin/orangescrum` (and `bin/osv4-prod` for compatibility)
