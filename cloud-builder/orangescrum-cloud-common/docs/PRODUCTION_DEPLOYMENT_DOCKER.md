# Production Deployment Guide - Docker Mode

## Prerequisites

- Docker Engine 20.10+ and Docker Compose 2.0+
- PostgreSQL 13+ (external, managed database)
- Redis 6+ (external, for cache and queue)
- S3-compatible storage (AWS S3, DigitalOcean Spaces, MinIO)
- Domain name with SSL certificate
- Reverse proxy (nginx, Apache, or Caddy)

---

## Step 1: Prepare Production Environment

### 1.1 Install Docker

```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
newgrp docker

# Verify installation
docker --version
docker compose version
```

### 1.2 Create Application Directory

```bash
sudo mkdir -p /opt/application
sudo chown $USER:$USER /opt/application
cd /opt/application
```

### 1.3 Extract Deployment Package

```bash
# Upload package to server
scp orangescrum-frankenphp-v*.tar.gz user@server:/opt/application/

# Extract
cd /opt/application
tar -xzf orangescrum-frankenphp-v*.tar.gz
cd orangescrum-frankenphp-v*/
```

---

## Step 2: Configure Environment

### 2.1 Create .env File

```bash
cp .env.example .env
nano .env
```

### 2.2 Configure Required Variables

```bash
# ============================================
# Critical: Change These Values
# ============================================

# Generate with: openssl rand -base64 32
SECURITY_SALT=PASTE_GENERATED_VALUE_HERE

# Database (external PostgreSQL)
DB_HOST=<db-host>
DB_PORT=5432
DB_USERNAME=orangescrum
DB_PASSWORD=PASTE_STRONG_PASSWORD_HERE  # Generate with: openssl rand -base64 24
DB_NAME=orangescrum

# Redis (external)
REDIS_HOST=<redis-host>
REDIS_PORT=6379
REDIS_PASSWORD=YOUR_REDIS_PASSWORD  # If authentication enabled
REDIS_TLS_ENABLED=false  # Set to true for AWS ElastiCache with encryption

# Production Settings
DEBUG=false
CACHE_ENGINE=redis
QUEUE_ENGINE=redis

# S3 Storage (REQUIRED for file uploads)
STORAGE_ENDPOINT=https://s3.amazonaws.com
STORAGE_ACCESS_KEY=AKIAXXXXXXXXXXXXXXXX
STORAGE_SECRET_KEY=PASTE_SECRET_KEY_HERE
STORAGE_BUCKET=orangescrum-production-files
STORAGE_REGION=us-east-1
STORAGE_PATH_STYLE=false

# Email (SendGrid recommended)
EMAIL_TRANSPORT=sendgrid
EMAIL_API_KEY=SG.PASTE_API_KEY_HERE
FROM_EMAIL=noreply@<your-domain>
NOTIFY_EMAIL=admin@<your-domain>

# Application URL
FULL_BASE_URL=https://app.<your-domain>

# Application Port Binding
APP_BIND_IP=127.0.0.1  # Localhost only (behind reverse proxy)
APP_PORT=8080

# Sessions
SESSION_HANDLER=cache  # Use Redis for sessions
SESSION_COOKIE_DOMAIN=.<your-domain>  # For subdomain sharing

# ============================================
# Optional: Google reCAPTCHA (Recommended)
# ============================================
RECAPTCHA_ENABLED=true
RECAPTCHA_SITE_KEY=6LeXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
RECAPTCHA_SECRET_KEY=6LeXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
RECAPTCHA_VERSION=v3
RECAPTCHA_MIN_SCORE=0.5

# ============================================
# Optional: Google OAuth
# ============================================
GOOGLE_OAUTH_ENABLED=true
GOOGLE_OAUTH_CLIENT_ID=XXXXX.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=GOCSPX-XXXXX
GOOGLE_OAUTH_REDIRECT_URI=https://app.<your-domain>/oauth/google/callback

# ============================================
# Production Optimizations
# ============================================
SKIP_MIGRATIONS=1  # Skip migrations on every restart (run manually)
PHP_MEMORY_LIMIT=1024M
PHP_MAX_EXECUTION_TIME=300
```

### 2.3 Validate Configuration

```bash
# Run validation script
./validate-env.sh

# Should output: "[OK] VALIDATION PASSED"
# Fix any critical errors before proceeding
```

