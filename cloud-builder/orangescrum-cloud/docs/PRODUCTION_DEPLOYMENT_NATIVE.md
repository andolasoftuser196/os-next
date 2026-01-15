# Production Deployment Guide - Native FrankenPHP Binary Mode

## Overview

This guide covers deploying OrangeScrum using the native FrankenPHP binary (standalone mode without Docker). This approach offers:

✅ **Lower resource usage** - No Docker overhead  
✅ **Faster startup** - No containerization layer  
✅ **Simpler debugging** - Direct access to processes  
✅ **Native systemd integration** - Standard Linux service management

---

## Prerequisites

- Linux server (Ubuntu 20.04+, Debian 11+, RHEL 8+, or similar)
- PostgreSQL 13+ (external, managed database)
- Redis 6+ (external, for cache and queue)
- S3-compatible storage (AWS S3, DigitalOcean Spaces, MinIO)
- Domain name with SSL certificate
- Reverse proxy (nginx or Apache)
- Sudo/root access for system configuration

---

## Step 1: Prepare Server Environment

### 1.1 Create Application User

```bash
# Create dedicated user for OrangeScrum
sudo useradd -r -m -d /opt/orangescrum -s /bin/bash orangescrum

# Add to www-data group (for nginx/Apache integration)
sudo usermod -a -G www-data orangescrum
```

### 1.2 Install Dependencies

```bash
# PostgreSQL client (for migrations and health checks)
sudo apt update
sudo apt install -y postgresql-client redis-tools curl wget

# For Ubuntu/Debian
sudo apt install -y ca-certificates

# Verify installations
psql --version
redis-cli --version
```

### 1.3 Create Application Directory

```bash
# Create directories
sudo mkdir -p /opt/orangescrum
sudo mkdir -p /opt/orangescrum/logs
sudo mkdir -p /opt/orangescrum/backups
sudo mkdir -p /var/log/orangescrum

# Set permissions
sudo chown -R orangescrum:orangescrum /opt/orangescrum
sudo chown -R orangescrum:orangescrum /var/log/orangescrum
```

---

## Step 2: Deploy Application

### 2.1 Upload and Extract Package

```bash
# Upload package to server
scp orangescrum-frankenphp-v*.tar.gz user@server:/tmp/

# Switch to orangescrum user
sudo su - orangescrum

# Extract to application directory
cd /opt/orangescrum
tar -xzf /tmp/orangescrum-frankenphp-v*.tar.gz --strip-components=1

# Verify binary
ls -lh /opt/orangescrum/bin/orangescrum
# Should show executable with size ~100MB+

# Set executable permissions (should already be set)
chmod +x /opt/orangescrum/bin/orangescrum
```

### 2.2 Configure Environment

```bash
# Create .env file
cd /opt/orangescrum
cp .env.example .env
nano .env
```

**Production Configuration:**

```bash
# ============================================
# CRITICAL: Change These Values
# ============================================

# Generate with: php -r 'echo hash("sha256", bin2hex(random_bytes(32)));'
SECURITY_SALT=PASTE_GENERATED_VALUE_HERE

# Database (external PostgreSQL)
DB_HOST=your-postgres-server.example.com
DB_PORT=5432
DB_USERNAME=orangescrum
DB_PASSWORD=PASTE_STRONG_PASSWORD_HERE
DB_NAME=orangescrum

# Redis (external)
REDIS_HOST=your-redis-server.example.com
REDIS_PORT=6379
REDIS_PASSWORD=YOUR_REDIS_PASSWORD
REDIS_DATABASE=0
REDIS_TLS_ENABLED=false

# Production Settings
DEBUG=false
CACHE_ENGINE=redis
QUEUE_ENGINE=redis

# S3 Storage
STORAGE_ENDPOINT=https://s3.amazonaws.com
STORAGE_ACCESS_KEY=AKIAXXXXXXXXXXXXXXXX
STORAGE_SECRET_KEY=PASTE_SECRET_KEY_HERE
STORAGE_BUCKET=orangescrum-production-files
STORAGE_REGION=us-east-1
STORAGE_PATH_STYLE=false

# Email
EMAIL_TRANSPORT=sendgrid
EMAIL_API_KEY=SG.PASTE_API_KEY_HERE
FROM_EMAIL=noreply@yourdomain.com
NOTIFY_EMAIL=admin@yourdomain.com

# Application URL
FULL_BASE_URL=https://app.yourdomain.com

# Application Port
PORT=8080

# Sessions
SESSION_HANDLER=cache
SESSION_COOKIE_DOMAIN=.yourdomain.com

# Migrations (skip on restart after initial setup)
SKIP_MIGRATIONS=0  # Set to 1 after first successful deployment
```

