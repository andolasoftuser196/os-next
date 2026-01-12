# Durango Builder - Quick Reference

## 📁 Directory Purpose Summary

| Directory | Purpose | Tracked? | Can Delete? |
|-----------|---------|----------|-------------|
| `builder/package/` | Temp git archive extraction + Docker context | ❌ No (only .gitkeep) | ✅ Yes |
| `orangescrum-ee/` | **Deployment package** | ✅ Structure only | ❌ No |
| `orangescrum-ee/orangescrum-app/orangescrum-ee` | Built binary | ❌ No | ✅ Yes (rebuild) |
| `builder/*.Dockerfile` | Docker build configs | ✅ Yes | ❌ No |
| `*.py` | Build scripts | ✅ Yes | ❌ No |

## 🔄 Build Flow in 5 Steps

```txt
1. SOURCE (durango-pg repo)
   ↓ git archive
2. EXTRACT → builder/package/ (Docker context)
   ↓ docker build
3. BINARY → orangescrum-ee/orangescrum-app/orangescrum-ee
   ↓ docker build
4. DEPLOY → orangescrum-ee/ (final container)
```

## 🚀 Common Commands

### Build (First Time - Slow ~30min)

```bash
python3 build_optimized.py
```

### Build (Code Changes - Fast ~2min)

```bash
python3 build_optimized.py --skip-base
```

### Clean Everything

```bash
rm -rf builder/package/*
rm -f orangescrum-ee/orangescrum-app/orangescrum-ee
```

### Deploy

```bash
cd orangescrum-ee
docker compose --env-file .env.production up -d
```

## 📦 What to Commit

✅ **DO COMMIT:**

- Scripts: `*.py`, `*.sh`
- Configs: `*.Dockerfile`, `*.yaml`
- Docs: `*.md`
- Structure: `.gitkeep` files
- Deployment: `orangescrum-ee/` (without binary)

❌ **DON'T COMMIT:**

- Binary: `orangescrum-ee/orangescrum-app/orangescrum-ee`
- Temp source: `builder/package/*` contents
- Env files: `.env` (except examples)
- Backups: `backups/*`

## 🎯 Key Files

| File | Purpose |
|------|---------|
| `build_optimized.py` | Main build script (two-stage) |
| `builder/base-build.Dockerfile` | Stage 1: Build FrankenPHP base |
| `builder/app-embed.Dockerfile` | Stage 2: Embed app into binary |
| `orangescrum-ee/Dockerfile` | Runtime: Alpine + binary |
| `orangescrum-ee/entrypoint.sh` | Init: migrations + seeds |
| `orangescrum-ee/docker-compose.yaml` | Deployment config |

## 📚 Full Documentation

- [GIT_SETUP_GUIDE.md](GIT_SETUP_GUIDE.md) - Complete git setup and concepts
- [REPOSITORY_STRUCTURE.md](REPOSITORY_STRUCTURE.md) - Detailed structure docs
- [README.md](README.md) - Main documentation
- [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md) - Deployment guide
