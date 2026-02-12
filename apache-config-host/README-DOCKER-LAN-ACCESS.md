# Docker-Based LAN Access Setup

This setup is **system-agnostic** and runs entirely in Docker containers - no host installation required!

## Quick Start

### 1. Generate SSL Certificates
```bash
./generate-certs.sh
```

This creates certificates for both:
- `*.ossiba.local` (internal domain)
- `*.ossiba.com` (public/LAN domain)

### 2. Start Containers with Apache Proxy

**For local development only:**
```bash
docker compose up -d
```

**For LAN access (includes Apache on ports 80/443):**
```bash
docker compose --profile lan-access up -d
```

### 3. Configure Client Machines

**On LAN clients, add to hosts file:**

**Linux/Mac** (`/etc/hosts`):
```
192.168.2.111  v4.ossiba.com app.ossiba.com selfhosted.ossiba.com mail.ossiba.com
```

**Windows** (`C:\Windows\System32\drivers\etc\hosts`):
```
192.168.2.111  v4.ossiba.com app.ossiba.com selfhosted.ossiba.com mail.ossiba.com
```

Replace `192.168.2.111` with your server's LAN IP address.

## Architecture

```
LAN Client Browser
    ↓ (https://v4.ossiba.com)
Apache Container (ports 80/443)
    ↓ (rewrites Host: v4.ossiba.com → v4.ossiba.local)
Traefik Container (internal port 18643)
    ↓ (routes based on hostname)
Application Containers (PHP/Apache)
```

## Access URLs

**From LAN (via Apache proxy):**
- https://v4.ossiba.com - OrangeScrum V4
- https://selfhosted.ossiba.com - Durango PG
- https://app.ossiba.com - OrangeScrum V2
- https://mail.ossiba.com - MailHog

**From localhost (direct to Traefik):**
- https://v4.ossiba.local:18643 - OrangeScrum V4
- https://selfhosted.ossiba.local:18643 - Durango PG
- https://app.ossiba.local:18643 - OrangeScrum V2
- https://mail.ossiba.local:18643 - MailHog

## How It Works

1. **Apache Container** runs on standard ports 80/443
2. **Host header rewriting**: `*.ossiba.com` → `*.ossiba.local`
3. **Traefik** routes requests based on the rewritten hostname
4. **Application containers** receive properly routed traffic

## Benefits

✅ **System-agnostic**: Works on any OS with Docker  
✅ **No host dependencies**: No Apache installation needed on host  
✅ **Isolated**: All services run in containers  
✅ **Multi-tenant**: Each domain gets unique ports  
✅ **Profile-based**: Enable Apache only when needed

## Stopping Services

**Stop all containers:**
```bash
docker compose --profile lan-access down
```

**Stop Apache only (keep apps running):**
```bash
docker compose stop apache-proxy
```

## Troubleshooting

**Port conflicts:**
If ports 80/443 are in use, either stop the conflicting service or don't use the `lan-access` profile.

**SSL certificate warnings:**
You'll see browser warnings for self-signed certificates. This is normal for development. Import the certificate to your browser's trusted certificates to remove the warning.

**Container name resolution:**
The Apache container uses Docker DNS to resolve `ossiba-local-traefik`. This works automatically within the same Docker network.

## Development vs Production

**Development (localhost only):**
```bash
docker compose up -d
# Access via https://v4.ossiba.local:18643
```

**LAN Access (team/office):**
```bash
docker compose --profile lan-access up -d
# Access via https://v4.ossiba.com (from any machine on network)
```
