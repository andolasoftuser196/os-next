# Apache → Traefik Reverse Proxy Setup

This configuration allows Apache (running on host ports 80/443) to reverse proxy to Traefik (running in Docker on ports 8880/8443).

## Architecture

```
Internet/Browser
       ↓
Apache (port 80/443) - Main web server with existing vhosts
       ↓
Traefik (port 8880/8443) - Docker reverse proxy (localhost only)
       ↓
Docker Containers (OrangeScrum apps, MailHog, MinIO, etc.)
```

## Quick Setup

### 1. Enable Apache Modules

```bash
sudo a2enmod proxy proxy_http proxy_wstunnel ssl rewrite headers
sudo systemctl restart apache2
```

### 2. Generate SSL Certificates

```bash
cd /workspaces/os-next
./generate-certs.sh
```

### 3. Install Apache Configuration

```bash
sudo cp /workspaces/os-next/apache-config-host/orangescrum-proxy.conf /etc/apache2/sites-available/
sudo a2ensite orangescrum-proxy
sudo apache2ctl configtest
sudo systemctl reload apache2
```

### 4. Update /etc/hosts

```bash
sudo tee -a /etc/hosts <<EOF
127.0.0.1 app.ossiba.local
127.0.0.1 v4.ossiba.local
127.0.0.1 selfhosted.ossiba.local
127.0.0.1 mail.ossiba.local
127.0.0.1 storage.ossiba.local
127.0.0.1 console.ossiba.local
127.0.0.1 traefik.ossiba.local
EOF
```

### 5. Start Docker Services

```bash
cd /workspaces/os-next
docker compose up -d
```

## Access URLs

All via Apache on standard ports (80/443):

- **https://app.ossiba.local** - Orangescrum V2
- **https://v4.ossiba.local** - OrangeScrum V4
- **https://selfhosted.ossiba.local** - Durango PG
- **https://mail.ossiba.local** - MailHog (email testing)
- **https://storage.ossiba.local** - MinIO S3 API
- **https://console.ossiba.local** - MinIO Console
- **https://traefik.ossiba.local** - Traefik Dashboard

## Port Configuration

Defined in [.env](.env):

```bash
TRAEFIK_HTTP_PORT=8880          # Internal HTTP (Apache proxies to this)
TRAEFIK_HTTPS_PORT=8443         # Internal HTTPS (Apache proxies to this)
TRAEFIK_DASHBOARD_PORT=8080     # Dashboard (localhost only)
```

## Troubleshooting

### Verify Apache is running
```bash
sudo systemctl status apache2
sudo netstat -tlnp | grep apache2
```

### Verify Traefik is running
```bash
docker compose ps traefik
sudo netstat -tlnp | grep 8443
```

### Test direct Traefik access
```bash
curl -k https://127.0.0.1:8443
```

### Check Apache proxy logs
```bash
sudo tail -f /var/log/apache2/orangescrum-proxy-error.log
sudo tail -f /var/log/apache2/v4-proxy-error.log
```

### Check Traefik logs
```bash
docker compose logs -f traefik
```

### Verify ProxyPreserveHost is working
```bash
# This should show the correct hostname being passed through
docker compose logs traefik | grep "Host:"
```

## Benefits

✅ Apache remains on standard ports 80/443  
✅ Existing Apache virtual hosts still work  
✅ Docker services isolated on non-standard ports  
✅ SSL handled by Apache (single certificate management)  
✅ ProxyPreserveHost ensures Traefik routes correctly  
✅ WebSocket support included
