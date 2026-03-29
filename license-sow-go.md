# Statement of Work (SOW) — Go Edition

**Project Title:** Offline License Validation System & Generator (FrankenPHP Native)
**Target Ecosystem:** FrankenPHP 1.12+, Go 1.26+, CakePHP 4

## 1. Executive Summary

This project develops a highly secure, offline-only software licensing system built natively into FrankenPHP using **Go** instead of C. The system consists of two components: a **Caddy middleware module** that enforces license validity at the HTTP layer before PHP ever executes, and a **License Generation CLI** that issues cryptographically signed license keys. Zero modifications to the CakePHP application codebase.

### Why Go Instead of C

| Aspect | C Extension (Original SOW) | Go/Caddy Module (This SOW) |
|--------|---------------------------|----------------------------|
| Language | C with Zend API | Pure Go |
| Hook point | `PHP_RINIT_FUNCTION` (Zend engine) | Caddy middleware (HTTP layer) |
| Blocks before PHP | Yes (at request init) | Yes (before request reaches PHP) |
| Worker mode compatible | Requires careful ZTS handling | Native — middleware runs per-request |
| Compilation | `config.m4`, `phpize`, SPC descriptor | `xcaddy --with`, standard Go module |
| Portability to standard PHP | Yes (`.so`/`.dll`) | No — FrankenPHP only |
| Code maintenance | C + Zend macros + memory management | Pure Go + standard library |
| Crypto library | libsodium (C binding) | `crypto/ed25519` (Go stdlib) |
| File I/O | C `fopen`/`fread` + manual parsing | `os.ReadFile` + `encoding/json` |
| Testing | PHP test framework + valgrind | `go test` |
| Binary size impact | ~50 KB | ~200 KB |

**Trade-off:** The Go approach loses compatibility with standard PHP-FPM/Apache deployments. If standard PHP support is needed, the C extension from the original SOW should be built as a separate deliverable. The Go module covers the FrankenPHP deployment path.

## 2. Architecture

```
                    ┌─────────────────────────────────┐
                    │         HTTP Request             │
                    └──────────────┬──────────────────┘
                                   │
                    ┌──────────────▼──────────────────┐
                    │     Caddy HTTP Server            │
                    │  (TLS, routing, static files)    │
                    └──────────────┬──────────────────┘
                                   │
                    ┌──────────────▼──────────────────┐
                    │   license_guard middleware       │  ◄── THIS MODULE
                    │                                  │
                    │  1. Read /data/license/license.key
                    │  2. Verify Ed25519 signature     │
                    │  3. Check org + email match      │
                    │  4. Check expiry date            │
                    │  5. Optional hardware check      │
                    │                                  │
                    │  PASS → continue to PHP          │
                    │  FAIL → 403 + error page         │
                    └──────────────┬──────────────────┘
                                   │ (only if valid)
                    ┌──────────────▼──────────────────┐
                    │     FrankenPHP PHP Handler       │
                    │     (CakePHP 4 application)      │
                    └─────────────────────────────────┘
```

### Why Caddy Middleware (Not Go PHP Extension)

FrankenPHP's Go extension generator creates PHP functions callable from userland. But for license enforcement, we need to **block before PHP runs** — not expose a function PHP code can call (and bypass).

Options evaluated:

| Approach | Blocks before PHP? | Needs C code? | Worker mode safe? |
|----------|-------------------|---------------|-------------------|
| Go PHP extension (MINIT) | At startup only | No | Yes |
| Go PHP extension (RINIT) | Per-request | Yes (manual C) | Complex |
| **Caddy middleware** | **Per-request** | **No** | **Yes** |
| Go PHP extension + middleware combo | Both layers | No | Yes |

**Caddy middleware is the cleanest.** It operates at the HTTP layer, pure Go, no Zend API, no C glue code. The request never touches PHP if the license is invalid.

## 3. Scope of Work

### 3.1. Caddy License Guard Module (`caddy-license-guard`)

A Go module that registers as a Caddy HTTP handler middleware.

#### 3.1.1. Cryptographic Verification

- **Algorithm:** Ed25519 using Go's `crypto/ed25519` standard library (no external dependencies)
- **Public key embedding:** The Ed25519 public key is embedded at compile time via Go `ldflags`:

  ```go
  var publicKeyHex string // set via -ldflags "-X main.publicKeyHex=..."
  ```

  Or as a constant in the module source (requires recompilation to change — this is a feature, not a bug)
- **Signature format:** `license.key` contains Base64-encoded JSON payload + detached Ed25519 signature

#### 3.1.2. License Validation Logic

Executed on every HTTP request (with in-memory caching):

