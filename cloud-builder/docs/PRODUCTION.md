# OrangeScrum FrankenPHP - Production Deployment Guide

This guide covers deploying the production-ready FrankenPHP static binary application.

## Production Build Overview

The build system creates a fully self-contained FrankenPHP static binary that includes:
- **PHP 8.3** with all required extensions (statically compiled)
- **Caddy web server** (embedded)
- **Complete OrangeScrum application** (embedded)
- **All PHP dependencies** (composer packages included)

Binary size: ~370 MB (single executable, no external dependencies)

---

## Quick Production Deployment

### 1. Prerequisites

```bash
# Check prerequisites
python3 build.py --check
```

Required:
- Docker 24.0+
- Docker Compose v2.0+
- Python 3.8+
- Git access to OrangeScrum repository

### 2. Configure Environment

```bash
cd orangescrum-ee
cp .env.example .env
nano .env
```

**Critical production settings:**

```bash
# Database (use external managed database)
DB_HOST=your-postgres-host
DB_PORT=5432
DB_USERNAME=orangescrum_user
DB_PASSWORD=<STRONG_PASSWORD_HERE>  # Generate with: openssl rand -base64 32
DB_NAME=orangescrum_production

# Application
DEBUG=false                # MUST be false in production
CACHE_ENGINE=file         # Use 'redis' for better performance with external Redis
SKIP_MIGRATIONS=1         # Skip on startup after initial deployment

# Network
APP_BIND_IP=0.0.0.0       # Bind to all interfaces (put behind reverse proxy)
APP_PORT=8080             # Internal port (map via reverse proxy)
```

### 3. Build Production Binary

```bash
# Full build (first time or when dependencies change)
python3 build.py

# Or with custom options
python3 build.py \
  --db-host production-db.example.com \
  --db-name orangescrum_prod \
  --db-username orangescrum \
  --db-password 'your-secure-password'
```

Build time:
- First build (base image): ~20-30 minutes
- Subsequent builds (app only): ~1-2 minutes

### 4. Deploy to Production

The build script automatically:
1. ✅ Archives OrangeScrum repository
2. ✅ Builds/reuses base FrankenPHP image (one-time)
3. ✅ Embeds application code into binary
4. ✅ Extracts ~370MB static binary
5. ✅ Builds optimized runtime container
6. ✅ Deploys app-only service (no database, MinIO, etc.)
7. ✅ Runs health checks

---

## Production Architecture

```
┌─────────────────────────────────────────┐
│   Reverse Proxy (nginx/Caddy/Traefik)  │
│   - HTTPS termination                   │
│   - Rate limiting                       │
│   - Request filtering                   │
└───────────────┬─────────────────────────┘
                │
                ↓
┌─────────────────────────────────────────┐
│   OrangeScrum FrankenPHP Container      │
│   - Port: 8080 (internal)               │
│   - User: orangescrum (non-root)        │
│   - Binary: /orangescrum-app/orangescrum-ee │
└───────────────┬─────────────────────────┘
                │
                ↓
┌─────────────────────────────────────────┐
│   External PostgreSQL Database          │
│   - Managed service recommended         │
│   - Regular backups                     │
│   - Connection pooling (PgBouncer)      │
└─────────────────────────────────────────┘
```

---

## Security Hardening

### 1. Container Security

The production Dockerfile includes:

✅ **Non-root user**: Runs as `orangescrum` user (UID 1000)
✅ **Minimal base**: Alpine Linux (5 MB)
✅ **CAP_NET_BIND_SERVICE**: Allows binding to port 80 without root
✅ **No SSH/shell**: No debugging tools in production image
✅ **Read-only filesystem**: Application is embedded (immutable)

### 2. Network Security

```yaml
# Recommended nginx reverse proxy config
server {
    listen 443 ssl http2;
    server_name orangescrum.example.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    
    # Rate limiting
    limit_req zone=orangescrum burst=20 nodelay;
    
    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 3. Database Security

- ✅ Use managed PostgreSQL service (RDS, Cloud SQL, etc.)
- ✅ Enable SSL/TLS connections
- ✅ Restrict access by IP (security groups)
- ✅ Use strong passwords (32+ characters)
- ✅ Enable automatic backups
- ✅ Use connection pooling (PgBouncer)

---

## Performance Optimization

### 1. Cache Configuration

**Development**: File cache (default)
```bash
CACHE_ENGINE=file
```

**Production**: Redis cache (recommended)
```bash
CACHE_ENGINE=redis
REDIS_HOST=redis.example.com
REDIS_PORT=6379
```

### 2. Resource Limits

Current docker-compose.yaml settings:
```yaml
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 2G
    reservations:
      cpus: '0.5'
      memory: 512M
