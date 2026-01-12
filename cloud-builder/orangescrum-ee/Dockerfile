# ==========================================
# OrangeScrum Cloud Edition - Full Stack Runtime
# ==========================================
# This Dockerfile creates a FrankenPHP-based runtime container
# with cron support for scheduled tasks.
#
# The FrankenPHP binary is a self-contained executable that includes:
# - PHP 8.3 interpreter with all required extensions
# - Caddy web server
# - Embedded OrangeScrum application code
# - All PHP dependencies (vendor directory)
# ==========================================

FROM alpine:latest

# ==========================================
# Install Runtime Dependencies
# ==========================================
# Install minimal tools for FrankenPHP runtime + cron support
RUN apk add --no-cache \
    bash \
    wget \
    postgresql-client \
    dcron \
    libcap && \
    # Create non-root user for security
    addgroup -g 1000 orangescrum && \
    adduser -D -u 1000 -G orangescrum orangescrum

WORKDIR /orangescrum-app

# ==========================================
# Copy FrankenPHP Static Binary
# ==========================================
# This self-contained binary includes PHP 8.3, Caddy, and the embedded app
COPY ./orangescrum-app/orangescrum-ee /orangescrum-app/orangescrum-ee
RUN chmod +x /orangescrum-app/orangescrum-ee && \
    chown orangescrum:orangescrum /orangescrum-app/orangescrum-ee

# ==========================================
# Copy Configuration Files
# ==========================================
COPY ./config /orangescrum-app/config
RUN chown -R orangescrum:orangescrum /orangescrum-app/config

# ==========================================
# Copy Entrypoint and Cron Setup Script
# ==========================================
COPY ./entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# ==========================================
# Setup Cron for Recurring Tasks
# ==========================================
# Copy cron configuration for FrankenPHP
COPY ./config/cron/recurring_task_cron_franken /etc/crontabs/root
RUN chmod 0644 /etc/crontabs/root

# ==========================================
# Create Persistent Data Directories
# ==========================================
# Minimal directories needed (cache in Redis, files in S3, sessions in Redis/DB)
RUN mkdir -p \
    /data/tmp \
    /data/logs && \
    chown -R orangescrum:orangescrum /data /orangescrum-app /entrypoint.sh

# ==========================================
# Security: Run as non-root user
# ==========================================
# Note: FrankenPHP needs to bind to port 80, so we use setcap instead of switching user here
# The entrypoint will drop privileges after binding
RUN setcap 'cap_net_bind_service=+ep' /orangescrum-app/orangescrum-ee

# Switch to non-root user
USER orangescrum

# ==========================================
# Expose HTTP Port
# ==========================================
EXPOSE 80

# ==========================================
# Container Startup
# ==========================================
ENTRYPOINT ["/entrypoint.sh"]
CMD ["/orangescrum-app/orangescrum-ee", "php-server", "-r", "webroot", "-l", "0.0.0.0:80"]
