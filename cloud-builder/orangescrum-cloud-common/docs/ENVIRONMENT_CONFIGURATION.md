# Environment Configuration Architecture

## Overview

OrangeScrum FrankenPHP uses a layered environment configuration system that allows the application to be configured via environment variables without modifying code. This document explains how configuration flows from environment variables to the application.

---

## Configuration Flow

```
.env file → Environment Variables → FrankenPHP Binary → PHP env() → CakePHP Config Files
```

### 1. Environment Variable Sources

**Docker Mode:**

```yaml
# docker-compose.yaml
environment:
  DB_HOST: ${DB_HOST:-192.168.2.132}
  REDIS_HOST: ${REDIS_HOST:-localhost}
  FULL_BASE_URL: ${FULL_BASE_URL:-}
```

- Variables from `.env` file are passed to container
- Docker Compose syntax: `${VAR:-default}` provides fallback values

**Native Mode:**

```bash
# run.sh loads .env
source .env
export DB_HOST DB_PORT DB_USERNAME ...
./orangescrum-app/osv4-prod php-server --listen :8080
```

- Script loads `.env` file with `source`
- Exports variables to process environment
- FrankenPHP binary inherits all exported variables

---

## 2. Environment File Structure

### .env File Location

```
durango-builde./osv4-prod/.env
```

### Variable Categories

#### Database Configuration

```bash
DB_HOST=192.168.2.132
DB_PORT=5432
DB_USERNAME=postgres
DB_PASSWORD=postgres
DB_NAME=orangescrum-subscription-new-3
```

#### Redis Configuration

```bash
REDIS_HOST=192.168.2.132
REDIS_PORT=6379
REDIS_PASSWORD=your-secure-password
REDIS_DATABASE=0
REDIS_PREFIX=test_cache_
REDIS_TIMEOUT=5
REDIS_TLS_ENABLED=false
REDIS_TLS_VERIFY_PEER=false
```

#### Application URL

```bash
FULL_BASE_URL=https://durango.ossiba.online
```

#### Email (SendGrid)

```bash
EMAIL_TRANSPORT=sendgrid
EMAIL_API_KEY=SG.xxx
FROM_EMAIL=noreply@example.com
NOTIFY_EMAIL=admin@example.com
```

#### Storage (S3)

```bash
STORAGE_ENDPOINT=https://s3.amazonaws.com
STORAGE_ACCESS_KEY=AKIAXXXXXXXX
STORAGE_SECRET_KEY=xxxxx
STORAGE_BUCKET=my-bucket
STORAGE_REGION=us-east-1
STORAGE_PATH_STYLE=false
```

#### Google Services

```bash
RECAPTCHA_ENABLED=true
RECAPTCHA_SITE_KEY=6Lxxx
RECAPTCHA_SECRET_KEY=6Lxxx
RECAPTCHA_VERSION=v2

GOOGLE_OAUTH_ENABLED=true
GOOGLE_OAUTH_CLIENT_ID=xxx.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=GOCSPX-xxx
GOOGLE_OAUTH_REDIRECT_URI=https://example.com/auth/callback
```

#### Session & Security

```bash
SESSION_HANDLER=cache
SESSION_COOKIE_DOMAIN=.ossiba.online
SECURITY_SALT=your-random-salt-here
DEBUG=false
```

---

## 3. Configuration File System

### Config Override Mechanism

#### Build Time (Static Binary)

```python
# build.py - Config Override Process
def _copy_config_overrides():
    """Copy modified configs from orangescrum-cloud/config/ to package/config/"""
    config_files = [
        'app_local.example.php',
        'cache_redis.example.php',
        'queue.example.php',
        'sendgrid.example.php',
        'storage.example.php',
        'recaptcha.example.php',
        'google_oauth.example.php'
    ]
    
    # These files are embedded into the binary
    for config in config_files:
        shutil.copy2(
            f"orangescrum-cloud/config/{config}",
            f"builder/package/config/{config}"
        )
```

**Key Point:** Config files are embedded into the FrankenPHP binary at build time. They cannot be changed without rebuilding the binary.

#### Runtime (Container/Native)