### 2.3 Validate Configuration

```bash
# Run validation script
./validate-env.sh

# Should output: "✓ VALIDATION PASSED"
```

---

## Step 3: Set Up External Services

### 3.1 PostgreSQL Database

```bash
# Test connection
PGPASSWORD="your-password" psql -h your-postgres-server.example.com \
  -U orangescrum -d orangescrum -c "SELECT version();"

# Create database (if not exists)
# See PRODUCTION_DEPLOYMENT_DOCKER.md Step 3.1 for SQL commands
```

### 3.2 Redis Cache

```bash
# Test Redis connection
redis-cli -h your-redis-server.example.com -p 6379 -a YOUR_PASSWORD ping
# Should return: PONG
```

### 3.3 S3 Storage

```bash
# Test S3 access (using AWS CLI)
aws s3 ls s3://orangescrum-production-files/ --region us-east-1

# Or manually verify via web console
```

---

## Step 4: Initial Deployment and Migration

### 4.1 Run Database Migrations

```bash
# As orangescrum user
cd /opt/orangescrum

# Run first deployment (includes migrations)
# This will:
# 1. Extract embedded app to /tmp/frankenphp_*
# 2. Run database migrations
# 3. Start the server on port 8080
RUN_MIGRATIONS=true DAEMON=false ./run.sh
```

**Watch for:**
- ✓ App extracted and ready
- ✓ Main migrations completed successfully
- ✓ Application is ready!

Press Ctrl+C after verifying successful startup.

### 4.2 Disable Auto-Migration for Production

```bash
# Edit .env to skip migrations on restart
nano .env

# Change:
SKIP_MIGRATIONS=1
```

---

## Step 5: Configure systemd Service

### 5.1 Create systemd Service File

```bash
# Exit orangescrum user
exit

# Create service file as root
sudo nano /etc/systemd/system/orangescrum.service
```

**Service Configuration:**

```ini
[Unit]
Description=OrangeScrum FrankenPHP Application
Documentation=https://docs.orangescrum.com
After=network-online.target postgresql.service redis.service
Wants=network-online.target

[Service]
Type=simple
User=orangescrum
Group=orangescrum
WorkingDirectory=/opt/orangescrum

# Load environment variables from .env file
EnvironmentFile=/opt/orangescrum/.env

# Set PORT explicitly (systemd doesn't expand ${PORT} in ExecStart)
Environment="PORT=8080"
Environment="DAEMON=false"
Environment="RUN_MIGRATIONS=false"

# Start application
ExecStart=/opt/orangescrum/bin/orangescrum php-server -r webroot -l 127.0.0.1:8080

# Restart policy
Restart=on-failure
RestartSec=10s
StartLimitInterval=300
StartLimitBurst=5

# Resource limits
LimitNOFILE=65536
LimitNPROC=4096

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/orangescrum /var/log/orangescrum /tmp

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=orangescrum

[Install]
WantedBy=multi-user.target
```

### 5.2 Create Queue Worker Service (Optional but Recommended)

```bash
sudo nano /etc/systemd/system/orangescrum-queue.service
```

