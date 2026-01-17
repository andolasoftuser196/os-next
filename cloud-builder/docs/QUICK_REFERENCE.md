# Durango Builder - Quick Reference

## Directory Directory Purpose Summary

| Directory | Purpose | Tracked? | Can Delete? |
|-----------|---------|----------|-------------|
| `builder/package/` | Temp git archive extraction + Docker context | [ERROR] No (only .gitkeep) | [OK] Yes |
| `orangescrum-ee/` | **Deployment package** | [OK] Structure only | [ERROR] No |
| `orangescrum-ee/orangescrum-app/orangescrum-ee` | Built binary | [ERROR] No | [OK] Yes (rebuild) |
| `builder/*.Dockerfile` | Docker build configs | [OK] Yes | [ERROR] No |
| `*.py` | Build scripts | [OK] Yes | [ERROR] No |

## Workflow Build Flow in 5 Steps

```txt
1. SOURCE (durango-pg repo)
   ↓ git archive
2. EXTRACT → builder/package/ (Docker context)
   ↓ docker build
3. BINARY → orangescrum-ee/orangescrum-app/orangescrum-ee
   ↓ docker build
4. DEPLOY → orangescrum-ee/ (final container)
```

## Deployment Common Commands

### Build (First Time - Slow ~30min)

```bash
python3 build.py
```

### Build (Code Changes - Fast ~2min)

```bash
python3 build.py --skip-base
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

## Package What to Commit

[OK] **DO COMMIT:**

- Scripts: `*.py`, `*.sh`
- Configs: `*.Dockerfile`, `*.yaml`
- Docs: `*.md`
- Structure: `.gitkeep` files
- Deployment: `orangescrum-ee/` (without binary)

[ERROR] **DON'T COMMIT:**

- Binary: `orangescrum-ee/orangescrum-app/orangescrum-ee`
- Temp source: `builder/package/*` contents
- Env files: `.env` (except examples)
- Backups: `backups/*`

## Goal: Key Files

| File | Purpose |
|------|---------|
| `build.py` | Build orchestration script |
| `builder/base-build.Dockerfile` | Stage 1: Build FrankenPHP base |
| `builder/app-embed.Dockerfile` | Stage 2: Embed app into binary |
| `orangescrum-ee/orangescrum-ee` | Native FrankenPHP binary (built) |

## Documentation Full Documentation

- [GIT_SETUP_GUIDE.md](GIT_SETUP_GUIDE.md) - Complete git setup and concepts
- [REPOSITORY_STRUCTURE.md](REPOSITORY_STRUCTURE.md) - Detailed structure docs
- [README.md](README.md) - Main documentation
- [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md) - Deployment guide