---

## Step 3: Set Up External Services

### 3.1 PostgreSQL Database

```bash
# Connect to PostgreSQL server
psql -h <db-host> -U postgres

# Create database and user
CREATE DATABASE orangescrum;
CREATE USER orangescrum WITH PASSWORD 'your-strong-password';
GRANT ALL PRIVILEGES ON DATABASE orangescrum TO orangescrum;

# Grant schema permissions (PostgreSQL 15+)
\c orangescrum
GRANT ALL ON SCHEMA public TO orangescrum;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO orangescrum;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO orangescrum;

\q
```

### 3.2 Redis Cache

```bash
# Test Redis connection
redis-cli -h <redis-host> -p 6379 -a YOUR_PASSWORD ping
# Should return: PONG

# For AWS ElastiCache with TLS:
# Set REDIS_TLS_ENABLED=true in .env
```

### 3.3 S3 Bucket Setup

**AWS S3:**
```bash
# Create bucket
aws s3 mb s3://orangescrum-production-files --region us-east-1

# Create IAM user with S3 access
# Grant AmazonS3FullAccess or custom policy:
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::orangescrum-production-files",
        "arn:aws:s3:::orangescrum-production-files/*"
      ]
    }
  ]
}

# Generate access keys and add to .env
```

**DigitalOcean Spaces:**
```bash
# Create Space via DigitalOcean control panel
# Generate API keys (access key + secret key)
# Update .env:
STORAGE_ENDPOINT=https://nyc3.digitaloceanspaces.com
STORAGE_BUCKET=orangescrum-production
STORAGE_REGION=nyc3
```

---

## Step 4: Deploy Application

### 4.1 Run Database Migrations (First Time Only)

```bash
# Deploy application with migrations
docker compose up -d orangescrum-app

# Watch logs to verify migration success
docker compose logs -f orangescrum-app

# Look for: "[OK] Migrations completed successfully"
```

### 4.2 Deploy Application (Subsequent Runs)

```bash
# Set SKIP_MIGRATIONS=1 in .env for faster restarts

# Deploy application
docker compose up -d orangescrum-app

# Verify container is running
docker compose ps

# Check health
docker compose exec orangescrum-app wget -qO- http://localhost/home/healthcheck
```

### 4.3 Deploy Queue Worker (Optional but Recommended)

```bash
# Deploy queue worker for background jobs
docker compose --profile queue up -d queue-worker

# Verify it's running
docker compose ps queue-worker

# Check logs
docker compose logs -f queue-worker
```

---

## Step 5: Configure Reverse Proxy

### 5.1 nginx Configuration

```bash
sudo nano /etc/nginx/sites-available/orangescrum
```

```nginx
# Redirect HTTP to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name app.<your-domain>;
    
    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name app.<your-domain>;
    
    # SSL Configuration (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/app.<your-domain>/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/app.<your-domain>/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Max upload size (match PHP_UPLOAD_MAX_FILESIZE)
    client_max_body_size 200M;
    
    # Rate limiting (prevents brute force)
    limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;
    
    # Proxy to OrangeScrum
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        
        # Preserve original request information
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support (if needed)
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }
    
    # Rate limit login endpoint
    location ~ ^/(users/login|users/signup) {
        limit_req zone=login burst=10 nodelay;
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Access and error logs
    access_log /var/log/nginx/orangescrum-access.log;
    error_log /var/log/nginx/orangescrum-error.log;
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/orangescrum /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

### 5.2 Install SSL Certificate (Let's Encrypt)

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d app.<your-domain>

# Test auto-renewal
sudo certbot renew --dry-run
```

---

## Step 6: Configure Firewall

```bash
# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Block direct access to application port
sudo ufw deny 8080/tcp

# Allow SSH (if not already enabled)
sudo ufw allow 22/tcp

# Enable firewall
sudo ufw enable

# Verify rules
sudo ufw status
```

---

## Step 7: Set Up Monitoring

### 7.1 Health Check Monitoring

```bash
# Add to cron for monitoring
crontab -e

# Add health check every 5 minutes
*/5 * * * * curl -fsS -m 10 --retry 3 https://app.<your-domain>/home/healthcheck > /dev/null || echo "OrangeScrum health check failed" | mail -s "Alert: OrangeScrum Down" admin@<your-domain>
```

### 7.2 Docker Container Monitoring

