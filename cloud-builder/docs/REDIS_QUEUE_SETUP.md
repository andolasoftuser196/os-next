# Redis Cache & Queue Setup Guide

This guide explains how to configure Redis for caching and queue management in OrangeScrum.

---

## Overview

Redis provides:
- **Fast caching**: In-memory cache (faster than file-based)
- **Queue backend**: Reliable job queue for background tasks
- **Distributed support**: Share cache/queue across multiple app instances

---

## Quick Start

### 1. Enable Redis Services

```bash
cd orangescrum-ee

# Option A: Enable both Redis and Queue Worker
docker compose --profile redis --profile queue up -d

# Option B: Enable only Redis (no queue worker)
docker compose --profile redis up -d

# Option C: Full deployment with all services
docker compose --profile redis --profile queue up -d --build
```

### 2. Configure Environment

Edit `.env`:

```bash
# Application Configuration
DEBUG=false
CACHE_ENGINE=redis    # Switch from 'file' to 'redis'
QUEUE_ENGINE=redis    # Use Redis for queue backend

# Redis Configuration
REDIS_HOST=redis      # Use docker-compose service name
REDIS_PORT=6379
REDIS_PASSWORD=       # Optional: set password for production
REDIS_DATABASE=0      # Database number (0-15)
REDIS_BIND_IP=127.0.0.1  # Bind to localhost only

# Queue Worker Configuration
WORKER_MAX_RUNTIME=1800  # 30 minutes max runtime per worker
WORKER_SLEEP=5          # Check queue every 5 seconds
```

### 3. Restart Application

```bash
# Restart app with new configuration
docker compose --profile redis --profile queue down
docker compose --profile redis --profile queue up -d --build
```

---

## Service Architecture

```
┌─────────────────────────────────────┐
│   orangescrum-app (Port 8080)      │
│   - Handles web requests            │
│   - Dispatches jobs to queue       │
│   - Reads/writes cache             │
└──────────┬────────────┬─────────────┘
           │            │
           ↓            ↓
    ┌──────────┐  ┌──────────────┐
    │  Redis   │  │ Queue Worker │
    │ Port 6379│  │ (Background) │
    └──────────┘  └──────────────┘
         ↓               ↓
    Cache & Queue   Processes Jobs
```

---

## Configuration Files

### Redis Cache Configuration

The application uses `config/cache_redis.php` when `CACHE_ENGINE=redis`:

```php
'Cache' => [
    'default' => [
        'className' => RedisEngine::class,
        'host' => env('REDIS_HOST', 'localhost'),
        'port' => (int)env('REDIS_PORT', 6379),
        'password' => env('REDIS_PASSWORD', null),
        'database' => (int)env('REDIS_DATABASE', 0),
        'prefix' => env('REDIS_PREFIX', 'cake_') . 'default_',
        'duration' => '+1 hours',
    ],
    // ... other cache configs
]
```

### Queue Configuration

The application uses `config/queue.php` when `QUEUE_ENGINE=redis`:

```php
'Queue' => [
    'default' => [
        'url' => env('QUEUE_URL', 'redis://127.0.0.1:6379'),
        'queue' => 'default',
        'logger' => 'stdout',
        'storeFailedJobs' => true,
        'receiveTimeout' => 10000,
    ],
]
```

---

## Using the Queue System

### Dispatch Jobs from Code

```php
// In your controller or service
use Cake\Queue\QueueManager;

// Dispatch a job to the queue
QueueManager::push('SendEmail', [
    'to' => 'user@example.com',
    'subject' => 'Welcome!',
    'template' => 'welcome'
]);

// Dispatch with delay
QueueManager::push('GenerateReport', [
    'reportId' => 123
], [
    'delay' => 300 // Wait 5 minutes before processing
]);
```

### Create Queue Jobs

Create a job class in `src/Queue/`:

```php
<?php
namespace App\Queue;

use Cake\Queue\Job\JobInterface;
use Interop\Queue\Processor;

class SendEmailJob implements JobInterface
{
    public function execute($data): ?string
    {
        // Process the job
        $email = new Email('default');
        $email->setTo($data['to'])
              ->setSubject($data['subject'])
              ->send();
        
        return Processor::ACK; // Job completed successfully
    }
}
```

