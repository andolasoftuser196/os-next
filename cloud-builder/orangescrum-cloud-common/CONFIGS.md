# Configuration Files Inventory

This document lists all configuration files that are copied during container startup.

## Core Application Configs

### Cache Configurations
- [OK] `cache_redis.example.php` → `cache_redis.php` (Redis cache - recommended for production)
- [OK] `cache_file.example.php` → `cache_file.php` (File-based cache)
- [OK] `cache_memcached.example.php` → `cache_memcached.php` (Memcached cache)
- [OK] `cache_auto.example.php` → `cache_auto.php` (Auto-detect cache engine)

### Queue Configurations
- [OK] `queue.example.php` → `queue.php` (Queue backend config)

### Email Configurations
- [OK] `sendgrid.example.php` → `sendgrid.php` (SendGrid email service)
- [OK] `smtp.example.php` → `smtp.php` (SMTP email service)

### Storage Configurations
- [OK] `storage.example.php` → `storage.php` (S3/MinIO object storage)
- [OK] `cloudstorage.example.php` → `cloudstorage.php` (Google Drive, Dropbox, OneDrive)

### Integration Configurations
- [OK] `recaptcha.example.php` → `recaptcha.php` (Google reCAPTCHA)
- [OK] `google_oauth.example.php` → `google_oauth.php` (Google OAuth login)
- [OK] `google_drive.example.php` → `google_drive.php` (Google Drive API)
- [OK] `github.example.php` → `github.php` (GitHub OAuth & webhooks)
- [OK] `v2_routing.example.php` → `v2_routing.php` (V2/V4 routing for migration)

### App Configuration
- [OK] `app_local.example.php` → `app_local.php` (Local overrides - from embedded app)

## Plugin Configurations

### Payments Plugin
- [OK] `plugins/Payments/config/stripe.example.php` → `stripe.php` (Stripe payment integration)

### GitSync Plugin
- [OK] `plugins/GitSync/config/gitsync.example.php` → `gitsync.php` (Main GitSync config)
- [OK] `plugins/GitSync/config/gitsync_github.example.php` → `gitsync_github.php` (GitHub integration)
- [OK] `plugins/GitSync/config/gitsync_gitlab.example.php` → `gitsync_gitlab.php` (GitLab integration)
- [OK] `plugins/GitSync/config/gitsync_bitbucket.example.php` → `gitsync_bitbucket.php` (Bitbucket integration)

## Copy Process

All files are copied during container startup by `entrypoint.sh`:

1. **Core configs** are copied from `$EXTRACTED_APP/config/*.example.php`
2. **Plugin configs** are copied conditionally if the plugin directory exists
3. All copies use `2>/dev/null` to suppress errors if files don't exist
4. Success messages are printed for each copied file

## Environment Variables

Most config files read from environment variables using `env()` function:

- Cache: `REDIS_HOST`, `REDIS_PORT`, `MEMCACHED_SERVER`, etc.
- Queue: `QUEUE_URL`, `QUEUE_ENGINE`
- Email: `EMAIL_TRANSPORT`, `SMTP_HOST`, `EMAIL_API_KEY`
- Storage: `STORAGE_ENDPOINT`, `STORAGE_ACCESS_KEY`, `STORAGE_BUCKET`
- Integrations: `RECAPTCHA_SITE_KEY`, `GITHUB_CLIENT_ID`, etc.

See `.env.example` for full list of available environment variables.

## Adding New Configs

To add a new configuration file:

1. Add the `.example.php` file to `config/` or `config/plugins/{PluginName}/`
2. Update `entrypoint.sh` to copy it during startup
3. Document it in this file
4. Add required environment variables to `.env.example`

## Verification

After deployment, check the container logs for:
```
Setting up configuration files...
  [OK] app_local.php
  [OK] cache_redis.php
  [OK] queue.php
  ...
```

Missing files will not show the [OK] checkmark but won't cause errors.
