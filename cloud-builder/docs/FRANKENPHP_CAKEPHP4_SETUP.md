# FrankenPHP Static Binary - CakePHP4 Configuration Guide

Complete configuration steps for running OrangeScrum (CakePHP4) as a self-contained FrankenPHP static binary.

## Overview

FrankenPHP combines:
- **PHP 8.3** interpreter
- **Caddy** web server (for static files + HTTP/2/3)
- **OrangeScrum app** (embedded in binary)

Into a single **~340MB portable executable** with zero external dependencies.

---

## 1. Caddyfile Configuration

**File location:** App root (same level as `webroot/`)

```caddyfile
:8080 {
  # Root directory - CakePHP webroot
  root * /app/webroot

  # Static files - serve directly without PHP
  @static {
    path /css/*
    path /js/*
    path /images/*
    path /img/*
    path /fonts/*
    path /font/*
    path /favicon.ico
    path /robots.txt
    file
  }

  # Cache headers for static assets (30 days)
  header @static Cache-Control "public, max-age=2592000, immutable"
  
  # Serve static files directly (Caddy handles - no PHP)
  file_server @static

  # Gzip compression for dynamic content
  encode gzip

  # PHP server - handles dynamic requests (CakePHP routing)
  php_server
}
```

### Caddyfile Breakdown

| Component | Purpose |
|-----------|---------|
| `:8080` | Listen on port 8080 |
| `root * /app/webroot` | Static files served from webroot/ |
| `@static` matcher | CSS, JS, images, fonts |
| `header @static` | Set cache headers (30 days) |
| `file_server @static` | Serve matching files directly via Caddy |
| `encode gzip` | Compress dynamic responses |
| `php_server` | Route remaining requests to PHP |

### Performance Impact

- **Static files:** 10-50x faster (served by Caddy, not PHP)
- **Cache headers:** Reduces repeat requests by ~95%
- **Gzip:** Reduces bandwidth by 60-80%

---

## 2. php.ini Configuration

**File location:** App root (same level as `webroot/`)

```ini
; ==========================================
; OPcache - Operation Cache (256MB)
; ==========================================
; Dramatically speeds up PHP by caching compiled bytecode
opcache.enable=1
opcache.memory_consumption=256
opcache.max_accelerated_files=10000
opcache.revalidate_freq=0
opcache.validate_timestamps=1

; ==========================================
; Memory Limits
; ==========================================
; Allow PHP requests to use up to 512MB
memory_limit=512M
upload_max_filesize=100M
post_max_size=100M

; ==========================================
; Sessions - Redis Backend
; ==========================================
; Store sessions in Redis for:
; - 5-10x faster access (vs file system)
; - Shared across multiple servers
; - Automatic cleanup
session.save_handler=redis
session.save_path="tcp://192.168.49.10:6379?auth=orangescrum-redis-password"
session.serialize_handler=igbinary

; ==========================================
; Output Compression
; ==========================================
; Gzip compress PHP output
zlib.output_compression=1
zlib.output_compression_level=6

; ==========================================
; Security
; ==========================================
; Prevent JavaScript access to session cookies
session.cookie_httponly=1
; Cross-site request forgery protection
session.cookie_samesite=Lax
; Strict session validation
session.use_strict_mode=1

; ==========================================
; Error Handling
; ==========================================
; Don't expose errors to users
display_errors=0
log_errors=1
error_log=/var/log/php-error.log
```

### php.ini Benefits

| Setting | Benefit | Impact |
|---------|---------|--------|
| OPcache | Bytecode caching | 40-50% faster PHP execution |
| Memory 512M | More concurrent requests | Handles 2-5x more load |
| Redis sessions | Distributed sessions | Works across load balancers |
| Igbinary | Binary serialization | 30% faster session I/O |
| Gzip output | Reduced bandwidth | 60-80% smaller responses |

---

## 3. Environment Variables

Set these before running FrankenPHP:

```bash
# Application
export SERVER_ROOT=webroot
export FULL_BASE_URL=http://localhost:8080

# Database (PostgreSQL)
export DB_HOST=192.168.49.10
export DB_PORT=5432
export DB_USERNAME=postgres
export DB_PASSWORD=postgres
export DB_NAME=durango

# Redis (Session/Cache)
export REDIS_HOST=192.168.49.10
export REDIS_PASSWORD=orangescrum-redis-password
export REDIS_PORT=6379

# Application
export APP_ENV=production
export DEBUG=false
```

