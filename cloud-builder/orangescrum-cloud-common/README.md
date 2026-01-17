# OrangeScrum Cloud - Common Files

This directory contains **shared files** used by both Docker and Native deployments.

## Directory Structure

```
orangescrum-cloud-common/
├── config/                      # Configuration file templates
│   ├── cache_*.example.php     # Cache configuration examples
│   ├── storage.example.php     # S3 storage configuration
│   ├── smtp.example.php        # Email configuration
│   ├── queue.example.php       # Queue configuration
│   └── ...                     # Other config templates
├── docs/                        # Shared documentation
│   ├── PRODUCTION_DEPLOYMENT_DOCKER.md
│   ├── PRODUCTION_DEPLOYMENT_NATIVE.md
│   ├── PRODUCTION_READINESS_SUMMARY.md
│   └── ...
├── helpers/                     # Shared helper scripts
│   ├── cake.sh                 # CakePHP CLI wrapper
│   ├── queue-worker.sh         # Queue worker wrapper
│   └── validate-env.sh         # Environment validator
├── orangescrum-app/            # FrankenPHP binary location (built)
│   └── osv4-prod               # Static binary with embedded app
├── .env.example                # Base environment template
├── .env.full.example           # Complete configuration reference
└── CONFIGS.md                  # Configuration documentation
```

## Purpose

These files are the **source of truth** for both deployments. They are copied by the build scripts:

- **orangescrum-cloud-docker/build.sh** → Creates Docker deployment package
- **orangescrum-cloud-native/build.sh** → Creates Native deployment package

## Note on Deployment

This folder contains source files only. Use the deployment packages instead:

- **dist-docker/** - Docker deployment package
- **dist-native/** - Native deployment package

## Building Deployments

```bash
# Build FrankenPHP binary and create deployment packages
# From the cloud-builder directory:
python build.py

# This will:
# 1. Build FrankenPHP binary → orangescrum-cloud-common/orangescrum-app/osv4-prod
# 2. Run Docker build → dist-docker/
# 3. Run Native build → dist-native/
```

## Making Changes

To update configuration or documentation:

1. Edit files in this folder
2. Rebuild deployment packages:
   ```bash
   # Rebuild Docker package
   cd ../orangescrum-cloud-docker && ./build.sh
   
   # Rebuild Native package
   cd ../orangescrum-cloud-native && ./build.sh
   ```

## FrankenPHP Binary

The FrankenPHP static binary (`orangescrum-app/osv4-prod`) is built by `build.py` and contains:

- PHP 8.3 interpreter
- Caddy web server
- Full OrangeScrum V4 application
- All PHP dependencies (vendor/)

Both Docker and Native deployments use the same binary.