```ini
[Unit]
Description=OrangeScrum Queue Worker
Documentation=https://docs.orangescrum.com
After=network-online.target orangescrum.service redis.service
Wants=network-online.target

[Service]
Type=simple
User=orangescrum
Group=orangescrum
WorkingDirectory=/opt/orangescrum

# Load environment variables
EnvironmentFile=/opt/orangescrum/.env

# Environment overrides
Environment="QUEUE_WORKER=true"
Environment="WORKER_MAX_RUNTIME=1800"
Environment="WORKER_SLEEP=5"

# Start queue worker wrapper script
ExecStart=/opt/orangescrum/queue-worker.sh start

# Restart policy
Restart=on-failure
RestartSec=10s

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/orangescrum /var/log/orangescrum /tmp

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=orangescrum-queue

[Install]
WantedBy=multi-user.target
```

### 5.3 Enable and Start Services

```bash
# Reload systemd daemon
sudo systemctl daemon-reload

# Enable services to start on boot
sudo systemctl enable orangescrum
sudo systemctl enable orangescrum-queue

# Start services
sudo systemctl start orangescrum
sudo systemctl start orangescrum-queue

# Check status
sudo systemctl status orangescrum
sudo systemctl status orangescrum-queue

# View logs
sudo journalctl -u orangescrum -f
```

---

## Step 6: Configure Reverse Proxy (nginx)

### 6.1 Install nginx

```bash
sudo apt install -y nginx
```

### 6.2 Create nginx Configuration

```bash
sudo nano /etc/nginx/sites-available/orangescrum
```

```nginx
# Redirect HTTP to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name app.yourdomain.com;
    
    # ACME challenge for Let's Encrypt
    location /.well-known/acme-challenge/ {
        root /var/www/letsencrypt;
    }
    
    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name app.yourdomain.com;
    
    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/app.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/app.yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Security Headers
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    
    # Max upload size
    client_max_body_size 200M;
    client_body_buffer_size 128k;
    
    # Timeouts
    proxy_connect_timeout 60s;
    proxy_send_timeout 300s;
    proxy_read_timeout 300s;
    send_timeout 300s;
    
    # Logging
    access_log /var/log/nginx/orangescrum-access.log;
    error_log /var/log/nginx/orangescrum-error.log warn;
    
    # Rate limiting zones
    limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;
    limit_req_zone $binary_remote_addr zone=api:10m rate=30r/s;
    
    # Proxy to OrangeScrum application
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        
        # Preserve original request information
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port $server_port;
        
        # WebSocket support
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Buffering
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
        proxy_busy_buffers_size 8k;
    }
    
    # Rate limit authentication endpoints
    location ~ ^/(users/login|users/signup|users/forgot_password) {
        limit_req zone=login burst=10 nodelay;
        limit_req_status 429;
        
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Rate limit API endpoints
    location ~ ^/api/ {
        limit_req zone=api burst=50 nodelay;
        limit_req_status 429;
        
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Health check (no rate limit)
    location = /home/healthcheck {
        access_log off;
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
    }
    
    # Static file caching (if served by nginx)
    location ~* \.(jpg|jpeg|png|gif|ico|css|js|svg|woff|woff2|ttf|eot)$ {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

### 6.3 Enable Site and Test

```bash
# Create Let's Encrypt webroot
sudo mkdir -p /var/www/letsencrypt

# Enable site
sudo ln -s /etc/nginx/sites-available/orangescrum /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

---

## Step 7: Install SSL Certificate

### 7.1 Install Certbot

```bash
sudo apt install -y certbot python3-certbot-nginx
```

### 7.2 Obtain Certificate

```bash
# Stop nginx temporarily
sudo systemctl stop nginx

# Obtain certificate (standalone mode)
sudo certbot certonly --standalone -d app.yourdomain.com \
  --agree-tos --email admin@yourdomain.com

# Start nginx
sudo systemctl start nginx

# Test auto-renewal
sudo certbot renew --dry-run
```

### 7.3 Configure Auto-Renewal

