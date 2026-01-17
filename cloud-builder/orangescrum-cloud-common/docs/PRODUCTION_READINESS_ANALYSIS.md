# OrangeScrum FrankenPHP - Production Readiness Analysis

**Date:** January 10, 2026  
**Analyzed:** orangescrum-cloud deployment setup  
**Binary:** `/orangescrum-app/osv4-prod` (FrankenPHP static binary with embedded CakePHP 4 app)

---

## Executive Summary

The current setup is **NOT fully production-ready** and requires several critical fixes before deployment to production environments. The issues range from security vulnerabilities to missing production configurations.

### Critical Issues Found: 7
### Medium Issues Found: 5
### Minor Issues Found: 3

---

## Critical Issues (Required Before Production)

### 1. Default Passwords in .env.example
**File:** `.env.example`  
**Issue:** Default passwords are weak and predictable
```bash
DB_PASSWORD=changeme_in_production
SECURITY_SALT=__CHANGE_THIS_TO_RANDOM_STRING__
V2_ROUTING_API_KEY=your-secure-api-key-here-change-this
```

**Risk:** High - Anyone can access the database or compromise encryption  
**Fix Required:**
- Remove default values or use placeholder text
- Add validation in entrypoint.sh to fail if defaults are still in use
- Add stronger warnings in comments

### 2. Missing Production Environment Detection
**File:** `entrypoint.sh`, `run.sh`  
**Issue:** No validation that required production variables are set  
**Risk:** Application may start with insecure defaults  
**Fix Required:**
```bash
# Add to entrypoint.sh at startup
if [ "$SECURITY_SALT" = "__CHANGE_THIS_TO_RANDOM_STRING__" ]; then
    echo "FATAL: SECURITY_SALT must be changed from default value"
    exit 1
fi

if [ "$DB_PASSWORD" = "changeme_in_production" ]; then
    echo "FATAL: DB_PASSWORD must be changed from default value"
    exit 1
fi

if [ "$DEBUG" = "true" ] && [ "$ENVIRONMENT" = "production" ]; then
    echo "Note: DEBUG should be false in production"
fi
```

### 3. No TLS/HTTPS Configuration for Production
**File:** Docker setup, deployment docs  
**Issue:** Application runs on HTTP (port 80/8080) without TLS  
**Risk:** Data transmitted in plaintext, session hijacking  
**Fix Required:**
- Add reverse proxy documentation (nginx/Apache/Caddy)
- Configure FrankenPHP to handle TLS natively (it supports this via Caddy)
- Add environment variable for TLS cert/key paths

### 4. Insecure Default Bind Address
**File:** `.env.example`, `docker-compose.yaml`  
**Issue:** `APP_BIND_IP=0.0.0.0` - binds to all interfaces  
**Risk:** Exposes application to external networks when it should be internal-only  
**Fix Required:**
```bash
# For production behind reverse proxy
APP_BIND_IP=127.0.0.1  # Localhost only
APP_PORT=8080

# Only use 0.0.0.0 when directly exposed with proper firewall
```

### 5. No Rate Limiting or DDoS Protection
**Issue:** No built-in rate limiting for API endpoints  
**Risk:** Vulnerable to brute force, credential stuffing, DDoS  
**Fix Required:**
- Implement middleware for rate limiting
- Document required reverse proxy rate limiting (nginx limit_req)
- Add CAPTCHA on sensitive endpoints (login, signup)

### 6. Missing Health Check Endpoint Validation
**File:** `docker-compose.yaml`  
**Issue:** Health check uses `/home/healthcheck` but no validation of response  
```yaml
healthcheck:
  test: ["CMD-SHELL", "wget --no-verbose --tries=1 --spider http://localhost/home/healthcheck || exit 1"]
```
**Risk:** Container marked healthy even if app is degraded  
**Fix Required:**
- Validate actual response content, not just HTTP 200
- Check database connectivity in health check
- Check Redis connectivity in health check

### 7. Cron Job Uses Wildcard Path Matching
**File:** `config/cron/recurring_task_cron_franken`  
**Issue:** `cd /tmp/frankenphp_*` - wildcard can match multiple directories  
```bash
*/30 * * * * cd /tmp/frankenphp_* && /orangescrum-app/osv4-prod php-cli bin/cake.php recurring_task
```
**Risk:** Cron may fail or run in wrong directory  
**Fix Required:**
```bash
# Store extracted path in a fixed location
*/30 * * * * EXTRACTED_APP=$(find /tmp -maxdepth 1 -name "frankenphp_*" -type d | head -1) && cd "$EXTRACTED_APP" && /orangescrum-app/osv4-prod php-cli bin/cake.php recurring_task >> /data/logs/cron.log 2>&1
```

