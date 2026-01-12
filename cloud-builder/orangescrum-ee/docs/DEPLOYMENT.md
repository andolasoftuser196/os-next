# OrangeScrum FrankenPHP - Deployment Guide

## Quick Start

```bash
# 1. Extract package
tar -xzf orangescrum-frankenphp-v26.1.1.tar.gz
cd orangescrum-frankenphp-v26.1.1/

# 2. Create environment file
cp .env.example .env
nano .env

# 3. Configure required variables (see below)

# 4. Run application
./run.sh

# Access: http://localhost:8080
```

---

## Required Configuration

Edit `.env` file and configure these required variables:

### Database (PostgreSQL)

```bash
DB_HOST=localhost           # PostgreSQL server address
DB_PORT=5432               # PostgreSQL port
DB_USERNAME=orangescrum    # Database user
DB_PASSWORD=CHANGE_ME      # Database password (REQUIRED)
DB_NAME=orangescrum        # Database name
```

**Database Setup:**

```sql
CREATE DATABASE orangescrum;
CREATE USER orangescrum WITH PASSWORD 'your-secure-password';
GRANT ALL PRIVILEGES ON DATABASE orangescrum TO orangescrum;
```

### Redis Cache

```bash
REDIS_HOST=localhost       # Redis server address
REDIS_PORT=6379           # Redis port
REDIS_PASSWORD=           # Redis password (if required)
REDIS_DATABASE=0          # Redis database number
```

### Security

```bash
# Generate with: openssl rand -base64 32
SECURITY_SALT=GENERATE_WITH_openssl_rand_-base64_32

DEBUG=false               # ALWAYS false in production
```

---

## Optional Configuration

### Application URL

```bash
# Set for production deployments behind proxy/load balancer
FULL_BASE_URL=https://app.example.com
```

### Email (SendGrid)

```bash
EMAIL_TRANSPORT=sendgrid
EMAIL_API_KEY=SG.xxxxx
FROM_EMAIL=noreply@example.com
```

**OR SMTP:**

```bash
EMAIL_TRANSPORT=smtp
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=user@example.com
SMTP_PASSWORD=your-password
SMTP_TLS=true
FROM_EMAIL=noreply@example.com
```

### S3 Storage (for file uploads)

```bash
STORAGE_ENDPOINT=https://s3.amazonaws.com
STORAGE_ACCESS_KEY=AKIAXXXXXXXX
STORAGE_SECRET_KEY=xxxxx
STORAGE_BUCKET=orangescrum-files
STORAGE_REGION=us-east-1
STORAGE_PATH_STYLE=false  # true for MinIO, false for AWS S3
```

### Sessions

```bash
SESSION_HANDLER=cache              # Use Redis for sessions (recommended)
SESSION_COOKIE_DOMAIN=             # Optional: .example.com for subdomains
```

### Google reCAPTCHA (optional)

```bash
RECAPTCHA_ENABLED=true
RECAPTCHA_SITE_KEY=6Lxxxxx
RECAPTCHA_SECRET_KEY=6Lxxxxx
RECAPTCHA_VERSION=v2              # v2 or v3
```

### Google OAuth (optional)

```bash
GOOGLE_OAUTH_ENABLED=true
GOOGLE_OAUTH_CLIENT_ID=xxxxx.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=GOCSPX-xxxxx
GOOGLE_OAUTH_REDIRECT_URI=https://app.example.com/oauth/google/callback
```

---

## Production Deployment

### systemd Service

Create `/etc/systemd/system/orangescrum.service`:

```ini
[Unit]
Description=OrangeScrum FrankenPHP Application
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/orangescrum
EnvironmentFile=/opt/orangescrum/.env
ExecStart=/opt/orangescrum/bin/orangescrum php-server -r webroot -l 0.0.0.0:8080
Restart=always
RestartSec=10

# Security
NoNewPrivileges=true
PrivateTmp=true
ReadWritePaths=/tmp

[Install]
WantedBy=multi-user.target
```

**Enable and start:**

```bash
sudo systemctl daemon-reload
sudo systemctl enable orangescrum
sudo systemctl start orangescrum
sudo systemctl status orangescrum
```

**View logs:**

```bash
sudo journalctl -u orangescrum -f
```

### Apache Reverse Proxy

Create `/etc/apache2/sites-available/orangescrum.conf`:

```apache
<VirtualHost *:80>
    ServerName app.example.com
    
    # Redirect to HTTPS
    Redirect permanent / https://app.example.com/
</VirtualHost>

<VirtualHost *:443>
    ServerName app.example.com
    
    SSLEngine On
    SSLCertificateFile /etc/ssl/certs/your-cert.crt
    SSLCertificateKeyFile /etc/ssl/private/your-key.key
    
    ProxyPreserveHost On
    ProxyPass / http://127.0.0.1:8080/
    ProxyPassReverse / http://127.0.0.1:8080/
    
    RequestHeader set X-Forwarded-Proto "https"
    RequestHeader set X-Forwarded-SSL "on"
    
    ErrorLog ${APACHE_LOG_DIR}/orangescrum-error.log
    CustomLog ${APACHE_LOG_DIR}/orangescrum-access.log combined
</VirtualHost>
```

**Enable:**

