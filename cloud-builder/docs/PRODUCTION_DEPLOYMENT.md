# 🚀 Production Deployment Guide

## Pre-Deployment Checklist

- [ ] Server with Docker 24.0+ and Compose V2 installed
- [ ] At least 8GB RAM, 20GB disk space
- [ ] Domain name configured (optional but recommended)
- [ ] SSL certificate ready (if using HTTPS)
- [ ] Firewall configured
- [ ] Backup strategy in place

---

## Quick Deployment

### 1. Build the Application

```bash
# Clone repository and navigate to builder
cd durango-multitenant/durango-builder

# Create Python virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install docker

# Build base image (one-time, ~30 minutes)
python3 build_optimized.py

# Binary will be at: orangescrum-ee/orangescrum-app/orangescrum-ee
```

### 2. Configure Environment

```bash
cd orangescrum-ee

# Copy example environment file
cp .env.example .env

# Edit with your settings
nano .env
```

**Required changes in `.env`:**

```bash
COMPOSE_PROJECT_NAME=orangescrum-production
APP_PORT=80
DB_USER=orangescrum
DB_PASSWORD=YOUR_STRONG_PASSWORD_HERE  # ⚠️ CHANGE THIS!
DB_NAME=orangescrum
```

**Generate a strong password:**

```bash
openssl rand -base64 32
```

### 3. Deploy

```bash
# Start services
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f
```

### 4. Verify Deployment

```bash
# Check health
docker compose ps

# Expected output:
# NAME                  STATUS
# orangescrum-app-1     Up (healthy)
# orangescrum-db-1      Up (healthy)

# Test application
curl -I http://localhost:80

# Expected: HTTP 302 (redirect to login)
```

---

## Production Configuration

### Resource Limits

Current configuration (adjust in `docker-compose.yaml`):

**Application:**

- CPU: 0.5-2 cores
- Memory: 512MB-2GB

**Database:**

- CPU: 0.5-2 cores
- Memory: 256MB-2GB
- Shared memory: 256MB

### Logging

Logs are limited to prevent disk space issues:

- Max size per file: 10MB
- Max files: 3 (30MB total per container)

View logs:

```bash
docker compose logs -f orangescrum-app
docker compose logs -f orangescrum-db
```

### Health Checks

**Application:**

- Endpoint: `http://localhost:80`
- Interval: 30 seconds
- Timeout: 10 seconds
- Retries: 3
- Start period: 40 seconds

**Database:**

- Command: `pg_isready`
- Interval: 10 seconds
- Timeout: 5 seconds
- Retries: 5

---

## Reverse Proxy Setup (Recommended)

### Option 1: Nginx

```nginx
# /etc/nginx/sites-available/orangescrum
server {
    listen 80;
    server_name orangescrum.example.com;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name orangescrum.example.com;

    ssl_certificate /etc/ssl/certs/orangescrum.crt;
    ssl_certificate_key /etc/ssl/private/orangescrum.key;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Increase upload size limit
    client_max_body_size 100M;

    location / {
        proxy_pass http://localhost:80;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

**Enable and restart:**

```bash
sudo ln -s /etc/nginx/sites-available/orangescrum /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Option 2: Traefik

```yaml
# Add to docker-compose.yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.orangescrum.rule=Host(`orangescrum.example.com`)"
  - "traefik.http.routers.orangescrum.entrypoints=websecure"
  - "traefik.http.routers.orangescrum.tls.certresolver=letsencrypt"
  - "traefik.http.services.orangescrum.loadbalancer.server.port=80"
```

---

## Security Hardening

### 1. Change Default Port

Edit `.env`:

```bash
APP_PORT=8080  # Instead of 80
```

Then use reverse proxy on port 80/443.

### 2. Network Isolation

```yaml
# Add to docker-compose.yaml
networks:
  orangescrum-network:
    driver: bridge
    internal: true  # Isolate from external networks
```

### 3. Database Access

Database is not exposed externally (no ports section). Access only through internal network.

### 4. File Upload Restrictions

Configure in application settings (after deployment):

- Max file size
- Allowed file types
- Upload directory permissions

### 5. Regular Updates

```bash
# Update base images
docker compose pull

# Rebuild with latest security patches
docker compose up -d --build
```

---

## Backup Strategy

### Automated Daily Backups

```bash
# Create backup script
cat > /usr/local/bin/orangescrum-backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR=/backups/orangescrum
cd /path/to/durango-builder
./backup_volumes.sh backup ${BACKUP_DIR}

# Clean old backups (keep last 7 days)
find ${BACKUP_DIR} -type d -mtime +7 -exec rm -rf {} +
EOF

chmod +x /usr/local/bin/orangescrum-backup.sh

# Add to crontab (daily at 2 AM)
echo "0 2 * * * /usr/local/bin/orangescrum-backup.sh" | crontab -
```