---

## Medium Priority Issues (Recommended)

### 8. Missing Log Rotation Configuration
**Issue:** Logs will grow indefinitely  
**Files:** `/data/logs/cron.log`, application logs  
**Fix Required:**
- Add logrotate configuration
- Document log management
- Set max log size in Docker logging config (already present in docker-compose.yaml [OK])

### 9. No Backup/Restore Documentation
**Issue:** No documented backup strategy for:
- Database (PostgreSQL)
- Redis data (if persistent)
- S3 uploaded files (already in S3, but no backup policy documented)

**Fix Required:**
- Document backup procedures
- Add backup scripts
- Document disaster recovery process

### 10. Missing Monitoring/Alerting Setup
**Issue:** No built-in monitoring for:
- Application uptime
- Database connections
- Redis connections
- Queue processing status
- Disk usage

**Fix Required:**
- Add Prometheus metrics endpoint
- Document integration with monitoring tools (Grafana, Datadog, New Relic)
- Add alerting for critical failures

### 11. Queue Worker Has No Dead Letter Queue
**File:** `queue-worker.sh`, `docker-compose.yaml`  
**Issue:** Failed jobs may be lost or retry indefinitely  
**Fix Required:**
- Configure max retry attempts
- Implement dead letter queue for failed jobs
- Add monitoring for failed jobs

### 12. No Container Image Scanning
**Issue:** Docker image built from `alpine:latest` without security scanning  
**Fix Required:**
- Pin Alpine version: `FROM alpine:3.19`
- Add vulnerability scanning (Trivy, Snyk)
- Document update policy

---

## Minor Issues (Optional Enhancement)

### 13. Inconsistent Script Names
**Issue:** [RESOLVED] `run.sh` and `run-native.sh` duplication eliminated - now using single `run.sh`  
**Fix:** Consolidate or clarify naming

### 14. Missing Performance Tuning Docs
**Issue:** No guidance on:
- PHP-FPM worker count (if applicable to FrankenPHP)
- Database connection pooling
- Redis connection limits

### 15. No Graceful Shutdown Handling
**Issue:** Container shutdown may interrupt requests  
**Fix:** Add SIGTERM handling to complete in-flight requests

---

## Current Capabilities

1. **Non-root user in Docker** - Container runs as `orangescrum` user (UID 1000)
2. **External database support** - No database in container (stateless)
3. **External Redis support** - Cache and queue externalized
4. **S3 storage** - File uploads not in container filesystem
5. **Health checks** - Docker health check configured
6. **Resource limits** - CPU and memory limits in docker-compose.yaml
7. **Log limits** - Docker log rotation configured
8. **Queue worker separation** - Separate container for background jobs
9. **Auto-restart** - `restart: unless-stopped` policy
10. **Environment variable configuration** - All config via .env

---

## Checklist Production Deployment Checklist

### Pre-Deployment

- [ ] Change all default passwords and secrets
- [ ] Generate strong SECURITY_SALT: `openssl rand -base64 32`
- [ ] Set DEBUG=false
- [ ] Configure production database with strong password
- [ ] Configure Redis with authentication (REDIS_PASSWORD)
- [ ] Set up S3 bucket with proper IAM permissions
- [ ] Configure email provider (SendGrid/SMTP)
- [ ] Set FULL_BASE_URL to production domain
- [ ] Enable HTTPS with valid SSL certificate
- [ ] Configure session domain for production
- [ ] Review and configure rate limiting
- [ ] Set up monitoring and alerting
- [ ] Configure backup strategy
- [ ] Test disaster recovery procedure

### Docker Deployment

```bash
# 1. Copy and configure environment
cp .env.example .env
nano .env  # Configure all production values

# 2. Validate configuration
grep -E "changeme|CHANGE_THIS|your-" .env
# Should return no results!

# 3. Deploy application
docker-compose up -d orangescrum-app

# 4. Deploy queue worker (optional)
docker-compose --profile queue up -d queue-worker

# 5. Verify health
docker-compose ps
docker-compose logs -f orangescrum-app

# 6. Test health endpoint
curl http://localhost:8080/home/healthcheck
```

### Native FrankenPHP Binary Deployment