```bash
# entrypoint.sh or run.sh
# After FrankenPHP extracts app to /tmp/frankenphp_*

cp $EXTRACTED_APP/config/app_local.example.php \
   $EXTRACTED_APP/config/app_local.php

cp $EXTRACTED_APP/config/cache_redis.example.php \
   $EXTRACTED_APP/config/cache_redis.php

# ... repeat for all 7 config files
```

**Key Point:** `.example.php` files are copied to `.php` files at runtime. The `.php` files are what CakePHP actually loads.

---

## 4. How Config Files Use Environment Variables

### Example: app_local.example.php

```php
<?php
return [
    'debug' => filter_var(env('DEBUG', false), FILTER_VALIDATE_BOOLEAN),
    
    'Security' => [
        'salt' => env('SECURITY_SALT', '__SALT__'),
    ],
    
    'Datasources' => [
        'default' => [
            'host' => env('DB_HOST', 'orangescrum-db'),
            'port' => env('DB_PORT', '5432'),
            'username' => env('DB_USERNAME', 'orangescrum'),
            'password' => env('DB_PASSWORD', 'changeme'),
            'database' => env('DB_NAME', 'orangescrum'),
        ],
    ],
    
    'App.fullBaseUrl' => env('FULL_BASE_URL', ''),
    'App.trustProxy' => true,
];
```

**How `env()` Works:**

```php
env('DB_HOST', 'default-value')
// 1. Checks PHP's getenv('DB_HOST')
// 2. Returns value if set
// 3. Returns 'default-value' if not set
```

### Example: cache_redis.example.php

```php
<?php
function buildRedisConfig() {
    $config = [
        'className' => 'Cake\Cache\Engine\RedisEngine',
        'host' => env('REDIS_HOST', 'localhost'),
        'port' => env('REDIS_PORT', '6379'),
        'password' => env('REDIS_PASSWORD', ''),
        'database' => env('REDIS_DATABASE', '0'),
        'prefix' => env('REDIS_PREFIX', 'cake_'),
        'timeout' => env('REDIS_TIMEOUT', '1'),
    ];
    
    // Conditional TLS based on environment
    if (filter_var(env('REDIS_TLS_ENABLED', 'false'), FILTER_VALIDATE_BOOLEAN)) {
        $config['tls'] = true;
        $config['ssl'] = [
            'verify_peer' => filter_var(
                env('REDIS_TLS_VERIFY_PEER', 'true'), 
                FILTER_VALIDATE_BOOLEAN
            ),
        ];
    }
    
    return $config;
}

return [
    'Cache' => [
        'default' => buildRedisConfig(),
        '_cake_core_' => buildRedisConfig(),
        '_cake_model_' => buildRedisConfig(),
    ],
];
```

---

## 5. Application Bootstrap Process

### Startup Sequence

```
1. FrankenPHP Binary Starts
   └─> Extracts embedded app to /tmp/frankenphp_XXXXX/

2. Entrypoint/Script Copies Configs
   └─> cp *.example.php → *.php

3. CakePHP Bootstrap (config/bootstrap.php)
   ├─> Loads config/app.php (base configuration)
   ├─> Loads config/app_local.php (local overrides)
   ├─> Loads config/cache_redis.php (if exists)
   ├─> Loads config/queue.php (if exists)
   ├─> Loads config/sendgrid.php (if exists)
   └─> Loads config/storage.php (if exists)

4. Bootstrap Reads Environment Variables
   └─> All env() calls resolve to actual values

5. Router Configured
   └─> Router::fullBaseUrl($fullBaseUrl) sets base URL

6. Application Ready
   └─> HTTP requests processed with configured settings
```

### Bootstrap Code (Simplified)

```php
// config/bootstrap.php

// Load local configuration
Configure::load('app_local', 'default');

// Load cache configuration
if (file_exists(CONFIG . 'cache_redis.php')) {
    Configure::load('cache_redis', 'default');
}

// Load queue configuration
if (file_exists(CONFIG . 'queue.php')) {
    Configure::load('queue', 'default');
}

// Set full base URL for the application
$fullBaseUrl = Configure::read('App.fullBaseUrl');
if ($fullBaseUrl) {
    Router::fullBaseUrl($fullBaseUrl);
}
```

---

## 6. Configuration Priority

When the same setting appears in multiple places:

```
Environment Variable (highest priority)
    ↓
.env file default
    ↓
Config file env() default parameter
    ↓
app.php base configuration (lowest priority)
```

