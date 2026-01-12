# Apache Configuration for Host Machine (192.168.2.132)

## Installation Instructions

### 1. Copy configuration to Apache sites-available

```bash
sudo cp 001-orangescrum-online-vm.conf /etc/apache2/sites-available/
```

### 2. Enable required Apache modules

```bash
sudo a2enmod ssl
sudo a2enmod proxy
sudo a2enmod proxy_http
sudo a2enmod headers
sudo a2enmod rewrite
```

### 3. Enable the site

```bash
# Disable old configuration if exists
sudo a2dissite 001-orangescrum-online-vm.conf

# Enable new configuration
sudo a2ensite 001-orangescrum-online-vm.conf
```

### 4. Test configuration

```bash
sudo apachectl configtest
sudo apachectl -S  # Verify VirtualHost order
```

### 5. Restart Apache

```bash
sudo systemctl restart apache2
```

### 6. Verify logs

```bash
sudo tail -f /var/log/apache2/ossiba-online-v4-access.log
sudo tail -f /var/log/apache2/ossiba-online-v2-access.log
```

## Expected VirtualHost Order

After installation, `apachectl -S` should show:

```
*:443                  is a NameVirtualHost
         default server v4.ossiba.online (...)
         port 443 namevhost v4.ossiba.online (...)
         port 443 namevhost ossiba.online (...)
                 alias www.ossiba.online
                 wild alias *.ossiba.online
```

**Important:** `v4.ossiba.online` must appear BEFORE the wildcard `*.ossiba.online`

## Testing

### Test V4 (Durango)
```bash
curl -I https://v4.ossiba.online/
```

### Test V2 (Orangescrum)
```bash
curl -I https://ossiba.online/
```

### Test Common Login Flow
```bash
# Should redirect from V4 to V2
curl -I https://v4.ossiba.online/users/login
```

## Troubleshooting

### Redirect Loop
- Check that `ProxyPreserveHost On` is set
- Verify SSL proxy settings are enabled
- Check Traefik logs: `docker compose logs traefik`

### "Too many redirects"
- Clear browser cookies for `.ossiba.online`
- Check that V4_ROUTING_ENABLED is consistent across apps
- Verify session cookie domain is `.ossiba.online` (with dot)

### Connection refused
- Verify VM is accessible: `curl -k https://192.168.49.10/`
- Check Traefik is running: `docker compose ps traefik`
- Check firewall rules on VM

## Configuration Details

### Proxy Settings
- **ProxyPreserveHost On**: Preserves original Host header for Traefik routing
- **SSLProxyEngine On**: Enables HTTPS proxying
- **SSLProxyVerify none**: Accepts self-signed certificates (Traefik)
- **ProxyPassReverseCookieDomain**: Fixes cookie domains for session sharing

### Security Headers
- **Strict-Transport-Security**: Forces HTTPS for 1 year
- **X-Frame-Options**: Prevents clickjacking
- **X-Forwarded-Proto**: Informs backend about original protocol
- **X-Forwarded-SSL**: Indicates SSL termination

### Load Test Support
- Uncomment the load test logging section to track load test requests
- Uses `X-Load-Test-Token` header to identify load test traffic
