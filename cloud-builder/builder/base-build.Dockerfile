# ==========================================
# FrankenPHP Base Builder with PHP 8.3
# ==========================================
# This Dockerfile rebuilds FrankenPHP v1.11.1 with PHP 8.3 instead of 8.4
# to ensure compatibility with CakePHP 4.6 and OrangeScrum requirements.
#
# Purpose: Build FrankenPHP static binary with PHP 8.3
# Build time: ~20-30 minutes (one-time cost)
# Image name: orangescrum-cloud-base:latest
#
# What this produces:
# - Compiled PHP 8.3 with all extensions (statically linked)
# - Compiled Caddy server with modules (statically linked)
# - All build artifacts for fast app embedding
#
# Rebuilding: Only rebuild when upgrading FrankenPHP or changing PHP version
# ==========================================

FROM dunglas/frankenphp:static-builder-musl-1.11.1 AS base-builder

WORKDIR /go/src/app

# ==========================================
# Configure Build for PHP 8.3
# ==========================================
# Override the default PHP_VERSION (8.4) to build with PHP 8.3
# for CakePHP 4.6 compatibility
ARG NO_COMPRESS=1
ENV PHP_VERSION=8.3 \
    NO_COMPRESS=${NO_COMPRESS} \
    SPC_LIBC=musl \
    PHP_EXTENSIONS=bcmath,calendar,ctype,curl,dom,exif,fileinfo,filter,ftp,gd,iconv,intl,ldap,mbstring,opcache,openssl,pcntl,pdo,pdo_pgsql,pdo_sqlite,pgsql,phar,posix,readline,redis,session,shmop,simplexml,soap,sockets,sodium,sqlite3,sysvmsg,sysvsem,sysvshm,tidy,tokenizer,xml,xmlreader,xmlwriter,zip,zlib,zstd

RUN echo "Building FrankenPHP with PHP ${PHP_VERSION} and extensions: ${PHP_EXTENSIONS}"

# Add TEST_BASE to keep the built frankenphp binary when running base builds in test mode.
# Accepts build-arg override; default is 0 (false).
ARG TEST_BASE=0
ENV TEST_BASE=${TEST_BASE}

# ==========================================
# Build FrankenPHP with PHP 8.3
# ==========================================
# Build time: ~20-30 minutes (compiling from source)
# We set CI='' to prevent build-static.sh from deleting downloads/ directory
RUN rm -rf dist/ && CI='' NO_COMPRESS=1 ./build-static.sh

# ==========================================
# Prepare for App Embedding
# ==========================================
# Remove standalone binary but keep all build artifacts:
# - dist/static-php-cli/buildroot/ (compiled libraries) 
# - dist/static-php-cli/downloads/ (source archives - prevents re-download)
# - dist/static-php-cli/source/ (extracted sources)
# - dist/static-php-cli/spc (spc binary)
RUN if [ "${TEST_BASE}" = "1" ] || [ "${TEST_BASE}" = "true" ]; then \
            echo "TEST_BASE=${TEST_BASE}; keeping dist/frankenphp-linux-* for testing"; \
        else \
            rm -f dist/frankenphp-linux-*; \
        fi && \
        echo "Base build completed with PHP 8.3 (binary removed for app embedding)"
