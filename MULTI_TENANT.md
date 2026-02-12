# Multi-Tenant Setup Guide

This OrangeScrum setup is designed to support **multiple developers/instances** on a single shared server.

## How It Works

### Automatic Port Assignment
Each domain gets **unique ports automatically** based on a hash of the domain name:

```
Port Offset Formula: MD5(domain) % 100 * 100
Example:
  - ossiba.local   → offset 0    → ports 8800-8900
  - dev1.local     → offset 600  → ports 9400-9500  
  - dev2.local     → offset 2300 → ports 11100-11200
```

### Your Instance Configuration

**Domain:** andolatraefik.online  
**Port Offset:** 1200

| Service | Port |
|---------|------|
| Traefik HTTP | 10000 |
| Traefik HTTPS | 10043 |
| Traefik Dashboard | 9200 |
| PostgreSQL | 6600 |
| MySQL | 4500 |
| Redis | 7500 |
| MinIO API | 10200 |
| MinIO Console | 10201 |
| Memcached (Durango) | 12400 |
| Memcached (V2) | 12401 |

## Running Multiple Instances

### Example: Three Developers on One Server

```bash
# Developer 1
cd /srv/orangescrum/dev1
./generate-config.py dev1.local -y
docker compose up -d

# Developer 2  
cd /srv/orangescrum/dev2
./generate-config.py dev2.local -y
docker compose up -d

# Developer 3
cd /srv/orangescrum/dev3
./generate-config.py dev3.local -y
docker compose up -d
```

Each instance gets:
- Unique Docker Compose project name: `orangescrum-dev1-local`, `orangescrum-dev2-local`, etc.
- Unique container names
- Unique ports (no conflicts)
- Separate databases and data
- Independent SSL certificates

### Apache Proxy Configuration

Install all Apache vhost configs:

```bash
# Dev1
sudo cp /srv/orangescrum/dev1/apache-config-host/apache-proxy.conf \
    /etc/apache2/sites-available/orangescrum-dev1-local.conf
sudo a2ensite orangescrum-dev1-local

# Dev2
sudo cp /srv/orangescrum/dev2/apache-config-host/apache-proxy.conf \
    /etc/apache2/sites-available/orangescrum-dev2-local.conf
sudo a2ensite orangescrum-dev2-local

# Dev3
sudo cp /srv/orangescrum/dev3/apache-config-host/apache-proxy.conf \
    /etc/apache2/sites-available/orangescrum-dev3-local.conf
sudo a2ensite orangescrum-dev3-local

sudo systemctl reload apache2
```

Apache will proxy each domain to its unique Traefik port:
- `dev1.local` → `127.0.0.1:10043`
- `dev2.local` → `127.0.0.1:[different port]`
- `dev3.local` → `127.0.0.1:[different port]`

## Benefits

✅ **No Port Conflicts** - Automatic unique port assignment  
✅ **Complete Isolation** - Each instance has separate data and containers  
✅ **Easy Management** - Standard Apache on :80/:443 for all domains  
✅ **Scalable** - Support 100+ instances on one server  
✅ **Development-Friendly** - Each developer can manage their own stack

## Troubleshooting

### Check Running Instances

```bash
# List all compose projects
docker compose ls

# Check specific instance
cd /srv/orangescrum/andolatraefik-online
docker compose ps

# View logs
docker compose logs -f traefik
```

### Port Conflicts

If you see port conflicts, the port offset algorithm has a collision (rare, 1% chance).
 
**Solution:** Choose a different domain name:
```bash
# Instead of: dev1.local
# Try: developer1.local or dev-john.local
```

### Database Access

Connect directly to your instance's database:
```bash
# PostgreSQL
psql -h 127.0.0.1 -p 6600 -U orangescrum -d orangescrum

# MySQL  
mysql -h 127.0.0.1 -P 4500 -u osuser -p orangescrum
```

## Resource Management

Each full instance uses approximately:
- **Memory:** 2-4 GB RAM
- **Storage:** 1-2 GB (depends on data)
- **Ports:** ~10-15 ports

For a shared server with 32GB RAM, you can comfortably run **5-8** full instances.
