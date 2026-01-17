# Cloud Builder Documentation

## Start Start Here

- **[CLOUD_BUILDER_README.md](../CLOUD_BUILDER_README.md)** Important: **Complete guide to building and running the native FrankenPHP binary**

---

## Documentation Documentation

### Core Documentation

- **[FRANKENPHP_DEPLOYMENT.md](FRANKENPHP_DEPLOYMENT.md)** - Binary deployment architecture, configuration options, and environment variables
- **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - Quick command reference for common tasks

### Reference Documentation

- **[REPOSITORY_STRUCTURE.md](REPOSITORY_STRUCTURE.md)** - Project directory structure
- **[GIT_SETUP_GUIDE.md](GIT_SETUP_GUIDE.md)** - Git configuration and workflow
- **[TECHNICAL_ARCHITECTURE.md](TECHNICAL_ARCHITECTURE.md)** - High-level system architecture
- **[SCHEMA_COMPARISON_SUMMARY.md](SCHEMA_COMPARISON_SUMMARY.md)** - Database schema reference

---

## Deployment Quick Workflow

```
1. Read: CLOUD_BUILDER_README.md
2. Build binary: python3 build.py
3. Configure: .env file with your database/services
4. Run app: orangescrum-ee/run.sh
5. Reference: FRANKENPHP_DEPLOYMENT.md, QUICK_REFERENCE.md
```

---

## Directory Key Files

| File | Purpose |
|------|---------|
| `../CLOUD_BUILDER_README.md` | Main documentation (start here) |
| `../build.py` | FrankenPHP binary build script |
| `../orangescrum-ee/.env` | Application configuration |
| `../orangescrum-ee/run.sh` | Native binary runner |

## About Configuration

The cloud builder requires database and cache services (PostgreSQL, Redis, etc.) to be available. These can be:

- **Hosted locally** (Docker, native installations)
- **Cloud-hosted** (AWS RDS, ElastiCache, etc.)
- **Third-party services** (managed databases, etc.)

Configure the connection details in `.env` file.

---

## FAQ Frequently Asked Questions

**Q: Where do I start?**
- Start with [CLOUD_BUILDER_README.md](../CLOUD_BUILDER_README.md)

**Q: Why do I still need Docker if the app runs natively?**
- The app runs natively. Supporting services (database, cache, etc.) can be hosted anywhere - locally, cloud, or managed services

**Q: How do I build the binary?**
- See [CLOUD_BUILDER_README.md](../CLOUD_BUILDER_README.md) → "Step 4: Build FrankenPHP Binary"

**Q: How do I run the application?**
- See [CLOUD_BUILDER_README.md](../CLOUD_BUILDER_README.md) → "Step 5: Run Native Binary"

**Q: What environment variables do I need?**
- See [FRANKENPHP_DEPLOYMENT.md](FRANKENPHP_DEPLOYMENT.md) → "Environment Variables"
- Or review `../orangescrum-ee/.env.example`

**Q: How do I troubleshoot issues?**
- See [CLOUD_BUILDER_README.md](../CLOUD_BUILDER_README.md) → "Troubleshooting"

---

## Related Related Files

- **Application Configuration**: [.env](../orangescrum-ee/.env)
- **Environment Template**: [.env.example](../orangescrum-ee/.env.example)
- **Main README**: [README.md](../README.md)