### Example Flow

For `DB_HOST`:

```
1. Check: getenv('DB_HOST')
   → If set: use "192.168.2.132"
   
2. If not set, check env() default:
   → env('DB_HOST', 'orangescrum-db')
   → Returns 'orangescrum-db'
   
3. If no default in env(), check app.php:
   → May have 'localhost' as base default
```

---

## 7. Special Configuration Cases

### Redis TLS (Conditional Logic)

```php
// Only enable TLS if environment variable is true
if (filter_var(env('REDIS_TLS_ENABLED', 'false'), FILTER_VALIDATE_BOOLEAN)) {
    $config['tls'] = true;
    // Additional TLS configuration
}
```

**Why:** Local Redis doesn't use TLS, but AWS ElastiCache does. The same config file works for both environments by checking the env var.

### Proxy Trust (SSL Termination)

```php
'App.trustProxy' => true,
```

**Why:** When running behind Apache/Nginx with SSL termination, CakePHP must trust the `X-Forwarded-Proto` header to correctly detect HTTPS.

### Session Handler

```bash
SESSION_HANDLER=cache  # Use Redis for sessions
# vs
SESSION_HANDLER=database  # Use PostgreSQL for sessions
```

**Why:** Stateless architecture requires sessions in Redis, not database, to avoid early database dependency during bootstrap.

---

## 8. Troubleshooting

### Check if environment variables are loaded

```bash
# Inside container
docker exec orangescrum-cloud-orangescrum-app-1 env | grep DB_

# Native mode
./orangescrum-app/osv4-prod php-cli -r "echo getenv('DB_HOST');"
```

### Verify config file exists

```bash
# Inside container
docker exec orangescrum-cloud-orangescrum-app-1 ls -la /tmp/frankenphp_*/config/

# Native mode
ls -la /tmp/frankenphp_*/config/
```

### Test database connection

```bash
# Using healthcheck
curl http://localhost:8080/home/healthcheck

# Direct test
./orangescrum-app/osv4-prod php-cli -r "
\$conn = pg_connect('host=192.168.2.132 port=5432 dbname=orangescrum user=postgres password=postgres');
echo \$conn ? 'Connected' : 'Failed';
"
```

### Common Issues

#### Environment variables not picked up

- **Docker:** Check `docker-compose.yaml` has the variable listed
- **Native:** Verify `.env` file is being sourced
- **Both:** Restart the process after changing `.env`

#### Config file not loaded

- Check if `.example.php` was copied to `.php`
- Verify file has correct permissions (readable)
- Check CakePHP bootstrap.php loads the config

#### Placeholder constants still present

- Old issue: `__EMAIL_API_KEY__` instead of `env('EMAIL_API_KEY')`
- Solution: Rebuild binary to embed updated config files
- Command: `python build.py --skip-deploy`

---

## 9. Best Practices

### Development

```bash
# Use .env file for all settings
# Never hardcode credentials in config files
DEBUG=true
DB_HOST=localhost
REDIS_HOST=localhost
```

### Production

```bash
# Disable debug
DEBUG=false

# Use strong security salt
SECURITY_SALT=$(openssl rand -base64 32)

# Use secure Redis password
REDIS_PASSWORD=$(openssl rand -base64 24)

# Set proper base URL
FULL_BASE_URL=https://app.<your-domain>

# Enable TLS for AWS ElastiCache
REDIS_TLS_ENABLED=true
```

### Environment Variable Naming

- Use UPPERCASE with underscores
- Be descriptive: `EMAIL_API_KEY` not `EMAIL_KEY`
- Group related vars: `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`
- Include units when relevant: `REDIS_TIMEOUT` (seconds implied)

---

## 10. Summary

The environment configuration system works through this chain:

1. **Define** variables in `.env` file
2. **Load** variables into process environment (Docker Compose or shell script)
3. **Embed** config templates (`.example.php`) into FrankenPHP binary at build time
4. **Copy** templates to active configs (`.php`) at runtime
5. **Read** environment variables using `env()` function in config files
6. **Apply** configuration during CakePHP bootstrap
7. **Use** configured services (database, cache, email, storage)

**Key Insight:** The configuration is **declarative** (defined in `.env`) and **portable** (same binary works in different environments by changing environment variables only).
