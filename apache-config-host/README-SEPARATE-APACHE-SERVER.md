# Apache Reverse Proxy on Separate LAN Server

This guide explains how to set up Apache reverse proxy on a **different machine** than where Docker is running.

## Scenario

- **Docker Server (192.168.2.132)**: Running Traefik on ports 18600/18643
- **Apache Server (192.168.2.250)**: Running native Apache on ports 80/443
- **Clients**: Access via https://v4.ossiba.com (resolved to 192.168.2.250)

## Prerequisites

On the Apache server (192.168.2.250):
- Apache 2.4+ installed
- SSL module enabled
- Network access to Docker server

## Step 1: Copy SSL Certificates

From the Docker server (192.168.2.132), copy the certificates:

```bash
# On Docker server
cd /workspaces/os-next/certs
scp ossiba.com.crt ossiba.com.key user@192.168.2.250:/etc/ssl/certs/
```

## Step 2: Update Apache Configuration

Edit `apache-proxy-ossiba-com.conf` and set the correct Docker server IP:

```apache
# Change this line to point to your Docker server
Define TRAEFIK_HOST 192.168.2.132
Define TRAEFIK_HTTPS_PORT 18643
```

Also update the SSL certificate paths:

```apache
SSLCertificateFile /etc/ssl/certs/ossiba.com.crt
SSLCertificateKeyFile /etc/ssl/certs/ossiba.com.key
```

## Step 3: Install Configuration

On Apache server (192.168.2.250):

```bash
# Copy configuration
sudo cp apache-proxy-ossiba-com.conf /etc/apache2/sites-available/orangescrum-ossiba-com.conf

# Enable required modules
sudo a2enmod proxy proxy_http ssl rewrite headers

# Enable site
sudo a2ensite orangescrum-ossiba-com

# Test configuration
sudo apache2ctl configtest

# Reload Apache
sudo systemctl reload apache2
```

## Step 4: Firewall Rules

On **Docker server** (192.168.2.132), allow traffic from Apache server:

```bash
# Allow traffic from Apache server IP
sudo ufw allow from 192.168.2.250 to any port 18643 proto tcp
sudo ufw allow from 192.168.2.250 to any port 18600 proto tcp
```

Or for the entire LAN:
```bash
sudo ufw allow from 192.168.2.0/24 to any port 18643 proto tcp
sudo ufw allow from 192.168.2.0/24 to any port 18600 proto tcp
```

## Step 5: Client Configuration

On all LAN client machines, add to hosts file:

**Linux/Mac** (`/etc/hosts`):
```
192.168.2.250 v4.ossiba.com app.ossiba.com selfhosted.ossiba.com mail.ossiba.com storage.ossiba.com console.ossiba.com
```

**Windows** (`C:\Windows\System32\drivers\etc\hosts`):
```
192.168.2.250 v4.ossiba.com app.ossiba.com selfhosted.ossiba.com mail.ossiba.com storage.ossiba.com console.ossiba.com
```

## Step 6: Verify Setup

Test from Apache server:
```bash
# Test connection to Traefik
curl -k -H "Host: v4.ossiba.local" https://192.168.2.132:18643/

# Should return HTML content, not 404
```

Test from any LAN client:
```bash
curl -k https://v4.ossiba.com
```

## Architecture

```
Client Browser (192.168.2.x)
    ↓ (https://v4.ossiba.com:443)
Apache Server (192.168.2.250:443)
    ↓ (rewrites Host: v4.ossiba.com → v4.ossiba.local)
    ↓ (proxies to https://192.168.2.132:18643/)
Traefik Container (192.168.2.132:18643)
    ↓ (routes based on hostname v4.ossiba.local)
Application Containers (on 192.168.2.132)
```

## Advantages

✅ **Separation of concerns**: Apache and Docker on different machines  
✅ **Existing infrastructure**: Use existing Apache server  
✅ **Security**: Docker server doesn't need to expose port 443  
✅ **SSL termination**: Handle SSL on dedicated Apache server  
✅ **Load balancing**: Easy to add multiple Docker backends  

## Troubleshooting

**502 Bad Gateway:**
- Check firewall rules on Docker server
- Verify Docker server IP in Apache config
- Ensure Traefik ports are bound to 0.0.0.0 (not 127.0.0.1)

**SSL Certificate errors:**
- Verify certificate paths in Apache config
- Check file permissions (certificates should be readable)

**Connection refused:**
- Verify Docker containers are running: `docker compose ps`
- Check Traefik port bindings: `docker compose port traefik 443`
- Test direct access: `curl -k https://192.168.2.132:18643`

## Environment Variables in Config

The Apache config uses variables for easy deployment:

- `TRAEFIK_HOST`: IP address of Docker server
- `TRAEFIK_HTTPS_PORT`: HTTPS port Traefik is listening on

To check Traefik port from Docker server:
```bash
cd /workspaces/os-next
grep TRAEFIK_HTTPS_PORT .env
```