```

Adjust based on traffic:
- **Small** (< 100 users): 1 CPU, 1GB RAM
- **Medium** (100-500 users): 2 CPU, 2GB RAM
- **Large** (500+ users): 4 CPU, 4GB RAM + horizontal scaling

### 3. Database Optimization

```sql
-- Create indexes for common queries
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_projects_status ON projects(status);

-- Enable query optimization
ANALYZE;
VACUUM;
```

---

## Monitoring & Logging

### 1. Container Logs

```bash
# View logs
docker logs -f orangescrum-cloud-orangescrum-app-1

# Export logs
docker logs orangescrum-cloud-orangescrum-app-1 > /var/log/orangescrum.log
```

### 2. Health Checks

Built-in health check endpoint:
```bash
curl http://localhost:8080/home/healthcheck
```

Docker health status:
```bash
docker ps | grep orangescrum
# Status should show: (healthy)
```

### 3. Application Logs

Logs location inside container:
- Application: `/data/logs/`
- Cron: `/data/logs/cron.log`

Mount volume for persistent logs:
```yaml
volumes:
  - /var/log/orangescrum:/data/logs
```

---

## Backup & Recovery

### 1. Database Backups

```bash
# Daily automated backup
pg_dump -h $DB_HOST -U $DB_USERNAME -d $DB_NAME | gzip > backup-$(date +%Y%m%d).sql.gz
```

### 2. File Storage Backups

Mount persistent volumes:
```yaml
volumes:
  - /var/orangescrum/files:/data/webroot/files
  - /var/orangescrum/uploads:/data/webroot/csv
```

### 3. Disaster Recovery

To restore:
1. Deploy fresh container
2. Restore database: `psql -h $DB_HOST -U $DB_USERNAME -d $DB_NAME < backup.sql`
3. Restore files: `cp -r backup/files/* /var/orangescrum/files/`
4. Start application: `docker compose up -d`

---

## Scaling

### Horizontal Scaling

Run multiple app containers behind a load balancer:

```yaml
# docker-compose.yaml
services:
  orangescrum-app:
    deploy:
      replicas: 3  # Run 3 instances
    # ... rest of config
```

Load balancer (nginx):
```nginx
upstream orangescrum_backend {
    least_conn;
    server 10.0.0.1:8080;
    server 10.0.0.2:8080;
    server 10.0.0.3:8080;
}
```

### Database Scaling

- Use read replicas for reports
- Enable connection pooling (PgBouncer)
- Use managed database auto-scaling

---

## Troubleshooting

### Container won't start

```bash
# Check logs
docker logs orangescrum-cloud-orangescrum-app-1

# Verify database connection
docker exec orangescrum-cloud-orangescrum-app-1 psql -h $DB_HOST -U $DB_USERNAME -d $DB_NAME -c "SELECT 1"
```

### 500 Internal Server Error

1. Check `DEBUG=false` and `CACHE_ENGINE=file` are set
2. Verify cache directories are writable
3. Check database connectivity
4. Review application logs

### Migrations failing

```bash
# Skip migrations on startup
SKIP_MIGRATIONS=1 docker compose up -d

# Run migrations manually
docker exec orangescrum-cloud-orangescrum-app-1 sh -c 'cd /tmp/frankenphp_* && /orangescrum-app/orangescrum-ee php-cli bin/cake.php migrations migrate'
```

---

## Production Checklist

Before going live:

- [ ] **Database**: Using managed PostgreSQL with backups enabled
- [ ] **Environment**: `DEBUG=false` in .env
- [ ] **Cache**: Redis configured for production
- [ ] **Security**: Strong database password (32+ chars)
- [ ] **SSL/TLS**: HTTPS enabled via reverse proxy
- [ ] **Monitoring**: Health checks configured
- [ ] **Backups**: Automated daily backups
- [ ] **Logs**: Persistent log storage configured
- [ ] **Resources**: CPU/memory limits appropriate for load
- [ ] **Firewall**: Only necessary ports exposed
- [ ] **Updates**: Plan for zero-downtime deployments

---

## Updating the Application

### Rolling Update (Zero Downtime)

```bash
# 1. Build new version
python3 build.py --skip-deploy

# 2. Tag current container
docker tag orangescrum-cloud-orangescrum-app orangescrum-cloud-orangescrum-app:backup

# 3. Deploy new version
cd orangescrum-ee
docker compose up -d --build

# 4. Verify health
curl http://localhost:8080/home/healthcheck

# 5. Rollback if needed
# docker tag orangescrum-cloud-orangescrum-app:backup orangescrum-cloud-orangescrum-app:latest
# docker compose up -d
```

---

## Support

For issues or questions:
1. Check logs: `docker logs orangescrum-cloud-orangescrum-app-1`
2. Verify configuration: `.env` settings
3. Test database: Connection and migrations
4. Review this guide's troubleshooting section