### Monitor Queue Worker

```bash
# View queue worker logs
docker logs -f orangescrum-cloud-queue-worker-1

# Check worker status
docker ps | grep queue-worker

# Restart worker
docker compose --profile queue restart queue-worker
```

---

## Production Deployment

### External Redis Server

For production, use an external Redis server:

```bash
# .env configuration
REDIS_HOST=redis.production.example.com  # External Redis
REDIS_PORT=6379
REDIS_PASSWORD=your-strong-password-here
REDIS_DATABASE=0

# Use profiles for production
docker compose --profile redis --profile queue up -d
```

### Redis Security

1. **Enable authentication**:
```bash
REDIS_PASSWORD=<generate-strong-password>
```

2. **Restrict network access**:
```bash
# Only allow app to connect
REDIS_BIND_IP=127.0.0.1
```

3. **Use firewall rules**:
```bash
# Only allow from app server IP
iptables -A INPUT -p tcp --dport 6379 -s <app-server-ip> -j ACCEPT
iptables -A INPUT -p tcp --dport 6379 -j DROP
```

### Scaling Queue Workers

Run multiple workers for high load:

```yaml
# docker-compose.yaml
queue-worker:
  # ... existing config
  deploy:
    replicas: 3  # Run 3 worker instances
```

Or manually scale:
```bash
docker compose --profile queue up -d --scale queue-worker=3
```

---

## Monitoring

### Redis Monitoring

```bash
# Connect to Redis CLI
docker exec -it orangescrum-cloud-redis-1 redis-cli

# Inside Redis CLI:
INFO             # Server information
DBSIZE           # Number of keys
KEYS cake_*      # List cache keys
MONITOR          # Watch commands in real-time
```

### Queue Statistics

```bash
# Check queue stats via CakePHP CLI
docker exec orangescrum-cloud-orangescrum-app-1 \
  sh -c 'cd /tmp/frankenphp_* && /orangescrum-app/orangescrum-ee php-cli bin/cake.php queue stats'

# View failed jobs
docker exec orangescrum-cloud-orangescrum-app-1 \
  sh -c 'cd /tmp/frankenphp_* && /orangescrum-app/orangescrum-ee php-cli bin/cake.php queue failed'

# Retry failed jobs
docker exec orangescrum-cloud-orangescrum-app-1 \
  sh -c 'cd /tmp/frankenphp_* && /orangescrum-app/orangescrum-ee php-cli bin/cake.php queue retry'
```

---

## Troubleshooting

### Redis Connection Issues

```bash
# Test Redis connectivity from app container
docker exec orangescrum-cloud-orangescrum-app-1 sh -c "
  redis-cli -h redis -p 6379 ping
"

# Expected output: PONG

# Check Redis logs
docker logs orangescrum-cloud-redis-1
```

### Queue Worker Not Processing Jobs

1. **Check worker is running**:
```bash
docker ps | grep queue-worker
```

2. **View worker logs**:
```bash
docker logs -f orangescrum-cloud-queue-worker-1
```

3. **Verify queue configuration**:
```bash
# Check environment variables
docker exec orangescrum-cloud-queue-worker-1 env | grep -E "QUEUE|REDIS"
```

4. **Manually run worker for debugging**:
```bash
docker exec -it orangescrum-cloud-orangescrum-app-1 sh -c "
  cd /tmp/frankenphp_* && 
  /orangescrum-app/orangescrum-ee php-cli bin/cake.php queue worker --verbose
"
```

### Cache Not Working

1. **Verify CACHE_ENGINE setting**:
```bash
docker exec orangescrum-cloud-orangescrum-app-1 env | grep CACHE_ENGINE
# Should show: CACHE_ENGINE=redis
```

2. **Check cache_redis.php exists**:
```bash
docker exec orangescrum-cloud-orangescrum-app-1 sh -c "
  ls -la /tmp/frankenphp_*/config/cache_redis.php
"
```

