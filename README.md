# OrangeScrum Docker Setup

Multi-domain Docker setup for OrangeScrum V2 (PHP 7.2 + MySQL) and V4 Durango (PHP 8.3 + PostgreSQL).

## One-Command Setup

```bash
./setup.sh ossiba.local
```

Then follow the printed instructions.

## Access

- **V4 (Durango)**: https://v4.ossiba.local
- **V2 (Orangescrum)**: https://app.ossiba.local
- **MailHog**: https://mail.ossiba.local

## Commands

```bash
docker compose up -d          # Start
docker compose down           # Stop
docker compose logs -f        # Logs
```
