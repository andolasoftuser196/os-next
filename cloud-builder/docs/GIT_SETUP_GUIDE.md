# Durango Builder Repository Setup Guide

## Package Repository Purpose

The `durango-builder` repository is a **build system** that:

1. Takes source code from `durango-pg` (CakePHP application)
2. Builds a static FrankenPHP binary with embedded application
3. Produces a deployable Docker container

This is **NOT** the application source code repository. It's the **packaging and deployment** system.

---

## Building Directory Roles Explained

### **durango-builder/package/** - TEMPORARY Source Extraction

**Purpose**: Temporary holding area for extracted source code

**What happens**:

- `build.py` runs `git archive` on `../durango-pg`
- Extracts complete CakePHP app to this directory
- Used as staging before Docker build

**Status**:

- [ERROR] **Should be IGNORED by git**
- [OK] Only `.gitkeep` tracked
-  Can be deleted anytime (regenerated on build)

**Content Example**:

```txt
package/
├── .gitkeep           # ← Only this is tracked
├── bin/              # ← All ignored
├── config/
├── src/
├── webroot/
├── composer.json
└── ... (complete app)
```

---

### **durango-builder/builder/package/** - TEMPORARY Docker Context

**Purpose**: Copy of source within Docker build context

**What happens**:

- `build.py` copies from `package/` to here
- Docker uses this as build context
- `app-embed.Dockerfile` embeds this into binary

**Status**:

- [ERROR] **Should be IGNORED by git**
- [OK] Only `.gitkeep` tracked
-  Can be deleted anytime (regenerated on build)

**Why Separate?**:

- Docker needs files within its build context
- Can't directly reference `../package/` in Dockerfile
- Copy ensures Docker has clean working directory

---

### **durango-builder/orangescrum-ee/** - DEPLOYMENT Package

**Purpose**: Application deployment folder with binary, configuration, and runner scripts

**What's TRACKED**:

- [OK] `run.sh` - Native binary runner script
- [OK] `.env.example` - Configuration template
- [OK] Directory structure
- [OK] Configuration files

**What's IGNORED**:

- [ERROR] `orangescrum-app/orangescrum-ee` - The binary (340+ MB)
- [ERROR] `.env` files (except examples)

**Status**:

- Deployment **Cloud builder deployment package**
- Package **Ready for standalone deployment**
- [OK] Commit structure, not binaries

**Content Example**:

```txt
orangescrum-ee/
├── run.sh               # ← Tracked (native runner)
├── .env.example         # ← Tracked
├── .env                 # ← IGNORED (local config)
└── orangescrum-app/
    └── orangescrum-ee   # ← IGNORED (binary)
```

---

## Workflow Complete Build Flow

```txt
┌──────────────────────────────────────────────────────────────┐
│ 1. SOURCE: ../durango-pg (separate git repo)                │
│    - CakePHP application source code                         │
└──────────────────────────────────────────────────────────────┘
                        │
                        │ git archive (by build script)
                        ▼
┌──────────────────────────────────────────────────────────────┐
│ 2. EXTRACT: package/ (TEMP - ignored)                       │
│    - Complete app extracted here                             │
│    - Not tracked by git                                      │
└──────────────────────────────────────────────────────────────┘
                        │
                        │ Copy to Docker context
                        ▼
┌──────────────────────────────────────────────────────────────┐
│ 3. DOCKER CONTEXT: builder/package/ (TEMP - ignored)        │
│    - Docker build can access files here                      │
│    - Not tracked by git                                      │
└──────────────────────────────────────────────────────────────┘
                        │
                        │ Docker build (app-embed.Dockerfile)
                        ▼
┌──────────────────────────────────────────────────────────────┐
│ 4. BINARY: orangescrum-ee/orangescrum-app/ (ignored)        │
│    - Static binary: frankenphp-linux-x86_64                 │
│    - Renamed to: orangescrum-ee                             │
│    - 150+ MB file (PHP + Caddy + App)                       │
│    - Not tracked by git                                      │
└──────────────────────────────────────────────────────────────┘
                        │
                        │ Used by deployment
                        ▼
┌──────────────────────────────────────────────────────────────┐
│ 5. DEPLOY: orangescrum-ee/ (structure tracked)              │
│    - Dockerfile uses the binary                              │
│    - Creates minimal Alpine container                        │
│    - Ready for production deployment                         │
└──────────────────────────────────────────────────────────────┘
```

---

## Checklist What Should Be Committed

### [OK] DO Commit These Files

```txt
durango-builder/
├── .gitignore                     # Git ignore rules
├── README.md                      # Main documentation
├── REPOSITORY_STRUCTURE.md        # This guide
├── build.py                       # Build orchestration script
├── requirements.txt               # Python dependencies
├── backup_volumes.sh              # Backup utility
├── docs/                          # All documentation
│   ├── *.md
├── builder/                       # Build configuration
│   ├── *.Dockerfile              # All Dockerfiles
│   ├── *.yaml                    # Compose files
│   └── package/.gitkeep          # Keep directory
├── package/
│   └── .gitkeep                  # Keep directory
└── orangescrum-ee/                # Deployment package
    ├── docker-compose.yaml
    ├── Dockerfile
    ├── entrypoint.sh
    ├── .env.example
    └── .env.test-*
```

### [ERROR] DON'T Commit These