### Or from .env file:

```bash
source .env
./frankenphp php-server
```

---

## 4. Running the Application

### Basic (Development)
```bash
./frankenphp php-server
```
Listens on HTTP on all interfaces

### With HTTPS (Production)
```bash
./frankenphp php-server --domain example.com
```
- Auto-generates Let's Encrypt certificate
- HTTP/2 and HTTP/3 enabled
- Auto-redirects HTTP → HTTPS

### Custom Caddyfile
```bash
./frankenphp php-server -c ./Caddyfile
```

### With Background Workers (Queue Jobs)
```bash
./frankenphp php-server --worker webroot/index.php 4
```
Starts 4 worker threads for background processing

### Full Example with All Options
```bash
FULL_BASE_URL=http://localhost:8080 \
DB_HOST=192.168.49.10 \
REDIS_HOST=192.168.49.10 \
./frankenphp php-server \
  -c ./Caddyfile \
  -l 0.0.0.0:8080
```

---

## 5. File Structure

```
orangescrum/
├── Caddyfile                    # Caddy web server config
├── php.ini                      # PHP configuration
├── .env                         # Environment variables
│
├── webroot/                     # Public folder (site root)
│   ├── index.php               # Entry point
│   ├── css/                    # Served by Caddy (fast)
│   │   ├── bootstrap.min.css
│   │   └── ...
│   ├── js/                     # Served by Caddy (fast)
│   │   ├── app.js
│   │   └── ...
│   ├── img/                    # Served by Caddy (fast)
│   ├── images/                 # Served by Caddy (fast)
│   └── fonts/                  # Served by Caddy (fast)
│
├── config/                      # CakePHP config
│   ├── app_local.php
│   ├── cache_redis.php
│   ├── queue.php
│   └── ...
│
├── src/                         # CakePHP source code
│   ├── Controller/
│   ├── Model/
│   └── ...
│
├── plugins/                     # CakePHP plugins
│   ├── CloudStorage/
│   ├── Payments/
│   └── ...
│
├── vendor/                      # Composer dependencies
│
└── composer.json                # Project dependencies
```

---

## 6. Performance Tuning - Advanced

### Custom Caddyfile with Optimization

```caddyfile
{
  frankenphp {
    # Auto-scale PHP threads (2x CPU cores)
    num_threads auto
    
    # Allow up to 4x more threads if needed
    max_threads auto
    
    # Request timeout (30 seconds)
    max_wait_time 30s
    
    # Optional: Background worker for queue jobs
    worker {
      file webroot/worker.php
      num 4                                    # 4 worker threads
      watch ./src ./config ./plugins           # Restart on changes (dev)
      name background-jobs
    }
  }
  
  # Full-duplex for WebSocket/SSE
  servers {
    enable_full_duplex
  }
}

:8080 {
  root * /app/webroot

  @static {
    path /css/*
    path /js/*
    path /images/*
    path /img/*
    path /fonts/*
    path /font/*
    path /favicon.ico
    path /robots.txt
    file
  }

  header @static Cache-Control "public, max-age=2592000, immutable"
  file_server @static

  encode gzip

  php_server {
    root /app/webroot
    split_path .php
    env DB_HOST 192.168.49.10
    env REDIS_HOST 192.168.49.10
  }
}
```

---

## 7. Deployment Checklist

### Pre-Flight
- [ ] Ensure PostgreSQL is running on `192.168.49.10:5432`
- [ ] Ensure Redis is running on `192.168.49.10:6379`
- [ ] Create database and run migrations
- [ ] Generate Let's Encrypt certificate (if using HTTPS)

### Files
- [ ] `Caddyfile` in app root
- [ ] `php.ini` in app root
- [ ] `.env` in app root with correct values
- [ ] Binary has execute permissions: `chmod +x ./frankenphp`

### Configuration
- [ ] Set `FULL_BASE_URL` environment variable
- [ ] Set `DB_HOST`, `DB_USERNAME`, `DB_PASSWORD`
- [ ] Set `REDIS_HOST`, `REDIS_PASSWORD`
- [ ] Verify `webroot/` exists and is readable

### Runtime
- [ ] Start FrankenPHP: `./frankenphp php-server`
- [ ] Visit `http://localhost:8080`
- [ ] Check static files load (CSS, JS - should be fast)
- [ ] Test dynamic pages load correctly
- [ ] Monitor logs for errors

---