### Manual Backup

```bash
cd durango-builder
./backup_volumes.sh backup
```

### Off-Site Backup

```bash
# Sync to remote server
rsync -avz ./backups/ user@backup-server:/backups/orangescrum/

# Or upload to S3
aws s3 sync ./backups/ s3://your-bucket/orangescrum-backups/
```

---

## Monitoring

### Basic Health Check

```bash
#!/bin/bash
# healthcheck.sh

if docker compose ps | grep -q "unhealthy"; then
    echo "⚠️  Unhealthy containers detected!"
    docker compose ps
    exit 1
fi

echo "✅ All containers healthy"
```

### Resource Usage

```bash
# Check resource usage
docker stats orangescrum-app-1 orangescrum-db-1

# Check disk usage
docker system df -v
```

### Logs Monitoring

```bash
# Watch for errors
docker compose logs -f | grep -i error

# Export logs to file
docker compose logs --since 24h > orangescrum-logs-$(date +%Y%m%d).log
```

---

## Maintenance

### Update Application Code

```bash
# 1. Backup first!
cd durango-builder
./backup_volumes.sh backup

# 2. Pull latest code
git pull origin feature/multi-tenant

# 3. Rebuild binary
python3 build_optimized.py --skip-base

# 4. Rebuild and restart
cd orangescrum-ee
docker compose up -d --build

# 5. Verify
docker compose ps
curl -I http://localhost:80
```

### Database Maintenance

```bash
# Vacuum database
docker exec orangescrum-db-1 psql -U orangescrum -d orangescrum -c "VACUUM ANALYZE;"

# Check database size
docker exec orangescrum-db-1 psql -U orangescrum -d orangescrum -c "
SELECT pg_size_pretty(pg_database_size('orangescrum'));"
```

### Clean Docker Resources

```bash
# Remove unused images
docker image prune -a

# Remove stopped containers
docker container prune

# Check space
docker system df
```

---

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker compose logs orangescrum-app

# Common issues:
# - Port 80 already in use: Change APP_PORT in .env
# - Permission denied: Check file permissions
# - Database connection failed: Check DB_PASSWORD matches in .env
```

### Application Not Responding

```bash
# Check health status
docker compose ps

# Restart unhealthy container
docker compose restart orangescrum-app

# Check entrypoint logs
docker logs orangescrum-app-1 | grep -E "(Found|Linked|configured|ERROR)"
```

### Database Connection Issues

```bash
# Test database connectivity
docker exec orangescrum-db-1 pg_isready -U orangescrum

# Check database logs
docker compose logs orangescrum-db

# Verify credentials
docker compose exec orangescrum-db psql -U orangescrum -d orangescrum
```

### Disk Space Full

```bash
# Check disk usage
df -h

# Clean Docker
docker system prune -a --volumes  # ⚠️ CAREFUL! Use backup first

# Check volume sizes
docker system df -v
```

### Restore from Backup

```bash
cd durango-builder
./backup_volumes.sh list
./backup_volumes.sh restore ./backups/YYYYMMDD_HHMMSS
```

---

## Scaling Considerations

### Vertical Scaling

Increase resources in `docker-compose.yaml`:

```yaml
deploy:
  resources:
    limits:
      cpus: '4'
      memory: 4G
```

### Horizontal Scaling

For multiple instances:

1. Use external database (not in compose)
2. Configure shared storage for volumes (NFS, GlusterFS)
3. Add load balancer (HAProxy, Nginx)
4. Separate cache layer (Redis)

---

## Production Checklist

Before going live:

- [ ] Strong database password set
- [ ] `.env` file configured
- [ ] Reverse proxy with HTTPS configured
- [ ] Firewall rules configured
- [ ] Automated backups set up
- [ ] Monitoring in place
- [ ] Health checks passing
- [ ] Resource limits appropriate
- [ ] Logs rotation configured
- [ ] Documentation updated
- [ ] Disaster recovery plan documented
- [ ] Team trained on backup/restore

---

## Quick Commands Reference

```bash
# Start
docker compose up -d

# Stop
docker compose down

# Restart
docker compose restart

# View logs
docker compose logs -f

# Status
docker compose ps

# Backup
./backup_volumes.sh backup

# Restore
./backup_volumes.sh restore ./backups/TIMESTAMP

# Update
docker compose up -d --build

# Clean (⚠️ dangerous!)
docker compose down -v  # Deletes all data!
```

---

## Support

For issues:

1. Check logs: `docker compose logs`
2. Verify health: `docker compose ps`
3. Review this guide
4. Check GitHub issues
5. Contact support team

## License

See main project LICENSE file.
