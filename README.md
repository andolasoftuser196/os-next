# OrangeScrum Multi-Environment Docker Setup

Complete Docker setup for OrangeScrum with multiple versions and environments:

- **V2 (Orangescrum)**: PHP 7.2 + MySQL 8.0
- **V4 (OrangeScrum)**: PHP 8.3 + PostgreSQL 16
- **V4 (Durango PG)**: PHP 8.3 + PostgreSQL 16

## Quick Start

```bash
# 1. Run setup script
./setup.sh ossiba.online

# 2. Start services
docker compose up -d

# 3. Setup databases
./setup-v2-database.sh      # For V2 Orangescrum (MySQL)
./setup-databases.sh        # For V4 Durango PG (PostgreSQL)
```

## Access Points

| Service | URL | Description |
| --------- | ----- | ------------- |
| **V2 (Orangescrum)** | <https://app.ossiba.online> | PHP 7.2 + MySQL (wildcard: *.ossiba.online) |
| **V4 (OrangeScrum)** | <https://v4.ossiba.online> | PHP 8.3 + PostgreSQL (orangescrum DB) |
| **V4 (Durango PG)** | <https://selfhosted.ossiba.online> | PHP 8.3 + PostgreSQL (durango DB) |
| **MailHog** | <https://mail.ossiba.online> | Email testing interface |
| **MinIO API** | <https://storage.ossiba.online> | S3-compatible storage |
| **MinIO Console** | <https://console.ossiba.online> | Storage management UI |
| **Traefik Dashboard** | <https://traefik.ossiba.online/dashboard/> | Reverse proxy dashboard |

## Services

### Application Servers

- **durango-pg**: PHP 8.3 with Apache (PostgreSQL database: `durango`)
- **orangescrum-v4**: PHP 8.3 with Apache (PostgreSQL database: `orangescrum`)
- **orangescrum**: PHP 7.2 with Apache (MySQL database)

### Databases

- **postgres16**: PostgreSQL 16.10 (port 5433)
  - Database: `durango` (user: `durango`)
  - Database: `orangescrum` (user: `orangescrum`)
- **mysql**: MySQL 8.0 (port 3307)
  - Database: `orangescrum` (user: `osuser`)

### Caching & Queue

- **redis-durango**: Redis 7 for V4 queue (port 6380)
- **memcached-durango**: Memcached for V4 apps (port 11212)
- **memcached-orangescrum**: Memcached for V2 (port 11213)

### Storage & Infrastructure

- **minio**: S3-compatible object storage (API: 9000, Console: 9001)
- **traefik**: Reverse proxy with automatic SSL (ports 80, 443)
- **mailhog**: SMTP server for testing (SMTP: 1025, Web: 8025)
- **browser**: Selenium Chrome with VNC (WebDriver: 4444, VNC: 5900, noVNC: 7900)

## Environment Configuration

Each application has its own environment file:

```plaintext
os-pg/.env          # Durango PG configuration (durango database)
os-v4/.env          # OrangeScrum V4 configuration (orangescrum database)  
os-v2/.env          # Orangescrum V2 configuration (MySQL)
.env                # Port mappings and infrastructure settings
```

## Port Mappings

All ports are bound to `127.0.0.1` for security and configurable via `.env`:

```bash
TRAEFIK_HTTP_PORT=80          # HTTP (redirects to HTTPS)
TRAEFIK_HTTPS_PORT=443        # HTTPS
TRAEFIK_DASHBOARD_PORT=8080   # Dashboard (localhost only)
MYSQL_PORT=3307               # MySQL direct access
POSTGRES_PORT=5433            # PostgreSQL direct access
REDIS_PORT=6380               # Redis direct access
MINIO_API_PORT=9000           # MinIO S3 API
MINIO_CONSOLE_PORT=9001       # MinIO Console
MEMCACHED_DURANGO_PORT=11212  # V4 Memcached
MEMCACHED_ORANGESCRUM_PORT=11213  # V2 Memcached
```

## Common Commands

```bash
# Service Management
docker compose up -d              # Start all services
docker compose down               # Stop all services
docker compose ps                 # List running services
docker compose logs -f [service]  # Follow logs

# Database Operations
./setup-v2-database.sh            # Import V2 MySQL database
./setup-v2-database.sh --force    # Force reset and reimport
./setup-databases.sh              # Setup V4 PostgreSQL databases
./setup-databases.sh --force      # Force reset and reimport

# Configuration
./generate-config.py ossiba.online  # Regenerate all configs
./generate-certs.sh               # Generate SSL certificates
./dev-deploy.sh                   # Verify and deploy services

# Individual Services
docker compose restart traefik    # Restart reverse proxy
docker compose restart durango-pg # Restart Durango app
docker compose up -d orangescrum-v4  # Start OrangeScrum V4
```

## Database Access

### PostgreSQL (port 5433)

```bash
# Durango database
psql -h localhost -p 5433 -U durango -d durango

# OrangeScrum database  
psql -h localhost -p 5433 -U orangescrum -d orangescrum
```

### MySQL (port 3307)

```bash
mysql -h 127.0.0.1 -P 3307 -u osuser -p orangescrum
```

## Development Workflow

1. **Change domain**: Edit `generate-config.py ossiba.online` with new domain
2. **Regenerate SSL**: Run `./generate-certs.sh`
3. **Apply changes**: Run `docker compose up -d`
4. **Reset database**: Use `--force` flag with setup scripts

## Troubleshooting

### Service won't start

```bash
docker compose logs -f [service-name]
docker compose restart [service-name]
```

### SSL certificate issues

```bash
./generate-certs.sh              # Regenerate certificates
./php-trust-certs.sh             # Trust in PHP containers
```

### Database connection issues

```bash
docker compose ps                # Check service health
./setup-databases.sh             # Re-run database setup
```

### Port conflicts

Edit `.env` and change conflicting ports, then:

```bash
docker compose down
docker compose up -d
```

## Network Architecture

- **traefik-network** (172.25.0.0/16): Public-facing services
- **durango-backend** (172.26.0.0/16): V4 app internal network
- **orangescrum-backend** (172.27.0.0/16): V2 app internal network

## File Structure

```plaintext
project-durango/
├── apps/                      # Application code (gitignored)
│   ├── durango-pg/           # Durango PG app
│   ├── orangescrum-v4/       # OrangeScrum V4 app
│   └── orangescrum/          # OrangeScrum V2 app
├── config/                    # Apache & PHP configs
├── certs/                     # SSL certificates
├── os-pg/.env                # Durango PG environment
├── os-v4/.env                # OrangeScrum V4 environment
├── os-v2/.env                # OrangeScrum V2 environment
├── postgres-init/            # PostgreSQL init scripts
├── templates/                # Jinja2 configuration templates
├── traefik/                  # Traefik dynamic configuration
├── docker-compose.yml        # Main service definitions
├── docker-compose.override.yml  # Port mappings (optional)
├── generate-config.py        # Configuration generator
├── setup.sh                  # Complete setup script
└── dev-deploy.sh            # Deployment verification script
```

## MinIO S3 Storage

Default credentials (change in `.env`):

```env
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
```

Access:

- Console UI: <https://console.ossiba.online>
- S3 API: <https://storage.ossiba.online>

## Chrome Browser Testing

VNC access for browser automation:

- **WebDriver**: <http://localhost:4444>
- **VNC**: vnc://localhost:5900
- **noVNC Web**: <http://localhost:7900>

## License

See individual application licenses in their respective directories.