## 8. Testing Performance

### Check Static File Serving
```bash
# Should be <5ms (served by Caddy)
time curl -I http://localhost:8080/css/bootstrap.min.css

# Should show cache headers
curl -I http://localhost:8080/css/bootstrap.min.css | grep Cache-Control
# Expected: Cache-Control: public, max-age=2592000, immutable
```

### Check Dynamic Request
```bash
# Should be 200-500ms (PHP processing)
time curl http://localhost:8080/

# Should show PHP is handling it
curl -I http://localhost:8080/ | grep X-Powered-By
```

### Check Compression
```bash
# Should show gzip encoding for dynamic content
curl -H "Accept-Encoding: gzip" -I http://localhost:8080/ | grep Content-Encoding
```

---

## 9. Troubleshooting

### 404 on static files
- Verify Caddyfile has `root * /app/webroot`
- Verify `@static` matcher includes the file extension
- Verify `file` condition in matcher

### PHP errors not showing
- Set `display_errors=1` in php.ini temporarily
- Check log file specified in `error_log`
- Use: `./frankenphp php-server` and watch console

### Port already in use
```bash
# Find process on port 8080
lsof -i :8080

# Kill it
kill -9 <PID>

# Or use different port
./frankenphp php-server -l 0.0.0.0:9000
```

### Database connection errors
- Verify PostgreSQL is running: `psql -h 192.168.49.10 -U postgres`
- Verify credentials in .env match database
- Check `DB_HOST`, `DB_USERNAME`, `DB_PASSWORD`

### Redis session errors
- Verify Redis is running: `redis-cli -h 192.168.49.10 ping`
- Verify password is correct
- Check session.save_path in php.ini

---

## 10. Production Recommendations

1. **Enable HTTPS:**
   ```bash
   ./frankenphp php-server --domain yourdomain.com
   ```

2. **Use systemd service:** Create `/etc/systemd/system/frankenphp.service`
   ```ini
   [Unit]
   Description=FrankenPHP OrangeScrum
   After=network.target postgresql.service redis.service
   
   [Service]
   Type=simple
   User=www-data
   WorkingDirectory=/opt/orangescrum
   ExecStart=/opt/orangescrum/frankenphp php-server --domain yourdomain.com
   Restart=always
   RestartSec=10
   
   [Install]
   WantedBy=multi-user.target
   ```
   
   Then:
   ```bash
   sudo systemctl enable frankenphp
   sudo systemctl start frankenphp
   ```

3. **Monitor with logs:**
   ```bash
   journalctl -u frankenphp -f
   ```

4. **Setup reverse proxy (nginx)** for multiple servers behind load balancer

5. **Use Redis for sessions** across load-balanced instances

---

## 11. Architecture Overview

```
┌─────────────────────────────────────────────────┐
│          FrankenPHP Static Binary                │
│              (single executable)                 │
├─────────────────────────────────────────────────┤
│                                                  │
│  ┌──────────────┐         ┌─────────────────┐  │
│  │    Caddy     │         │   PHP 8.3       │  │
│  │  Web Server  │         │  Interpreter    │  │
│  ├──────────────┤         ├─────────────────┤  │
│  │              │         │                 │  │
│  │ • Static     │         │ • OPcache       │  │
│  │   files      │         │ • Extensions    │  │
│  │ • Routing    │         │ • CakePHP       │  │
│  │ • TLS/HTTPS  │         │ • OrangeScrum   │  │
│  └──────────────┘         └─────────────────┘  │
│          ↓                        ↓              │
│    CSS/JS/Images (fast)      Dynamic requests  │
│    1-5ms response              200-500ms        │
│                                                  │
└─────────────────────────────────────────────────┘
         ↓
┌──────────────────┬──────────────────┐
│  PostgreSQL DB   │  Redis Sessions  │
│  192.168.49.10   │  192.168.49.10   │
└──────────────────┴──────────────────┘
```

---

## Summary

| Feature | Benefit |
|---------|---------|
| **Single Binary** | No dependencies, easy deployment |
| **Embedded Caddy** | HTTP/2, HTTPS, static file optimization |
| **OPcache** | 40-50% faster PHP |
| **Redis Sessions** | 5-10x faster sessions, scalable |
| **Gzip Compression** | 60-80% smaller responses |
| **Static Optimization** | 10-50x faster static files |

**Result:** Production-ready, high-performance PHP application deployable in seconds on any Linux system.