```txt
durango-builder/
├── package/*                      # Temporary source
│   (except .gitkeep)
├── builder/package/*              # Temporary Docker context
│   (except .gitkeep)
├── orangescrum-ee/
│   ├── orangescrum-app/
│   │   └── orangescrum-ee        # Binary (150+ MB)
│   └── .env                      # Environment config
├── backups/*                      # Volume backups
├── repo.tar                      # Build artifacts
└── *.log                         # Logs
```

---

## Deployment Setting Up Git Repository

### Initialize Repository

```bash
cd durango-builder

# Initialize git
git init

# Add all tracked files
git add .

# Commit
git commit -m "Initial commit: FrankenPHP build system

- Build scripts for optimized two-stage builds
- Docker configurations for base and app-embed
- Deployment package with entrypoint and migrations
- Documentation for build process and deployment
"
```

### Create Remote Repository

```bash
# Add remote (replace with your repo URL)
git remote add origin git@github.com:yourusername/durango-builder.git

# Push to remote
git branch -M main
git push -u origin main
```

---

## Verification Verify Git Tracking

### Check What's Tracked

```bash
# See all tracked files
git ls-files

# Check status
git status

# Verify ignores work
git status --ignored
```

### Expected Output

**Tracked**: ~30-50 files (configs, scripts, docs)
**Ignored**: Binary, temp dirs, env files
**Clean**: No untracked important files

---

## Goal: Usage Patterns

### For Development (Frequent Code Changes)

```bash
# Make changes in ../durango-pg
cd ../durango-pg
git commit -am "Feature: Add new module"

# Build (fast, reuses base)
cd ../durango-builder
python3 build.py --skip-base

# package/ and builder/package/ are regenerated
# Old binary is replaced
# New binary is ready in orangescrum-ee/
```

### For Deployment (Use Pre-built Binary)

```bash
# Clone just the builder repo
git clone https://github.com/yourusername/durango-builder.git
cd durango-builder

# Get the binary (from build artifacts, CI/CD, etc.)
# Or build it yourself with build.py

# Deploy
cd orangescrum-ee
docker compose --env-file .env.production up -d
```

### For Clean Rebuild

```bash
# Remove all temporary files
rm -rf package/* builder/package/*
rm -f orangescrum-ee/orangescrum-app/orangescrum-ee

# Full rebuild
python3 build.py
```

---

## Note: Key Concepts

### Why Three Package Directories?

1. **package/** - Clean extraction from git
   - Ensures reproducible builds
   - Can be inspected before build

2. **builder/package/** - Docker build context
   - Docker limitation: needs files in context
   - Isolated from other builds

3. **orangescrum-ee/** - Deployment artifact
   - Final product
   - Includes runtime configuration
   - Ready to ship

### Why Ignore The Binary?

- **Size**: 150+ MB file
- **Reproducible**: Can be rebuilt from source
- **Environment-specific**: May differ per platform
- **Git best practice**: Don't commit build artifacts

### Why Track .gitkeep Files?

- Git doesn't track empty directories
- `.gitkeep` ensures directories exist
- Build script expects these directories

---

## Stats File Size Comparison

```txt
Repository (tracked):     ~5 MB
├── Scripts & configs:    ~500 KB
├── Documentation:        ~200 KB
└── Example files:        ~100 KB

Build artifacts (ignored):
├── Binary:               ~150 MB
├── package/:             ~50 MB
└── builder/package/:     ~50 MB

Total with artifacts:     ~255 MB
Total without artifacts:  ~5 MB  ← Git repo size
```

---

## Configuration Maintenance

### Cleaning Up

```bash
# Remove temporary build files
rm -rf package/* builder/package/*

# Remove old binaries
rm -f orangescrum-ee/orangescrum-app/orangescrum-ee

# Clean Docker
docker system prune -a
```

### Updating Dependencies

```bash
# Update PHP extensions
# Edit: builder/base-build.Dockerfile

# Rebuild base
python3 build.py --rebuild-base
```

### Adding New Configuration

```bash
# Add new environment template
cp orangescrum-ee/.env.example orangescrum-ee/.env.production

# Edit and commit
git add orangescrum-ee/.env.production
git commit -m "Add production environment template"
```

---

## [OK] Pre-Commit Checklist

Before committing changes:

- [ ] No binaries in commit
- [ ] No `.env` files (except examples)
- [ ] No `package/` contents (except `.gitkeep`)
- [ ] No `builder/package/` contents (except `.gitkeep`)
- [ ] Documentation updated
- [ ] Build script tested
- [ ] `.gitignore` rules verified

---

## 🆘 Troubleshooting

### "Large files detected"

```bash
# Check what's being committed
git status
git diff --cached --stat

# Remove large file from commit
git reset HEAD path/to/large/file
```

### "Directory not found"

```bash
# Ensure .gitkeep files exist
touch package/.gitkeep
touch builder/package/.gitkeep
git add package/.gitkeep builder/package/.gitkeep
```

### "Binary not working after clone"

```bash
# Binary is not in the repository!
# You need to build it or download it separately
python3 build.py
```

---

## Support Questions?

See:

- [README.md](README.md) - Build system overview
- [REPOSITORY_STRUCTURE.md](REPOSITORY_STRUCTURE.md) - Detailed structure
- [builder/BUILD_OPTIMIZATION.md](builder/BUILD_OPTIMIZATION.md) - Build details
- [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md) - Deployment guide
