# Multi-stage Dockerfile for PHP environments
# Supports both PHP 7.2 and PHP 8.3

# Stage 1: Common base with Ubuntu Jammy and shared packages
FROM ubuntu:jammy AS base-common

ARG BUILDER_UID=1000
ENV DEBIAN_FRONTEND=noninteractive

# Install common packages and add ondrej/php PPA
RUN apt update && \
    apt install -y --no-install-recommends \
        software-properties-common \
        ca-certificates \
        curl \
        zip \
        apache2 \
        sqlite3 && \
    apt clean && rm -rf /var/lib/apt/lists/*

RUN apt update && \
    apt install -y --no-install-recommends gnupg && \
    add-apt-repository ppa:ondrej/php -y && \
    apt update

# Apache base config
RUN a2enmod rewrite headers ssl && \
    echo "ServerName localhost" >> /etc/apache2/apache2.conf

# Create user with specified UID
RUN if id ${BUILDER_UID} >/dev/null 2>&1; then \
        userdel $(id -nu ${BUILDER_UID}) 2>/dev/null || true; \
    fi && \
    groupadd -g ${BUILDER_UID} appuser 2>/dev/null || true && \
    useradd -u ${BUILDER_UID} -g ${BUILDER_UID} -m -s /bin/bash appuser

# Set Apache to run as appuser
RUN sed -i "s/export APACHE_RUN_USER=www-data/export APACHE_RUN_USER=appuser/" /etc/apache2/envvars && \
    sed -i "s/export APACHE_RUN_GROUP=www-data/export APACHE_RUN_GROUP=appuser/" /etc/apache2/envvars

WORKDIR /var/www/html
EXPOSE 80 443

# Stage 2: PHP 7.2 specific image
FROM base-common AS php72

RUN apt update && \
    apt install -y --no-install-recommends \
        libapache2-mod-php7.2 \
        php7.2 php7.2-cli \
        php7.2-mbstring php7.2-xml \
        php7.2-mysql php7.2-intl \
        php7.2-zip php7.2-curl \
        php7.2-gd \
        php7.2-memcached php7.2-soap \
        php7.2-bcmath && \
    apt clean && rm -rf /var/lib/apt/lists/*

# Install Composer
RUN curl -sS https://getcomposer.org/installer | php -- --install-dir=/usr/local/bin --filename=composer

COPY php-trust-certs.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/php-trust-certs.sh

CMD ["sh", "-c", "/usr/local/bin/php-trust-certs.sh apache2ctl -D FOREGROUND"]

# Stage 3: PHP 8.3 specific image
FROM base-common AS php83

RUN apt install -y --no-install-recommends \
        libapache2-mod-php8.3 \
        php8.3 php8.3-cli \
        php8.3-mbstring php8.3-xml \
        php8.3-mysql php8.3-intl \
        php8.3-zip php8.3-curl \
        php8.3-gd php8.3-pgsql \
        php8.3-memcached php8.3-soap \
        php8.3-bcmath php8.3-redis \
        php8.3-sqlite3 && \
    apt clean && rm -rf /var/lib/apt/lists/*

# Install Composer
RUN curl -sS https://getcomposer.org/installer | php -- --install-dir=/usr/local/bin --filename=composer

COPY php-trust-certs.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/php-trust-certs.sh

CMD ["sh", "-c", "/usr/local/bin/php-trust-certs.sh apache2ctl -D FOREGROUND"]
