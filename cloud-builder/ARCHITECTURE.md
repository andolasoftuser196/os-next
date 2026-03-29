# OrangeScrum V4 FrankenPHP Cloud Builder

Single-command build system that produces a self-contained static binary (~340 MB) containing FrankenPHP 1.12.1 + PHP 8.3 + Caddy + the entire OrangeScrum V4 application.

```bash
python3 build.py --skip-deploy    # Build only (~3 min after first build)
python3 build.py --check          # Pre-flight checks
python3 build.py --verify <dir>   # Verify dist package integrity
```

## Output

Two deployment packages in `dist/{timestamp}/`:

| Package | Target | Startup |
|---------|--------|---------|
| `dist-docker/` | Docker + docker compose | `docker compose up -d` |
| `dist-native/` | Bare Linux server + systemd | `./run.sh` or systemd service |

## Guides

| Guide | Audience | Contents |
|-------|----------|----------|
| [Developer Guide](docs/DEVELOPER_GUIDE.md) | Developers | Build pipeline, project structure, config system, making changes |
| [DevOps Guide](docs/DEVOPS_GUIDE.md) | DevOps / SRE | Deployment steps, env setup, health checks, troubleshooting, security |

## Key Design Decisions

- **Zero hardcoded values** — everything flows from `VERSION` + `build.conf`
- **Shared shell library** (`lib/frankenphp-common.sh`) — 8 functions used by both Docker and Native
- **Config as code** — `BuildConfig` frozen dataclass, no global mutable state
- **Binary validation** — ELF check + SHA256 checksums + `build-manifest.json`
- **Glob-based config activation** — no hardcoded `cp` commands, new configs auto-discovered