```bash
# 1. Install as systemd service
sudo cp deployment-package/orangescrum.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable orangescrum
sudo systemctl start orangescrum

# 2. Configure reverse proxy (nginx/Apache)
# See DEPLOYMENT.md for examples

# 3. Set up SSL certificate (Let's Encrypt)
sudo certbot --nginx -d app.<your-domain>

# 4. Configure firewall
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw deny 8080/tcp  # Block direct access to app port

# 5. Monitor logs
sudo journalctl -u orangescrum -f
```

### Post-Deployment Verification

- [ ] Health check returns HTTP 200
- [ ] Can login to application
- [ ] Can upload files (S3 working)
- [ ] Can send email (test notification)
- [ ] Background jobs processing (check queue worker logs)
- [ ] Cron jobs running (check /data/logs/cron.log)
- [ ] SSL certificate valid and auto-renews
- [ ] Monitoring alerts configured
- [ ] Backup running successfully
- [ ] Database migrations applied
- [ ] Application performance acceptable

---

## Recommended Production Architecture

### High Availability Setup

```
                                    ┌─────────────────┐
                                    │   CloudFlare    │
                                    │   DNS + CDN     │
                                    └────────┬────────┘
                                             │
                                             ▼
                         ┌───────────────────────────────┐
                         │   Load Balancer (AWS ALB)     │
                         │   - SSL Termination           │
                         │   - Health Checks             │
                         │   - Rate Limiting             │
                         └───────┬──────────────┬────────┘
                                 │              │
                    ┌────────────┘              └────────────┐
                    ▼                                        ▼
        ┌─────────────────────┐                 ┌─────────────────────┐
        │  App Instance 1     │                 │  App Instance 2     │
        │  (Docker/Binary)    │                 │  (Docker/Binary)    │
        └──────┬──────────────┘                 └──────┬──────────────┘
               │                                        │
               └────────────┬───────────────────────────┘
                            │
           ┌────────────────┼────────────────┐
           ▼                ▼                ▼
    ┌──────────┐    ┌──────────┐    ┌──────────┐
    │PostgreSQL│    │  Redis   │    │ AWS S3   │
    │  (RDS)   │    │(ElastiC.)│    │ Bucket   │
    └──────────┘    └──────────┘    └──────────┘
```

### Minimal Production Setup (Single Server)

```
    ┌─────────────────────────────────────────┐
    │         Production Server               │
    │                                         │
    │  ┌───────────────────────────────────┐ │
    │  │  Nginx (Reverse Proxy + SSL)      │ │
    │  │  Port 80/443                       │ │
    │  └────────────┬──────────────────────┘ │
    │               ▼                         │
    │  ┌───────────────────────────────────┐ │
    │  │  OrangeScrum (FrankenPHP Binary)  │ │
    │  │  Port 8080 (localhost only)       │ │
    │  └────────────┬──────────────────────┘ │
    │               │                         │
    │  ┌────────────┼────────────────┐       │
    │  ▼            ▼                ▼       │
    │  PostgreSQL  Redis       Queue Worker │
    │  (local)     (local)     (FrankenPHP) │
    └─────────────────────────────────────────┘
              ▼
       External S3 Bucket
       (DigitalOcean Spaces, AWS S3, etc.)
```

---

## Configuration Required Fixes - Implementation Priority

### Priority 1 (Critical - Fix Immediately)
1. Add startup validation for default passwords
2. Document and enforce HTTPS usage
3. Fix cron wildcard path issue
4. Change default APP_BIND_IP to 127.0.0.1

### Priority 2 (High - Fix Before Production)
5. Add comprehensive health checks
6. Implement rate limiting documentation
7. Add monitoring integration
8. Document backup procedures

### Priority 3 (Medium - Fix Soon After)
9. Add log rotation configuration
10. Implement dead letter queue
11. Add container image scanning
12. Performance tuning documentation

---

## Documentation Conclusion

The OrangeScrum FrankenPHP setup has a **solid foundation** with good architectural decisions (stateless containers, external services, proper separation of concerns), but requires **critical security hardening** before production use.

**Estimated effort to make production-ready:**
- Critical fixes: 4-6 hours
- Medium fixes: 8-12 hours
- Documentation updates: 4-6 hours
- Testing and validation: 8-10 hours

**Total: ~2-3 days of focused work**

### Immediate Next Steps:
1. Create validation script for environment variables
2. Update .env.example with secure defaults
3. Add production deployment script with validation
4. Update documentation with security best practices
5. Create monitoring and backup guides

---

## Support Support Contacts

- For security issues: [Create security advisory]
- For deployment help: [See DEPLOYMENT.md]
- For bug reports: [Create GitHub issue]
