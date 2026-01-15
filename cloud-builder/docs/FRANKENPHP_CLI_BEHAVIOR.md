# FrankenPHP CLI Behavior & Limitations

## Error Analysis: Why `-r` Flag Was Failing

### The Error (In Previous Builds)
```
Warning: Unknown: Failed to open stream: No such file or directory in Unknown on line 0
Fatal error: Failed opening required '/tmp/frankenphp_xxx/-r' (include_path='.:') in Unknown on line 0
```

### Root Cause

The old FrankenPHP image (`v1.4.4` and earlier) had incomplete CLI support:
- ✅ Had `cmd.DisableFlagParsing = true`
- ❌ Missing the actual `-r` flag handler in `cmdPHPCLI` function
- Result: `-r` was treated as a filename instead of a flag

The fix was merged in **v1.11.1** (PR #1559):
- Adds proper flag detection: `if len(args) >= 2 && args[0] == "-r"`
- Enables inline PHP execution via `frankenphp.ExecutePHPCode(args[1])`

### Solution Applied

Updated [base-build.Dockerfile](./base-build.Dockerfile) to use:
```dockerfile
FROM dunglas/frankenphp:static-builder-1.11.1 AS base-builder
```

This ensures the compiled binary includes the full fix for `-r` flag support.

### Why It Happens

When you run an embedded FrankenPHP binary with `php-cli`:

1. **Binary extracts to temp directory** → `/tmp/frankenphp_xxx/`
2. **All arguments are treated as file paths**, not flags
3. **`php-cli` command signature**: `./osv4-prod php-cli <script> [args...]`
4. **Flag processing**: Only `-r` at position 0 is recognized as "execute code"
5. **Everything else** → treated as a file to execute

### Source Code Behavior

From `apps/frankenphp/caddy/php-cli.go`:

```go
func cmdPHPCLI(fs caddycmd.Flags) (int, error) {
	args := os.Args[2:]  // Gets everything after "php-cli"
	
	if len(args) >= 2 && args[0] == "-r" {
		status = frankenphp.ExecutePHPCode(args[1])  // Execute inline code
	} else {
		status = frankenphp.ExecuteScriptCLI(args[0], args)  // Execute file
	}
}
```

**Key limitation**: Only recognizes `-r` flag. All other flags are treated as filenames.

---

## ✅ Correct Usage Patterns

### 1. Run CakePHP CLI Commands
```bash
# Migrations
./osv4-prod php-cli bin/cake.php migrations migrate
./osv4-prod php-cli bin/cake.php migrations migrate -p PluginName

# Queue worker
./osv4-prod php-cli bin/cake.php queue worker

# Recurring tasks
./osv4-prod php-cli bin/cake.php recurring_task

# Custom commands
./osv4-prod php-cli bin/cake.php command_name
```

### 2. Run Inline PHP Code (With `-r` flag)
```bash
# ✅ CORRECT - flag comes FIRST, code is SECOND argument
./osv4-prod php-cli -r 'echo "Hello World";'

# ✅ Check PHP version
./osv4-prod php-cli -r 'echo phpversion();'

# ✅ List loaded extensions
./osv4-prod php-cli -r 'print_r(get_loaded_extensions());'

# ✅ Get PHP info (formatted)
./osv4-prod php-cli -r 'phpinfo();' | head -50
```

### 3. Get Binary Information (No php-cli needed)
```bash
# Get FrankenPHP + PHP + Caddy versions
./osv4-prod --version

# Check if binary is executable
./osv4-prod php-server --help 2>&1 | head -20
```

### 4. Run PHP Scripts in Embedded App
```bash
# If you create a PHP script file in the app
./osv4-prod php-cli scripts/my-script.php arg1 arg2

# Script will be found relative to embedded app
```

---

## ❌ Commands That DON'T Work

These standard PHP CLI flags are **NOT supported** with `php-cli`:

```bash
# ❌ These will fail
./osv4-prod php-cli --version          # ERROR: tries to find "--version" file
./osv4-prod php-cli -v                 # ERROR: tries to find "-v" file
./osv4-prod php-cli -m                 # ERROR: tries to find "-m" file
./osv4-prod php-cli -i                 # ERROR: tries to find "-i" file
./osv4-prod php-cli -h                 # ERROR: tries to find "-h" file
./osv4-prod php-cli --help             # ERROR: tries to find "--help" file
```

**Why?** The `-r` flag is special-cased in the code. Other flags are not recognized.

---

## Why This Design?

### 1. **Security First**
- Prevents arbitrary PHP execution outside the embedded application
- All PHP runs within the application context
- No access to system PHP configuration

### 2. **Simplicity**
- Avoids reimplementing full PHP CLI argument parsing
- Focuses on running application tasks (CakePHP commands)
- Reduces binary complexity

### 3. **Consistency**
- All PHP execution uses same context and environment
- No confusion between embedded app and system PHP
- Predictable behavior for deployment

### 4. **Performance**
- Minimal overhead
- No complex flag parsing
- Direct execution of application code

---

## Real-World Usage Examples

### Running Migrations on Deployment
```bash
#!/bin/bash
# Startup script for production deployment

set -e

export DB_HOST=postgres.example.com
export DB_PASSWORD=$DB_PASS
export SECURITY_SALT=$SECURE_SALT

# Run migrations
/app/osv4-prod php-cli bin/cake.php migrations migrate

# Start web server
/app/osv4-prod php-server -r webroot -l 0.0.0.0:80
```

### Running Queue Worker
```bash
#!/bin/bash
# Queue worker process

/app/osv4-prod php-cli bin/cake.php queue worker --verbose
```

### Checking Application Status
```bash
#!/bin/bash
# Health check script

# Check if binary exists and is executable
if [ ! -x /app/osv4-prod ]; then
    echo "Binary not found or not executable"
    exit 1
fi

# Check PHP version via inline code
/app/osv4-prod php-cli -r 'echo "PHP: " . phpversion();'

# Check database connection
/app/osv4-prod php-cli -r '
    require "config/bootstrap.php";
    echo "App initialized successfully";
'
```

---

## Troubleshooting

### Problem: Binary says it loaded but `php-cli` commands fail

**Solution**: The binary works fine. You're likely using incorrect syntax.

```bash
# WRONG - Treating flag as filename
./osv4-prod php-cli --version

# CORRECT - Use -r for inline code
./osv4-prod php-cli -r 'echo phpversion();'
```

### Problem: CakePHP command not found

**Solution**: Path must be relative to embedded app root.

```bash
# WRONG - Absolute path won't work
./osv4-prod php-cli /app/bin/cake.php migrations migrate

# CORRECT - Relative to app root
./osv4-prod php-cli bin/cake.php migrations migrate
```

### Problem: Can't run custom PHP script

**Solution**: Script must exist in embedded app or use `-r` for inline.

```bash
# If /app/scripts/check.php exists in embedded app
./osv4-prod php-cli scripts/check.php

# Or use inline execution
./osv4-prod php-cli -r 'include "scripts/check.php";'
```

---

## Comparison: Standard PHP vs FrankenPHP Embedded

| Feature | Standard PHP CLI | FrankenPHP Embedded |
|---------|------------------|-------------------|
| `--version` | ✅ Works | ❌ Use `./binary --version` instead |
| `-m` (modules) | ✅ Works | ❌ Use `-r 'print_r(get_loaded_extensions());'` |
| `-i` (info) | ✅ Works | ❌ Use `-r 'phpinfo();'` |
| `-r 'code'` | ✅ Works | ✅ Works |
| Script files | ✅ Works | ✅ Works (relative to app) |
| CakePHP CLI | ⚠️ Requires CakePHP install | ✅ Always available |
| External dependencies | ✅ PHP + extensions needed | ❌ None needed (static binary) |

---

## See Also

- [PRODUCTION_DEPLOYMENT.md](./PRODUCTION_DEPLOYMENT.md) - Deployment guide
- [TECHNICAL_ARCHITECTURE.md](./TECHNICAL_ARCHITECTURE.md) - Architecture details
- [FrankenPHP Documentation](https://frankenphp.dev/docs/cli/) - Official FrankenPHP docs