```bash
# Install Docker healthcheck monitor (optional)
docker run -d \
  --name watchtower \
  --restart unless-stopped \
  -v /var/run/docker.sock:/var/run/docker.sock \
  containrrr/watchtower --interval 3600 --cleanup
```

---

## Step 8: Backup Strategy

### 8.1 Database Backup

```bash
# Create backup script
sudo nano /opt/application/backup-database.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/opt/application/backups"
DATE=$(date +%Y%m%d-%H%M%S)
mkdir -p $BACKUP_DIR

# Backup PostgreSQL
PGPASSWORD="$DB_PASSWORD" pg_dump \
  -h <db-host> \
  -U orangescrum \
  -d orangescrum \
  -F c \
  -f "$BACKUP_DIR/orangescrum-db-$DATE.dump"

# Compress
gzip "$BACKUP_DIR/orangescrum-db-$DATE.dump"

# Keep only last 30 days
find $BACKUP_DIR -name "orangescrum-db-*.dump.gz" -mtime +30 -delete

echo "Backup completed: orangescrum-db-$DATE.dump.gz"
```

```bash
chmod +x /opt/application/backup-database.sh

# Add to cron (daily at 2 AM)
crontab -e
0 2 * * * /opt/application/backup-database.sh
```

### 8.2 S3 Backup (Optional)

Files are already in S3, but enable versioning:

```bash
# Enable S3 versioning
aws s3api put-bucket-versioning \
  --bucket orangescrum-production-files \
  --versioning-configuration Status=Enabled

# Enable lifecycle policy to archive old versions to Glacier
```

---

## Step 9: Post-Deployment Verification

```bash
# 1. Check container status
docker compose ps

# 2. Check logs for errors
docker compose logs --tail=100 orangescrum-app

# 3. Test health endpoint
curl -I https://app.<your-domain>/home/healthcheck
# Should return: HTTP/2 200

# 4. Test application login
# Open browser: https://app.<your-domain>

# 5. Verify file upload (S3)
# Login → Create project → Upload file → Verify in S3 bucket

# 6. Verify email sending
# Login → Test notification email

# 7. Check queue worker
docker compose logs queue-worker | grep "Processing job"

# 8. Check cron jobs
docker compose exec orangescrum-app cat /data/logs/cron.log
```

---

## Step 10: Ongoing Maintenance

### Update Application

```bash
cd /opt/application/orangescrum-frankenphp-v*/

# Pull latest image
docker compose pull

# Stop and restart containers
docker compose down
docker compose up -d

# Watch logs for errors
docker compose logs -f
```

### View Logs

```bash
# Application logs
docker compose logs -f orangescrum-app

# Queue worker logs
docker compose logs -f queue-worker

# nginx logs
sudo tail -f /var/log/nginx/orangescrum-*.log
```

### Restart Application

```bash
docker compose restart orangescrum-app
```

---

## Troubleshooting

### Container won't start

```bash
# Check logs
docker compose logs orangescrum-app

# Verify environment variables
docker compose config

# Check if port is already in use
sudo lsof -i :8080
```

### Database connection failed

```bash
# Test database connection from container
docker compose exec orangescrum-app sh
# Inside container:
PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -U "$DB_USERNAME" -d "$DB_NAME" -c "SELECT version();"
```

### Redis connection failed

```bash
# Test Redis from container
docker compose exec orangescrum-app sh
# Inside container:
redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" -a "$REDIS_PASSWORD" ping
```

### SSL certificate issues

```bash
# Renew certificate manually
sudo certbot renew

# Check certificate expiration
sudo certbot certificates
```

---

## Security Hardening

1. **Enable Docker security scanning:**
   ```bash
   docker scan orangescrum-app:latest
   ```

2. **Limit Docker daemon access:**
   ```bash
   sudo chmod 660 /var/run/docker.sock
   ```

3. **Enable audit logging:**
   ```bash
   sudo auditctl -w /var/run/docker.sock -k docker
   ```

4. **Regular security updates:**
   ```bash
   # System updates
   sudo apt update && sudo apt upgrade -y
   
   # Docker images
   docker compose pull && docker compose up -d
   ```

---

## Support

- **Documentation:** See /docs folder
- **Health Check:** `curl https://app.<your-domain>/home/healthcheck`
- **Logs:** `docker compose logs -f orangescrum-app`
