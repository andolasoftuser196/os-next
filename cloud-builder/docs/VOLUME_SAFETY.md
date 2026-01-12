# ⚠️ IMPORTANT: Volume Safety Guide

## The Danger of `docker compose down -v`

### What it does

```bash
docker compose down -v
```

This command **PERMANENTLY DELETES ALL VOLUMES**, including:

- ❌ All user uploads (photos, documents, attachments)
- ❌ All generated reports (PDFs, CSVs, invoices, timesheets)
- ❌ All application logs
- ❌ All cache data
- ❌ Runtime configuration changes
- ❌ Database data

### ⚠️ THIS DATA CANNOT BE RECOVERED! ⚠️

---

## Safe Commands

### Stop and Remove Containers (SAFE)

```bash
# Stops containers, removes them, but KEEPS all volumes
docker compose down
```

### Restart Application (SAFE)

```bash
# Just restart containers, volumes untouched
docker compose restart
```

### Rebuild and Update (SAFE)

```bash
# Rebuild image but preserve all data
docker compose down
docker compose up -d --build
```

### Update Code Only (SAFE)

```bash
# Rebuild with new code, data persists
python3 durango-builder/build_optimized.py --skip-base
docker compose -f durango-builder/orangescrum-ee/docker-compose.yaml up -d --build
```

---

## When You Need to Reset Everything

If you really need to delete all data and start fresh:

### Option 1: Backup First (RECOMMENDED)

```bash
# 1. Create backup
cd durango-builder
./backup_volumes.sh backup

# 2. Verify backup was created
./backup_volumes.sh list

# 3. Now safe to reset
cd ..
docker compose -f durango-builder/orangescrum-ee/docker-compose.yaml down -v

# 4. Start fresh
docker compose -f durango-builder/orangescrum-ee/docker-compose.yaml up -d
```

### Option 2: Remove Specific Volume Only

```bash
# Stop application
docker compose -f durango-builder/orangescrum-ee/docker-compose.yaml down

# Remove only the volume you want to reset
docker volume rm orangescrum-multitenant-base_app-uploads

# Restart (volume will be recreated empty)
docker compose -f durango-builder/orangescrum-ee/docker-compose.yaml up -d
```

---

## Backup & Restore

### Quick Backup

```bash
cd durango-builder
./backup_volumes.sh backup
```

This creates a timestamped backup in `./backups/YYYYMMDD_HHMMSS/` containing:

- All 8 application volumes
- Database volume
- Backup metadata

### List Backups

```bash
./backup_volumes.sh list
```

Example output:

```txt
Available backups in ./backups:

  📦 20241202_153045
     Date: 2024-12-02 15:30:45
     Size: 2.4G
     Info:
       Backup Date: Mon Dec 2 15:30:45 UTC 2024
       Project: orangescrum-multitenant-base
       Volumes: 9
```

### Restore Backup

```bash
# WARNING: This replaces all current data!
./backup_volumes.sh restore ./backups/20241202_153045
```

The script will:

1. Ask for confirmation
2. Stop all containers
3. Restore all volumes from backup
4. Show instructions to restart

---

## Volume Management

### Check Volume Sizes

```bash
docker system df -v | grep orangescrum-multitenant-base
```

### Inspect a Volume

```bash
docker volume inspect orangescrum-multitenant-base_app-uploads
```

### Browse Volume Contents

```bash
# See what's in the uploads volume
docker run --rm -v orangescrum-multitenant-base_app-uploads:/data alpine ls -lah /data
```

### Manual Backup Single Volume

```bash
docker run --rm \
  -v orangescrum-multitenant-base_app-uploads:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/uploads-backup.tar.gz /data
```

### Manual Restore Single Volume

```bash
docker run --rm \
  -v orangescrum-multitenant-base_app-uploads:/data \
  -v $(pwd):/backup \
  alpine sh -c "rm -rf /data/* && tar xzf /backup/uploads-backup.tar.gz -C /data"
```

---

## Production Best Practices

### 1. Regular Backups

```bash
# Add to crontab for daily backups at 2 AM
0 2 * * * cd /path/to/durango-builder && ./backup_volumes.sh backup /mnt/backup-storage
```

### 2. Backup Before Updates

```bash
# Always backup before rebuilding
./backup_volumes.sh backup
python3 build_optimized.py --skip-base
```

### 3. Test Restores

```bash
# Periodically test that backups can be restored
./backup_volumes.sh restore ./backups/latest
```

### 4. Off-site Backups

```bash
# Copy backups to remote location
rsync -avz ./backups/ user@backup-server:/backups/orangescrum/
```

### 5. Retention Policy

```bash
# Keep last 7 daily backups, delete older ones
find ./backups/ -type d -mtime +7 -exec rm -rf {} +
```

---

## Quick Reference

| Command | Safe? | What it does |
|---------|-------|--------------|
| `docker compose down` | ✅ YES | Stops containers, keeps volumes |
| `docker compose down -v` | ❌ NO | **DELETES ALL VOLUMES** |
| `docker compose restart` | ✅ YES | Restart containers only |
| `docker compose up -d --build` | ✅ YES | Rebuild image, keeps volumes |
| `docker volume rm <name>` | ⚠️ CAREFUL | Deletes specific volume |
| `./backup_volumes.sh backup` | ✅ YES | Creates backup |
| `./backup_volumes.sh restore` | ⚠️ CAREFUL | Replaces all data |

---

## Recovery Checklist

If you accidentally ran `docker compose down -v`:

1. ❌ **Data is permanently lost** - volumes cannot be recovered
2. ✅ Check if you have backups: `./backup_volumes.sh list`
3. ✅ If backup exists: `./backup_volumes.sh restore ./backups/<timestamp>`
4. ✅ If no backup: Start fresh with `docker compose up -d`
5. ⚠️ **For next time**: Set up automated backups (see Production Best Practices)

---

## Summary

- ✅ Always use `docker compose down` (without `-v`)
- ✅ Backup before any major changes
- ✅ Test your backups regularly
- ❌ Never use `docker compose down -v` in production
- ❌ Never use `docker volume prune` without checking first