```bash
sudo a2enmod proxy proxy_http ssl headers
sudo a2ensite orangescrum
sudo apachectl configtest
sudo systemctl reload apache2
```

### Nginx Reverse Proxy

Create `/etc/nginx/sites-available/orangescrum`:

```nginx
# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name app.example.com;
    return 301 https://$server_name$request_uri;
}

# HTTPS
server {
    listen 443 ssl http2;
    server_name app.example.com;
    
    ssl_certificate /etc/ssl/certs/your-cert.crt;
    ssl_certificate_key /etc/ssl/private/your-key.key;
    
    # SSL Configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # Proxy to FrankenPHP
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-SSL on;
    }
    
    # Logging
    access_log /var/log/nginx/orangescrum-access.log;
    error_log /var/log/nginx/orangescrum-error.log;
}
```

**Enable:**

```bash
sudo ln -s /etc/nginx/sites-available/orangescrum /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## Port Configuration

### Default Port (8080)

```bash
./run.sh
# Listens on: 0.0.0.0:8080
```

### Custom Port

```bash
PORT=9000 ./run.sh
# Listens on: 0.0.0.0:9000
```

Or edit `.env`:

```bash
APP_PORT=9000
```

---

## Database Migrations

### Automatic (default)

Migrations run automatically on first start via `./run.sh`

### Manual

```bash
# Skip auto-migration
RUN_MIGRATIONS=false ./run.sh

# Run migrations manually
./bin/orangescrum php-cli bin/cake.php migrations migrate
```

### Skip Migrations (production)

Add to `.env`:

```bash
SKIP_MIGRATIONS=1
```

---

## Health Check

```bash
curl http://localhost:8080/home/healthcheck
```

**Expected response:**

```json
{
    "status": "healthy",
    "checks": {
        "application": "ok",
        "database": "ok",
        "cache": "ok"
    }
}
```

---

## Logs

### Find Application Directory

```bash
find /tmp -maxdepth 1 -name "frankenphp_*" -type d
```

### View Logs

```bash
# Error log
tail -f /tmp/frankenphp_*/logs/error.log

# Debug log
tail -f /tmp/frankenphp_*/logs/debug.log

# Systemd logs
journalctl -u orangescrum -f
```

---

## Troubleshooting

### Connection Issues

**Database:**

```bash
# Test connection
PGPASSWORD=your-password psql -h localhost -U orangescrum -d orangescrum -c "SELECT 1"
```

**Redis:**

```bash
# Test connection
redis-cli -h localhost -p 6379 PING
```

### Port Already in Use

```bash
# Find what's using port 8080
sudo lsof -i :8080

# Use different port
PORT=9000 ./run.sh
```

### Binary Won't Start

```bash
# Check permissions
chmod +x bin/orangescrum

# Check architecture
file bin/orangescrum
# Should show: ELF 64-bit LSB executable, x86-64

# Test PHP version
./bin/orangescrum php-cli -v
```

### Application Errors

```bash
# Enable debug mode temporarily
DEBUG=true ./run.sh

# Check error logs
tail -50 /tmp/frankenphp_*/logs/error.log

# Check system logs
journalctl -u orangescrum --since "5 minutes ago"
```

---

## Security Checklist

- [ ] Set strong `DB_PASSWORD`
- [ ] Generate random `SECURITY_SALT` with `openssl rand -base64 32`
- [ ] Set `DEBUG=false` in production
- [ ] Use HTTPS only (`FULL_BASE_URL=https://...`)
- [ ] Set `REDIS_PASSWORD` if Redis is network-accessible
- [ ] Run as non-root user (www-data or dedicated user)
- [ ] Enable firewall (only ports 80/443 exposed)
- [ ] Use SSL certificates from trusted CA
- [ ] Restrict database access (PostgreSQL pg_hba.conf)
- [ ] Regular security updates (rebuild binary periodically)

---

## Updates

### Update Binary

```bash
# 1. Stop service
sudo systemctl stop orangescrum

# 2. Backup current binary
cp /opt/orangescrum/bin/orangescrum /opt/orangescrum/bin/orangescrum.backup

# 3. Extract new package
tar -xzf orangescrum-frankenphp-vXX.tar.gz

# 4. Copy new binary
cp orangescrum-frankenphp-vXX/bin/orangescrum /opt/orangescrum/bin/

# 5. Restart service
sudo systemctl start orangescrum
```

### Run Migrations After Update

```bash
./bin/orangescrum php-cli bin/cake.php migrations migrate
```

---

## Support

- **Health Check:** <http://localhost:8080/home/healthcheck>
- **Logs:** `/tmp/frankenphp_*/logs/`
- **Documentation:** See ENVIRONMENT_CONFIGURATION.md for advanced configuration

---

## System Requirements

- **OS:** Linux x86_64 (Ubuntu 20.04+, Debian 11+, RHEL 8+)
- **PostgreSQL:** 12+ (local or remote)
- **Redis:** 6+ (local or remote)
- **Memory:** 2GB minimum, 4GB+ recommended
- **Disk:** 1GB for application + database storage
- **Network:** Port 8080 available (or custom port)

**No PHP installation required** - Binary is self-contained with PHP 8.3.29 + Caddy web server.