```
1. Read license.key from configured path (OCDPATH env or Caddyfile directive)
2. Decode Base64 → JSON payload + signature bytes
3. Verify Ed25519 signature against embedded public key
4. Parse JSON payload:
   {
     "organization": "Acme Corp",
     "email": "admin@acme.com",
     "expires": "2027-01-01T00:00:00Z",
     "max_users": 50,
     "features": ["gantt", "timesheet", "invoice"],
     "hardware_enforce": false,
     "hardware_hash": ""
   }
5. Compare organization + email against license.ini
6. Check expiry date against current time
7. If hardware_enforce: compare machine fingerprint
8. Cache result in-process (invalidate on file change via fsnotify)
```

#### 3.1.3. Caddyfile Integration

```caddyfile
{
    frankenphp
}

localhost {
    root * webroot/

    # License guard — blocks requests if license is invalid
    license_guard {
        license_path /data/license          # Directory containing license.key + license.ini
        grace_period 7d                     # Allow 7 days past expiry before hard block
        bypass /healthz                     # Skip license check for health endpoint
        bypass /api/license/status          # Allow license status API
    }

    php_server
}
```

#### 3.1.4. Failure Behavior

| Condition | HTTP Response | Body |
|-----------|---------------|------|
| `license.key` missing | 503 Service Unavailable | "License file not found" |
| Invalid signature | 403 Forbidden | "License validation failed" |
| Org/email mismatch | 403 Forbidden | "License not valid for this installation" |
| Expired (within grace) | 200 + `X-License-Warning` header | App runs, header warns |
| Expired (past grace) | 403 Forbidden | "License expired" |
| Hardware mismatch | 403 Forbidden | "License not valid for this hardware" |

Error responses serve a static HTML page (embedded in the Go binary) — no PHP involved.

#### 3.1.5. Performance

- **First request:** Read files + verify signature (~1-2ms)
- **Subsequent requests:** In-memory cache check (~0.01ms)
- **Cache invalidation:** `fsnotify` watcher on `license.key` — revalidates on file change
- **No per-request file I/O** after initial load

#### 3.1.6. PHP-Accessible License Info

Expose license metadata to PHP via HTTP headers injected by the middleware:

```
X-License-Organization: Acme Corp
X-License-Email: admin@acme.com
X-License-Expires: 2027-01-01
X-License-Features: gantt,timesheet,invoice
X-License-Max-Users: 50
```

CakePHP reads these via `$this->request->getHeader('X-License-Features')` — zero code changes needed for basic feature gating.

### 3.2. License Generation CLI

A standalone Go CLI tool for the vendor to issue licenses.

```bash
# Generate Ed25519 keypair
license-gen keygen --output keys/

# Issue a license
license-gen issue \
  --private-key keys/private.key \
  --organization "Acme Corp" \
  --email "admin@acme.com" \
  --expires "2027-01-01" \
  --max-users 50 \
  --features "gantt,timesheet,invoice" \
  --output license.key

# Verify a license (using public key)
license-gen verify \
  --public-key keys/public.key \
  --license license.key

# Inspect license payload (without verification)
license-gen inspect --license license.key
```

#### Key Management

- **Private key:** Ed25519 private key, stored securely by vendor only. Never leaves vendor infrastructure.
- **Public key:** Embedded in the compiled FrankenPHP binary at build time. Cannot be replaced without recompilation.
- **Key rotation:** Issue new keypair → recompile binary → new licenses use new key. Old licenses remain valid until expiry (dual-key support in the middleware for transition periods).

### 3.3. Build Integration with Cloud Builder

#### Compile the license module into FrankenPHP

Add to `build.conf`:

```ini
[license]
# Go module path for the license guard Caddy middleware
caddy_module = github.com/orangescrum/caddy-license-guard
# Ed25519 public key (hex-encoded) — embedded at compile time
public_key_hex = a1b2c3d4...
```

Add to `builder/docker-compose.yaml` or `app-embed.Dockerfile`:

```bash
XCADDY_ARGS="--with github.com/orangescrum/caddy-license-guard"
```

The `build-static.sh` already supports `SPC_CMD_VAR_FRANKENPHP_XCADDY_MODULES` for adding custom Caddy modules. Our cloud builder passes this through.

#### Embed the public key at build time

In the `app-embed.Dockerfile`, add ldflags:

```dockerfile
ENV XCADDY_GO_BUILD_FLAGS="-ldflags='-X github.com/orangescrum/caddy-license-guard.publicKeyHex=${LICENSE_PUBLIC_KEY}'"
```

### 3.4. Client-Side File Structure

```
/data/license/
├── license.ini        # Client-configured: organization + email
└── license.key        # Vendor-issued: signed payload
```

**license.ini** (configured by the client):

```ini
organization = Acme Corp
email = admin@acme.com
```

**license.key** (issued by vendor):

