# ==========================================
# OrangeScrum App Embedding - Multi-Stage Build
# ==========================================
# This Dockerfile creates a FrankenPHP static binary with the OrangeScrum
# application embedded inside it. It uses a two-stage build process:
#
# Stage 1 (composer-helper): Generate PHP dependencies and autoloader
# Stage 2 (app-embedder): Embed the complete app into FrankenPHP binary
#
# This build is FAST (~1-2 minutes) because it reuses the pre-built
# frankenphp-base image which contains compiled PHP 8.3 and Caddy server.
# Only the application code is embedded in each build.
# ==========================================

# ==========================================
# Stage 1: Composer Helper
# Generate vendor directory and autoloader with PHP 8.3
# ==========================================
FROM php:8.3-alpine AS composer-helper

# ==========================================
# Install Composer and Build Dependencies
# ==========================================
# We need these tools to fetch and prepare PHP dependencies:
# - curl: Download Composer installer
# - git: Clone dependencies from Git repositories
# - unzip: Extract compressed dependency archives
RUN apk add --no-cache \
    curl \
    git \
    unzip && \
    curl -sS https://getcomposer.org/installer | php -- \
        --install-dir=/usr/local/bin \
        --filename=composer

WORKDIR /app

# ==========================================
# Copy Composer Configuration
# ==========================================
# Copy composer.json to define dependencies
# Note: We intentionally do NOT copy composer.lock to allow flexibility
# across different development environments and avoid lock file conflicts
COPY ./package/composer.json ./

# ==========================================
# Install PHP Dependencies
# ==========================================
# Install all required Composer packages
# Flags explained:
# --ignore-platform-req=*: Ignore all platform requirements (PHP version, extensions)
#                          This allows building with different PHP versions
# --no-dev: Skip development dependencies (PHPUnit, debug tools, etc.)
# --no-scripts: Don't run post-install scripts yet (we'll run them after copying full app)
# --no-interaction: Run non-interactively (for CI/CD compatibility)
RUN composer install \
    --ignore-platform-req=* \
    --no-dev \
    --no-scripts \
    --no-interaction

# ==========================================
# Copy Application Source Code
# ==========================================
# Copy the complete OrangeScrum application including:
# - PHP source code (src/, config/, plugins/, etc.)
# - Templates and views
# - Public assets (webroot/)
# - Configuration files
COPY ./package/ .

# ==========================================
# Generate Optimized Autoloader
# ==========================================
# CRITICAL STEP: Generate the Composer autoloader for PHP 8.3 runtime
#
# Why this matters:
# - The composer-helper stage uses PHP 8.3-alpine image
# - Without --ignore-platform-req=php, Composer would detect PHP 8.3
#   and generate platform_check.php requiring PHP >= 8.3
# - This flag ensures compatibility with the PHP 8.3 runtime
#
# Flags explained:
# --optimize: Generate optimized class maps for better performance
# --no-dev: Exclude dev dependencies from autoloader
# --ignore-platform-req=php: CRITICAL - Prevents PHP version checks in generated files
#                            Without this, autoloader would fail at runtime
RUN composer dump-autoload \
    --optimize \
    --no-dev \
    --ignore-platform-req=php

# ==========================================
# Run Post-Install Scripts
# ==========================================
# Execute Composer post-install scripts which typically:
# - Set correct file permissions on tmp/, logs/, cache/ directories
# - Generate configuration files
# - Prepare application for first run
RUN composer run-script post-install-cmd --no-interaction

# ==========================================
# Stage 2: App Embedding
# Embed application into FrankenPHP static binary
# ==========================================
# This stage takes the prepared application from Stage 1 and embeds it
# into a FrankenPHP static binary. The frankenphp-base image already
# contains pre-compiled PHP 8.3 and Caddy, so this is FAST.
FROM orangescrum-cloud-base:latest AS app-embedder

# ==========================================
# Copy Performance Configuration Files
# ==========================================
# Copy optimized Caddy configuration for serving static files efficiently
# and routing dynamic requests to PHP
# CRITICAL: Place in dist/app/ so it ends up at /app/Caddyfile when extracted
COPY ./Caddyfile /go/src/app/caddy/frankenphp/Caddyfile

# ==========================================
# Prepare Application Directory
# ==========================================
# FrankenPHP expects the application in dist/app/ directory
# The build-static.sh script will embed everything in this directory
WORKDIR /go/src/app/dist/app

# ==========================================
# Copy Complete Application
# ==========================================
# Copy the prepared application from composer-helper stage including:
# - PHP source code
# - vendor/ directory with all dependencies
# - Correctly generated autoloader for PHP 8.3
# - Configuration files
# - Public assets
COPY --from=composer-helper /app/ ./

# ==========================================
# Copy Custom PHP Configuration
# ==========================================
# Copy optimized php.ini to be embedded in the static binary
# 
# FrankenPHP's php-server.go checks for php.ini in the embedded app:
# if [ exists $EmbeddedAppPath/php.ini ] {
#     PHP_INI_SCAN_DIR += :$EmbeddedAppPath
# }
#
# This allows:
# - Static binary includes runtime PHP configuration
# - No separate config files needed at runtime
# - Environment variables can still override settings
# - Production-ready with optimized defaults
#
# Settings priority (highest to lowest):
# 1. PHP_* environment variables (docker-compose.yaml)
# 2. Embedded php.ini file (this file)
# 3. PHP compiled defaults
COPY ./php.ini ./php.ini

# ==========================================
# Build Static Binary with Embedded App
# ==========================================
# The build-static.sh script will:
# 1. Take the frankenphp-base (pre-compiled PHP 8.3 + Caddy)
# 2. Embed the application from dist/app/ directory
# 3. Link everything into a single static binary
# 4. Output: dist/frankenphp-linux-x86_64 (~338MB)
#
# This is FAST because it only embeds the application code.
# All the time-consuming compilation of PHP and Caddy was done
# once in the frankenphp-base image.
#
# Environment variable:
# EMBED=dist/app/ tells FrankenPHP which directory to embed
WORKDIR /go/src/app/

RUN EMBED=dist/app/ ./build-static.sh