```bash
# Certbot creates a systemd timer automatically
sudo systemctl list-timers | grep certbot

# Or add manual cron job (alternative)
sudo crontab -e

# Add (runs twice daily):
0 0,12 * * * certbot renew --quiet --post-hook "systemctl reload nginx"
```

---

## Step 8: Configure Firewall

```bash
# Enable UFW (if not already enabled)
sudo ufw enable

# Allow SSH
sudo ufw allow 22/tcp

# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Deny direct access to application port
sudo ufw deny 8080/tcp

# Check status
sudo ufw status

# Verify rules
sudo ufw status numbered
```

---

## Step 9: Set Up Cron Jobs

### 9.1 OrangeScrum Recurring Tasks

```bash
# Edit orangescrum user crontab
sudo su - orangescrum
crontab -e
```

**Add cron job:**

```bash
# OrangeScrum recurring tasks (every 30 minutes)
*/30 * * * * cd /opt/orangescrum && EXTRACTED_APP=$(find /tmp -maxdepth 1 -name "frankenphp_*" -type d | head -1) && [ -n "$EXTRACTED_APP" ] && cd "$EXTRACTED_APP" && /opt/orangescrum/bin/orangescrum php-cli bin/cake.php recurring_task >> /var/log/orangescrum/cron.log 2>&1
```

**Note:** The cron job finds the extracted FrankenPHP app directory dynamically.

### 9.2 Verify Cron Execution

```bash
# Wait 30 minutes, then check log
tail -f /var/log/orangescrum/cron.log

# Should show recurring task execution logs
```

---

## Step 10: Set Up Monitoring and Backup

### 10.1 Health Check Monitoring

```bash
# Create monitoring script
sudo nano /usr/local/bin/orangescrum-health-check.sh
```

```bash
#!/bin/bash
# OrangeScrum Health Check Script

HEALTH_URL="https://app.yourdomain.com/home/healthcheck"
ALERT_EMAIL="admin@yourdomain.com"

# Check health endpoint
if ! curl -fsS -m 10 --retry 3 "$HEALTH_URL" > /dev/null 2>&1; then
    echo "OrangeScrum health check failed at $(date)" | \
        mail -s "ALERT: OrangeScrum Application Down" "$ALERT_EMAIL"
    exit 1
fi

exit 0
```

```bash
sudo chmod +x /usr/local/bin/orangescrum-health-check.sh

# Add to root crontab (every 5 minutes)
sudo crontab -e
*/5 * * * * /usr/local/bin/orangescrum-health-check.sh
```

### 10.2 Database Backup

```bash
# Create backup script
sudo nano /opt/orangescrum/backup-database.sh
```

```bash
#!/bin/bash
# Database Backup Script

# Load environment
set -a
source /opt/orangescrum/.env
set +a

BACKUP_DIR="/opt/orangescrum/backups"
DATE=$(date +%Y%m%d-%H%M%S)
RETENTION_DAYS=30

mkdir -p "$BACKUP_DIR"

# Backup PostgreSQL
PGPASSWORD="$DB_PASSWORD" pg_dump \
  -h "$DB_HOST" \
  -p "$DB_PORT" \
  -U "$DB_USERNAME" \
  -d "$DB_NAME" \
  -F c \
  -f "$BACKUP_DIR/orangescrum-db-$DATE.dump"

# Compress
gzip "$BACKUP_DIR/orangescrum-db-$DATE.dump"

# Keep only last 30 days
find "$BACKUP_DIR" -name "orangescrum-db-*.dump.gz" -mtime +$RETENTION_DAYS -delete

echo "Backup completed: orangescrum-db-$DATE.dump.gz"

# Optional: Upload to S3
# aws s3 cp "$BACKUP_DIR/orangescrum-db-$DATE.dump.gz" \
#   s3://your-backup-bucket/database-backups/
```

```bash
sudo chmod +x /opt/orangescrum/backup-database.sh
sudo chown orangescrum:orangescrum /opt/orangescrum/backup-database.sh

# Add to orangescrum user crontab (daily at 2 AM)
sudo su - orangescrum
crontab -e
0 2 * * * /opt/orangescrum/backup-database.sh >> /var/log/orangescrum/backup.log 2>&1
```