3. **Test cache operations**:
```bash
docker exec orangescrum-cloud-orangescrum-app-1 sh -c "
  cd /tmp/frankenphp_* && 
  /orangescrum-app/orangescrum-ee php-cli bin/cake.php cache clear_all
"
```

---

## Performance Tuning

### Redis Configuration

Create `redis.conf` for custom Redis settings:

```conf
# Memory
maxmemory 512mb
maxmemory-policy allkeys-lru

# Persistence
save 900 1
save 300 10
save 60 10000
appendonly yes
appendfsync everysec

# Network
timeout 300
tcp-keepalive 60

# Performance
maxclients 10000
```

Mount in docker-compose:
```yaml
redis:
  volumes:
    - ./redis.conf:/usr/local/etc/redis/redis.conf
    - redis-data:/data
  command: redis-server /usr/local/etc/redis/redis.conf
```

### Queue Worker Optimization

```bash
# .env settings for high performance
WORKER_MAX_RUNTIME=3600    # 1 hour per worker
WORKER_SLEEP=1             # Check every 1 second (faster response)

# Resource limits in docker-compose.yaml
queue-worker:
  deploy:
    replicas: 4              # Run 4 workers
    resources:
      limits:
        cpus: '2'
        memory: 2G
```

---

## Migration from File Cache

### Step 1: Backup Current Setup

```bash
# Backup file cache
docker exec orangescrum-cloud-orangescrum-app-1 sh -c "
  tar -czf /data/cache-backup.tar.gz /tmp/frankenphp_*/tmp/cache
"
```

### Step 2: Enable Redis

```bash
# Update .env
CACHE_ENGINE=redis
REDIS_HOST=redis
```

### Step 3: Start Redis Service

```bash
docker compose --profile redis up -d
```

### Step 4: Clear Old Cache

```bash
docker exec orangescrum-cloud-orangescrum-app-1 sh -c "
  cd /tmp/frankenphp_* && 
  /orangescrum-app/orangescrum-ee php-cli bin/cake.php cache clear_all
"
```

### Step 5: Restart Application

```bash
docker compose restart orangescrum-app
```

---

## Common Queue Job Examples

### Email Sending

```php
QueueManager::push('SendEmail', [
    'to' => 'user@example.com',
    'subject' => 'Welcome',
    'message' => 'Welcome to OrangeScrum!'
]);
```

### Report Generation

```php
QueueManager::push('GenerateReport', [
    'type' => 'project_summary',
    'projectId' => 123,
    'format' => 'pdf'
]);
```

### Data Import

```php
QueueManager::push('ImportData', [
    'file' => '/uploads/data.csv',
    'type' => 'users'
], [
    'delay' => 60  // Wait 1 minute
]);
```

### Scheduled Tasks

```php
// In a cron job or recurring task
QueueManager::push('DailyCleanup', [
    'retention' => 30  // Days
]);
```

---

## Docker Compose Profiles

The setup uses Docker Compose profiles for flexible deployment:

| Profile | Services | Use Case |
|---------|----------|----------|
| *(default)* | orangescrum-app | App only, file cache |
| `redis` | app + redis | App with Redis cache |
| `queue` | app + queue-worker | App with queue worker |
| `redis,queue` | app + redis + queue-worker | Full setup |

Examples:
```bash
# App only (file cache)
docker compose up -d

# App + Redis cache
docker compose --profile redis up -d

# App + Queue worker (requires Redis)
docker compose --profile redis --profile queue up -d

# All services
docker compose --profile redis --profile queue up -d
```

---

## Summary

**To enable Redis cache and queue:**

1. Edit `.env`:
   ```bash
   CACHE_ENGINE=redis
   QUEUE_ENGINE=redis
   REDIS_HOST=redis
   ```

2. Start services:
   ```bash
   docker compose --profile redis --profile queue up -d
   ```

3. Verify:
   ```bash
   docker ps  # Should see redis and queue-worker
   docker logs orangescrum-cloud-queue-worker-1  # Check worker logs
   ```

**Performance gains:**
- Cache: 10-100x faster than file-based
- Queue: Reliable background job processing
- Scalability: Multiple workers, distributed cache

