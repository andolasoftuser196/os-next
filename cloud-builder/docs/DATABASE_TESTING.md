# Database Connectivity Test Guide

## Overview

OrangeScrum supports multiple database configuration scenarios:

1. **External DB via Container Name** - When DB is in another Docker container on same/shared network
2. **External DB via Host IP** - When DB is accessible via IP address (192.168.2.132:5432)
3. **External DB via Host Gateway** - Using Docker's host.docker.internal
4. **Bundled PostgreSQL** - Using Docker Compose bundled database (dev/test only)

## Test Results Summary

### ✅ Scenario 1: External DB via Container Name (durango-postgres-postgres-1)

**Status:** ✅ WORKING

**Configuration:**

```bash
DB_HOST=durango-postgres-postgres-1
DB_PORT=5432
DB_NAME=orangescrum-mt-test
APP_PORT=8081
```

**How to run:**

```bash
cd durango-builder/orangescrum-ee
docker compose --env-file .env.test-external-container up -d
curl -I http://localhost:8081  # Should return HTTP 302
docker compose --env-file .env.test-external-container down
```

**Requirements:**

- External PostgreSQL container must be running
- Both containers must be on shared Docker network (durango-postgres_default)
- docker-compose.yaml includes: `networks: durango-postgres_default: external: true`

---

### ⏳ Scenario 2: External DB via Host IP (192.168.2.132:5432)

**Status:** Ready to test

**Configuration:**

```bash
DB_HOST=192.168.2.132
DB_PORT=5432
DB_NAME=orangescrum-mt-test
APP_PORT=8082
```

**How to run:**

```bash
cd durango-builder/orangescrum-ee
docker compose --env-file .env.test-external-hostip up -d
curl -I http://localhost:8082  # Should return HTTP 302
docker compose --env-file .env.test-external-hostip down
```

**Requirements:**

- PostgreSQL must be accessible on 192.168.2.132:5432
- Firewall must allow connections from Docker network
- PostgreSQL pg_hba.conf must allow connections from Docker subnet

---

### ⏳ Scenario 3: External DB via host.docker.internal

**Status:** Ready to test

**Configuration:**

```bash
DB_HOST=host.docker.internal
DB_PORT=5432
DB_NAME=orangescrum-mt-test
APP_PORT=8083
```

**How to run:**

```bash
cd durango-builder/orangescrum-ee
docker compose --env-file .env.test-external-hostgateway up -d
curl -I http://localhost:8083  # Should return HTTP 302
docker compose --env-file .env.test-external-hostgateway down
```

**Requirements:**

- Docker Desktop or Docker with host-gateway support
- PostgreSQL accessible on host machine's localhost:5432
- extra_hosts configured in docker-compose.yaml

---

---

## Production Configuration

### For External Database (Recommended)

1. **Create `.env` file:**

    ```bash
    cd durango-builder/orangescrum-ee
    cp .env.example .env
    nano .env
    ```

2. **Configure external database:**

    ```bash
    # Production with external PostgreSQL
    COMPOSE_PROJECT_NAME=orangescrum-production
    APP_PORT=80

    # External database (choose appropriate method)
    DB_HOST=192.168.2.132          # Or container name or host.docker.internal
    DB_PORT=5432
    DB_USERNAME=orangescrum_user
    DB_PASSWORD=STRONG_PASSWORD_HERE
    DB_NAME=orangescrum_production
    ```

3. **Deploy:**

```bash
docker compose up -d
```

---

## Troubleshooting

### Cannot connect to external database

**Check network connectivity:**

```bash
# From host machine
nc -zv 192.168.2.132 5432
# Or
telnet 192.168.2.132 5432

# From container
docker exec orangescrum-app-1 wget -q -O - 192.168.2.132:5432
```

**Check Docker networks:**

```bash
# List networks
docker network ls

# Inspect external DB container's network
docker inspect durango-postgres-postgres-1 --format '{{range $net, $conf := .NetworkSettings.Networks}}{{$net}} {{end}}'

# Connect to same network
docker compose --env-file .env up -d
```

**Check PostgreSQL configuration:**

```bash
# Check pg_hba.conf allows Docker subnet
docker exec durango-postgres-postgres-1 cat /var/lib/postgresql/data/pg_hba.conf | grep -v "^#"

# Should include line like:
# host all all 0.0.0.0/0 md5
# Or specific Docker subnet:
# host all all 172.17.0.0/16 md5
```

### Database exists but app cannot connect

**Check credentials:**

```bash
# Test connection manually
docker exec durango-postgres-postgres-1 \
  psql -U postgres -d orangescrum-mt-test -c "SELECT version();"
```

**Check environment variables in container:**

```bash
docker exec orangescrum-app-1 env | grep DB_
```

**Check application logs:**

```bash
docker logs orangescrum-app-1 | grep -i "database\|connect\|error"
```

### Container starts but HTTP doesn't respond

**Wait for health check:**

```bash
# Health check takes 40 seconds (start_period)
docker ps
# Wait for status to show "healthy"

# Check logs
docker logs orangescrum-app-1 --tail 50
```

**Test manually:**

```bash
curl -v http://localhost:8081
# Should get HTTP 302 redirect
```

---

## Network Configuration Reference

### docker-compose.yaml network settings

```yaml
services:
  orangescrum-app:
    networks:
      - orangescrum-network        # Internal network
      - durango-postgres_default   # External DB network
    extra_hosts:
      - "host.docker.internal:host-gateway"  # For host DB access

networks:
  orangescrum-network:
    driver: bridge
  durango-postgres_default:
    external: true  # Connect to existing network
```

### Environment variable reference

| Variable | Description | Example |
|----------|-------------|---------|
| DB_HOST | Database hostname/IP | `192.168.2.132` or `durango-postgres-postgres-1` |
| DB_PORT | Database port | `5432` |
| DB_USER | Database username | `postgres` or `orangescrum_user` |
| DB_PASSWORD | Database password | Use strong password! |
| DB_NAME | Database name | `orangescrum-production` |
| APP_PORT | Application HTTP port | `80` or `8080` |
| COMPOSE_PROJECT_NAME | Docker Compose project name | `orangescrum-production` |

---

## Database Setup on External PostgreSQL

### Create database and user

```bash
# Connect to PostgreSQL
docker exec -it durango-postgres-postgres-1 psql -U postgres

# Create user
CREATE USER orangescrum_user WITH PASSWORD 'strong_password_here';

# Create database
CREATE DATABASE orangescrum_production OWNER orangescrum_user;

# Grant privileges
GRANT ALL PRIVILEGES ON DATABASE orangescrum_production TO orangescrum_user;

# Exit
\q
```

### Verify database

```bash
docker exec durango-postgres-postgres-1 \
  psql -U postgres -c "\l" | grep orangescrum
```

---

## Summary

✅ **External DB:** Recommended configuration path  
📝 **Documentation:** Setup and troubleshooting guide  

**Production Ready:** Yes, with proper .env configuration for your database setup.