---

## Step 11: Log Management

### 11.1 Configure logrotate

```bash
sudo nano /etc/logrotate.d/orangescrum
```

```
/var/log/orangescrum/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 orangescrum orangescrum
    sharedscripts
    postrotate
        systemctl reload orangescrum > /dev/null 2>&1 || true
    endscript
}

/var/log/nginx/orangescrum-*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 www-data adm
    sharedscripts
    postrotate
        systemctl reload nginx > /dev/null 2>&1 || true
    endscript
}
```

```bash
# Test logrotate configuration
sudo logrotate -d /etc/logrotate.d/orangescrum
```

---

## Step 12: Post-Deployment Verification

### 12.1 Service Status Checks

```bash
# Check application service
sudo systemctl status orangescrum

# Check queue worker
sudo systemctl status orangescrum-queue

# Check nginx
sudo systemctl status nginx

# Check if application is listening
sudo ss -tulpn | grep :8080

# Check if nginx is listening
sudo ss -tulpn | grep :443
```

### 12.2 Application Tests

```bash
# 1. Health check
curl -I https://app.yourdomain.com/home/healthcheck
# Should return: HTTP/2 200

# 2. Test SSL certificate
openssl s_client -connect app.yourdomain.com:443 -servername app.yourdomain.com < /dev/null

# 3. Test application login (browser)
# Open: https://app.yourdomain.com

# 4. Check application logs
sudo journalctl -u orangescrum -n 50

# 5. Check queue worker logs
sudo journalctl -u orangescrum-queue -n 50

# 6. Check cron execution
tail -f /var/log/orangescrum/cron.log

# 7. Test file upload
# Login → Create project → Upload file → Verify in S3

# 8. Test email
# Login → Test notification

# 9. Check database connection
sudo su - orangescrum
PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -U "$DB_USERNAME" -d "$DB_NAME" -c "SELECT COUNT(*) FROM users;"

# 10. Check Redis connection
redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" -a "$REDIS_PASSWORD" ping
```

---

## Maintenance and Operations

### View Logs

```bash
# Application logs (systemd journal)
sudo journalctl -u orangescrum -f

# Queue worker logs
sudo journalctl -u orangescrum-queue -f

# nginx access logs
sudo tail -f /var/log/nginx/orangescrum-access.log

# nginx error logs
sudo tail -f /var/log/nginx/orangescrum-error.log

# Cron logs
sudo tail -f /var/log/orangescrum/cron.log

# All orangescrum logs today
sudo journalctl -u orangescrum --since today
```

### Restart Services

```bash
# Restart application
sudo systemctl restart orangescrum

# Restart queue worker
sudo systemctl restart orangescrum-queue

# Restart nginx
sudo systemctl restart nginx

# Graceful reload nginx (no downtime)
sudo systemctl reload nginx
```

### Update Application

```bash
# 1. Download new package
cd /tmp
wget https://yourserver.com/orangescrum-frankenphp-v26.1.2.tar.gz

# 2. Stop services
sudo systemctl stop orangescrum-queue
sudo systemctl stop orangescrum

# 3. Backup current version
sudo cp -a /opt/orangescrum /opt/orangescrum.backup-$(date +%Y%m%d)

# 4. Extract new version (as orangescrum user)
sudo su - orangescrum
cd /opt/orangescrum
tar -xzf /tmp/orangescrum-frankenphp-v26.1.2.tar.gz --strip-components=1

# Keep existing .env file (don't overwrite)
# Binary will be replaced with new version

# 5. Run migrations if needed
# Edit .env: SKIP_MIGRATIONS=0
# Or run manually:
# ./run.sh  # Press Ctrl+C after migration

# 6. Restore SKIP_MIGRATIONS=1 in .env

# 7. Start services
exit  # Exit orangescrum user
sudo systemctl start orangescrum
sudo systemctl start orangescrum-queue

# 8. Verify
sudo systemctl status orangescrum
curl -I https://app.yourdomain.com/home/healthcheck
```

