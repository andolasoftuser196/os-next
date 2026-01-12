# ==========================================
# FrankenPHP Base Builder
# ==========================================
# This Dockerfile creates a base image containing a pre-compiled FrankenPHP
# static binary with PHP 8.3 and Caddy server, but WITHOUT any application code.
#
# Purpose: Build this ONCE and reuse it for fast app embedding builds
# Build time: ~20-30 minutes (one-time cost)
# Image name: orangescrum-cloud-base:latest
#
# What this produces:
# - Compiled PHP 8.3 with all extensions (statically linked)
# - Compiled Caddy server with modules (statically linked)
# - All source files and libraries needed for subsequent app embedding
# - NO standalone binary (removed to force app embedding)
#
# Rebuilding: Only rebuild when you need to:
# - Update PHP version
# - Add/remove PHP extensions
# - Update Caddy modules
# - Update Go version
# ==========================================

FROM dunglas/frankenphp:static-builder AS base-builder

# ==========================================
# Step 1: Clean Previous Build Artifacts
# ==========================================
# Remove any existing static-php-cli directory from previous builds
# This ensures a clean build environment and prevents conflicts
RUN rm -rf /go/src/app/dist/static-php-cli

# ==========================================
# Step 2: Install System Dependencies
# ==========================================
# Install packages needed for PHP compilation:
# - php84-iconv: Provides iconv library headers for PHP's iconv extension
#                (Alpine's default iconv has limitations that PHP requires)
RUN apk add --no-cache php84-iconv

# ==========================================
# Step 3: Install Go 1.25
# ==========================================
# FrankenPHP requires Go 1.25 for building the Caddy server integration
# The base image might have an older Go version, so we install the latest
ENV GOLANG_VERSION=1.25.0
ENV PATH="/usr/local/go/bin:${PATH}"

RUN wget https://dl.google.com/go/go${GOLANG_VERSION}.linux-amd64.tar.gz \
    && rm -rf /usr/local/go \
    && tar -C /usr/local -xzf go${GOLANG_VERSION}.linux-amd64.tar.gz \
    && rm go${GOLANG_VERSION}.linux-amd64.tar.gz \
    && go version

# ==========================================
# Step 4: Configure Build Environment
# ==========================================
# These environment variables control the FrankenPHP build process:
#
# NO_COMPRESS=1
#   Skip binary compression (faster builds, slightly larger binary)
#   Compression adds ~5-10 minutes to build time for minimal size savings
#
# PHP_VERSION=8.3
#   Target PHP version to compile
#   Must match the PHP version used in app-embed.Dockerfile (composer-helper stage)
#
# FRANKENPHP_VERSION=latest
#   Use the latest FrankenPHP code from the repository
#
# PHP_EXTENSIONS=...
#   Comma-separated list of PHP extensions to compile statically
#   Each extension is compiled into the binary (no dynamic loading)
#   
#   Extensions included:
#   - Core: bcmath, calendar, ctype, filter, tokenizer
#   - Database: pdo, pdo_pgsql, pdo_sqlite, pgsql, sqlite3
#   - Web: curl, dom, xml, xmlreader, xmlwriter, simplexml, soap
#   - Files: fileinfo, ftp, zip, zlib, zstd
#   - Images: exif, gd
#   - Security: openssl, sodium
#   - Text: iconv, intl, mbstring, tidy
#   - System: pcntl, posix, shmop, sockets, sysvmsg, sysvsem, sysvshm
#   - Performance: opcache
#   - Utilities: ldap, phar, readline, session
ENV NO_COMPRESS=1 \
    PHP_VERSION=8.3 \
    FRANKENPHP_VERSION=latest \
    PHP_EXTENSIONS=bcmath,calendar,ctype,curl,dom,exif,fileinfo,filter,ftp,gd,iconv,intl,ldap,mbstring,opcache,openssl,pcntl,pdo,pdo_pgsql,pdo_sqlite,pgsql,phar,posix,readline,redis,session,shmop,simplexml,soap,sockets,sodium,sqlite3,sysvmsg,sysvsem,sysvshm,tidy,tokenizer,xml,xmlreader,xmlwriter,zip,zlib,zstd

WORKDIR /go/src/app

# ==========================================
# Step 5: Build Static PHP + Caddy Server
# ==========================================
# This is the TIME-CONSUMING step (~20-30 minutes)
# The build-static.sh script will:
# 1. Download PHP 8.3 source code
# 2. Download and compile all specified PHP extensions
# 3. Statically link PHP with all extensions
# 4. Download and compile Caddy server with FrankenPHP module
# 5. Create a standalone binary with PHP + Caddy integrated
#
# Output location: dist/frankenphp-linux-x86_64
# Output size: ~338MB (includes all extensions and Caddy)
#
# Go Module Caching:
# - Uses Docker BuildKit cache mounts for /go/pkg/mod (Go module cache)
# - Uses cache mount for /root/.cache (HTTP cache for downloads)
# - Persists across builds, preventing redownload of Go packages
# - Speeds up subsequent builds significantly
#
# Why this is slow:
# - Compiling PHP from source with 50+ extensions
# - Static linking (no shared libraries)
# - Compiling Caddy and all its modules
# - Building the Go integration layer
RUN --mount=type=cache,target=/go/pkg/mod,sharing=locked \
    --mount=type=cache,target=/root/.cache,sharing=locked \
    ./build-static.sh

# ==========================================
# Step 6: Prepare for App Embedding
# ==========================================
# Remove the standalone binary to force app embedding in subsequent builds
# 
# Why remove the binary?
# - We don't want to use this binary directly (it has no app code)
# - Forces the app-embed.Dockerfile to embed the application
# - Keeps this image as a pure "base" for app builds
#
# What we keep (in dist/static-php-cli/):
# - Compiled PHP libraries and object files
# - Compiled Caddy modules
# - Build artifacts needed for fast re-linking with app code
# - Source files and headers
#
# These artifacts allow app-embed.Dockerfile to quickly embed the app
# without recompiling PHP or Caddy (~1-2 minutes instead of ~20-30 minutes)
RUN rm -f dist/frankenphp-linux-* && \
    echo "Base build completed (binary removed for app embedding)"