```
eyJvcmdhbml6YXRpb24iOiJBY21lIENvcnAi...  (Base64 payload)
--
MEQCIG...  (Base64 Ed25519 signature)
```

## 4. Optional: Dual-Layer Protection (Go Extension + Middleware)

For defense-in-depth, add a Go PHP extension alongside the Caddy middleware:

```go
package licenseext

// #include <Zend/zend_types.h>
import "C"
import (
    "os"
    "unsafe"
    "github.com/dunglas/frankenphp"
)

//export_php:namespace OrangeScrum\License

//export_php:function is_valid(): bool
func IsValid() bool {
    // Read cached validation state from shared memory or env
    return os.Getenv("__LICENSE_VALID") == "1"
}

//export_php:function organization(): string
func Organization() unsafe.Pointer {
    return frankenphp.PHPString(os.Getenv("__LICENSE_ORG"), false)
}

//export_php:function features(): string
func Features() unsafe.Pointer {
    return frankenphp.PHPString(os.Getenv("__LICENSE_FEATURES"), false)
}

//export_php:function max_users(): int
func MaxUsers() int64 {
    // parse from env
}

//export_php:function expires(): string
func Expires() unsafe.Pointer {
    return frankenphp.PHPString(os.Getenv("__LICENSE_EXPIRES"), false)
}
```

**Usage in CakePHP:**

```php
use function OrangeScrum\License\is_valid;
use function OrangeScrum\License\features;
use function OrangeScrum\License\max_users;

if (!is_valid()) {
    throw new ForbiddenException('Invalid license');
}

$features = explode(',', features());
if (!in_array('gantt', $features)) {
    // Hide Gantt chart feature
}
```

This gives PHP code **read-only access** to license metadata without being able to bypass the middleware enforcement.

## 5. Out of Scope

- Web-based license management dashboard (CLI-only for this phase)
- Payment gateway integration
- PHP source code obfuscation
- Standard PHP-FPM/Apache support (use the C extension SOW for that)
- License server / phone-home validation (this is offline-only)

## 6. Deliverables

| Deliverable | Description | Format |
|---|---|---|
| `caddy-license-guard` | Caddy middleware Go module with Ed25519 verification, caching, fsnotify | Go module (git repo) |
| `license-gen` | CLI tool for keygen, issue, verify, inspect | Go binary |
| `license-ext` (optional) | Go PHP extension exposing license info to PHP | Go module |
| Build integration | Changes to `build.conf`, `app-embed.Dockerfile` | Patch / PR |
| Deployment guide | Setup for `OCDPATH`, `license.ini`, Caddyfile config | Markdown |
| Test suite | Unit tests for crypto, validation, caching, expiry, grace period | `go test` |

## 7. Acceptance Criteria

- **Hard block:** CakePHP returns 403 if `license.key` is missing, tampered, or expired past grace period
- **Signature verification:** Rejects any payload not signed with the matching private key
- **Org/email binding:** Rejects if `license.ini` values don't match signed payload
- **Hardware lock (optional):** Rejects if `hardware_enforce: true` and machine fingerprint differs
- **Grace period:** App continues running with warning header for configured days past expiry
- **Performance:** < 0.1ms per request after initial validation (in-memory cache)
- **Cache invalidation:** File change triggers revalidation within 1 second (fsnotify)
- **Health bypass:** `/healthz` always passes regardless of license state
- **Build success:** Compiles into FrankenPHP static binary via cloud builder without errors
- **Feature gating:** PHP can read license features via headers or Go extension functions

## 8. Security Model

```
┌─────────────────────────────────────────────────────────┐
│                    VENDOR SIDE                           │
│                                                          │
│  Ed25519 Private Key  ──►  license-gen issue  ──►  license.key
│  (never leaves vendor)      (signs payload)        (sent to client)
│                                                          │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                    CLIENT SIDE                           │
│                                                          │
│  Ed25519 Public Key   ◄──  Embedded in binary at compile │
│  (cannot be changed         time via ldflags             │
│   without recompilation)                                 │
│                                                          │
│  license.key ──► Caddy middleware ──► signature check    │
│  license.ini ──►                  ──► org/email match    │
│                                                          │
│  VALID  → request passes to PHP                         │
│  INVALID → 403, PHP never executes                      │
└─────────────────────────────────────────────────────────┘
```

**Attack vectors mitigated:**

- **Key replacement:** Public key compiled into binary — requires binary recompilation
- **Payload tampering:** Ed25519 signature verification detects any modification
- **License sharing:** Org + email binding ties license to a specific customer
- **Clock manipulation:** Grace period limits exposure; optional hardware lock adds binding
- **PHP bypass:** Middleware runs before PHP — no userland code can skip it
- **File watching:** fsnotify detects license replacement, revalidates immediately