---

## Troubleshooting

### Application Won't Start

```bash
# Check service status
sudo systemctl status orangescrum

# Check detailed logs
sudo journalctl -u orangescrum -n 100 --no-pager

# Check if binary exists
ls -lh /opt/orangescrum/bin/orangescrum

# Check if port is already in use
sudo lsof -i :8080

# Test manually as orangescrum user
sudo su - orangescrum
cd /opt/orangescrum
DAEMON=false ./run.sh
# Watch for errors, then Ctrl+C
```

### Database Connection Issues

```bash
# Test connection
sudo su - orangescrum
PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -U "$DB_USERNAME" -d "$DB_NAME"

# Check firewall rules on database server
# Check if database allows connections from application server IP
```

### Redis Connection Issues

```bash
# Test Redis
redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" -a "$REDIS_PASSWORD" ping

# Check if Redis allows connections from application server IP
# Check Redis firewall rules
```

### High CPU/Memory Usage

```bash
# Check resource usage
top -u orangescrum

# Check FrankenPHP process
ps aux | grep orangescrum

# Check logs for errors
sudo journalctl -u orangescrum -n 100

# Adjust PHP memory limit in .env
# PHP_MEMORY_LIMIT=2048M
```

### SSL Certificate Issues

```bash
# Check certificate validity
sudo certbot certificates

# Renew manually
sudo certbot renew

# Check nginx SSL configuration
sudo nginx -t
```

---

## Security Hardening

### 1. AppArmor/SELinux Profile

```bash
# Enable AppArmor (Ubuntu/Debian)
sudo aa-enforce /etc/apparmor.d/usr.bin.orangescrum
```

### 2. Fail2Ban for Brute Force Protection

```bash
# Install fail2ban
sudo apt install -y fail2ban

# Configure jail for nginx
sudo nano /etc/fail2ban/jail.d/orangescrum.conf
```

```ini
[orangescrum-auth]
enabled = true
port = http,https
filter = orangescrum-auth
logpath = /var/log/nginx/orangescrum-access.log
maxretry = 5
bantime = 3600
findtime = 600
```

### 3. Regular Security Updates

```bash
# System updates (monthly)
sudo apt update && sudo apt upgrade -y

# Application updates (as released)
# See "Update Application" section above
```

---

## Performance Tuning

### nginx Worker Processes

```bash
# Edit nginx.conf
sudo nano /etc/nginx/nginx.conf

# Set based on CPU cores
worker_processes auto;
worker_connections 4096;
```

### FrankenPHP Performance

```bash
# Edit .env for higher performance
PHP_MEMORY_LIMIT=2048M
PHP_MAX_EXECUTION_TIME=300

# Consider adding more app instances behind load balancer
```

---

## Disaster Recovery

### Restore from Backup

```bash
# 1. Stop application
sudo systemctl stop orangescrum-queue
sudo systemctl stop orangescrum

# 2. Restore database
cd /opt/orangescrum/backups
gunzip orangescrum-db-20260110-020000.dump.gz

PGPASSWORD="$DB_PASSWORD" pg_restore \
  -h "$DB_HOST" \
  -U "$DB_USERNAME" \
  -d "$DB_NAME" \
  -c \ # Clean (drop) database objects before recreating
  orangescrum-db-20260110-020000.dump

# 3. Start application
sudo systemctl start orangescrum
sudo systemctl start orangescrum-queue

# 4. Verify
curl https://app.yourdomain.com/home/healthcheck
```

---

## Support

- **Documentation:** `/opt/orangescrum/docs/`
- **Logs:** `/var/log/orangescrum/` and `sudo journalctl -u orangescrum`
- **Health Check:** `curl https://app.yourdomain.com/home/healthcheck`
- **Service Status:** `sudo systemctl status orangescrum`
