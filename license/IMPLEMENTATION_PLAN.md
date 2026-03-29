# Implementation Plan: OrangeScrum License Guard System

## Context

Replace the existing PHP-level license enforcement in durango-pg with a binary-level Caddy middleware compiled into FrankenPHP. The PHP check is bypassable by editing source code. The binary check is tamper-proof.

### What Gets Replaced

| Existing (PHP)                                                | Replaced By (Go Binary)                     |
| ------------------------------------------------------------- | ------------------------------------------- |
| `src/Service/LicenseService.php` — RSA + AES-256-CBC          | Caddy middleware — Ed25519 signature verify  |
| `AppController::beforeFilter()` license check (line 185)      | Middleware blocks before PHP runs            |
| `public.pem` file on disk                                     | Public key compiled into binary              |
| `config/license.key` (encrypted blob)                         | `/data/license/license.key` (signed JSON)    |
| `webroot/os.ini` (OCDPATH package config)                     | `/data/license/license.ini` (org + email)    |
| `InstallController::checkLicense()` (upload + decrypt + save) | File drop to `/data/license/` (hot-reload)   |

### What Stays (reads headers instead of decrypting files)

| File                                                       | Change                                                    |
| ---------------------------------------------------------- | --------------------------------------------------------- |
| `InstallController::renew()`                               | Read `X-License-*` headers instead of `LicenseService`    |
| `AppController::setOCDetail()`                             | Read `X-License-Max-Users` header instead of `OCDPATH`    |
| `SubscriptionExpiredException` + error templates           | Still used, triggered by missing/invalid headers           |
| `InstallController::checkLicense()` — upload form          | Simplified: write uploaded file to `/data/license/`        |
| User limits in `UserSubscriptions` table                   | Seeded from `X-License-Max-Users` header                  |

---

## Architecture

```
HTTP Request
    │
    ▼
Caddy (TLS, static files, routing)
    │
    ▼
license_guard middleware              ◄── Compiled into binary
    │
    ├─ Read /data/license/license.key + license.ini
    ├─ Verify Ed25519 signature (cached, <0.1ms)
    ├─ Check org + email match
    ├─ Check expiry (with grace period)
    │
    ├─ VALID → inject X-License-* headers → pass to PHP
    ├─ GRACE → inject headers + X-License-Warning → pass to PHP
    └─ INVALID → return 403/503 HTML → PHP never runs
         │
         ▼
FrankenPHP / PHP (CakePHP 4)
    │
    ├─ Read X-License-Organization, X-License-Email
    ├─ Read X-License-Max-Users, X-License-Features
    ├─ Read X-License-Expires, X-License-Warning
    └─ Feature gating + user limits based on headers
```

### Hot-Reload (Upgrade/Renew without restart)

```
Client drops new license.key → /data/license/license.key
    │
    ▼
fsnotify detects file change (< 500ms)
    │
    ▼
cache.revalidate() — re-reads, re-verifies, updates state
    │
    ▼
Next request uses new license (zero downtime)

Safety net: 60s periodic refresh (Docker volumes may miss inotify)
```

---

## Components

| Component             | Path                           | Purpose                                         |
| --------------------- | ------------------------------ | ------------------------------------------------ |
| `caddy-license-guard` | `license/caddy-license-guard/` | Caddy middleware — validates license per-request  |
| `license-gen`         | `license/license-gen/`         | CLI — keygen, issue, verify, inspect              |
| PHP migration         | `apps/durango-pg/src/`         | Replace LicenseService with header reads          |
| Build patches         | `cloud-builder/`               | Thread module + public key into build pipeline    |

---

## Directory Structure

```
license/
├── caddy-license-guard/
│   ├── go.mod
│   ├── guard.go              # CaddyModule(), Provision(), ServeHTTP(), Cleanup()
│   ├── caddyfile.go          # init(), UnmarshalCaddyfile(), directive ordering
│   ├── license.go            # LicensePayload, Ed25519 verify, INI parse, LicenseState
│   ├── cache.go              # sync.RWMutex cache + fsnotify + 60s periodic refresh
│   ├── hardware.go           # Optional machine fingerprint
│   ├── errorpage.go          # go:embed for 403/503 HTML
│   ├── errorpage.html        # Self-contained error page (inline CSS, OrangeScrum branding)
│   ├── guard_test.go
│   ├── license_test.go
│   ├── cache_test.go
│   └── testdata/
│
└── license-gen/
    ├── go.mod
    ├── main.go               # CLI: keygen, issue, verify, inspect
    ├── cmd/
    │   ├── keygen.go
    │   ├── issue.go
    │   ├── verify.go
    │   └── inspect.go
    └── license/
        ├── types.go           # LicensePayload struct
        ├── crypto.go          # Ed25519 sign/verify (Go stdlib only)
        └── format.go          # base64(json)\n--\nbase64(signature)
```

---

## Implementation Phases

### Phase 1: License Format & CLI (3 days)

`license/license-gen/` — zero external dependencies, Go stdlib only.

**License payload:**

```json
{
  "organization": "Acme Corp",
  "email": "admin@acme.com",
  "expires": "2027-01-01T00:00:00Z",
  "max_users": 50,
  "features": ["gantt", "timesheet", "invoice", "gitsync"],
  "subscription": "Professional",
  "hardware_enforce": false,
  "hardware_hash": ""
}
```

**License file format (`license.key`):**

```
eyJvcmdhbml6YXRpb24iOi...   (base64 JSON payload)
--
MEQCIG...                     (base64 Ed25519 signature)
```

**License INI (`license.ini` — client-configured):**

```ini
organization = Acme Corp
email = admin@acme.com
```

**CLI commands:**

```bash
license-gen keygen --output keys/
license-gen issue --private-key keys/private.key \
    --org "Acme Corp" --email "admin@acme.com" \
    --expires "2027-01-01" --max-users 50 \
    --features "gantt,timesheet,invoice" \
    --subscription "Professional" \
    --output license.key
license-gen verify --public-key keys/public.key --license license.key
license-gen inspect --license license.key
```

**Verify:** `go test ./...` — round-trip keygen → issue → verify. Tampered payload rejected.

### Phase 2: Caddy Middleware (4 days)

`license/caddy-license-guard/` — depends on `caddyserver/caddy/v2` + `fsnotify/fsnotify`.

**Key files:**

| File            | Responsibility                                                                                                    |
| --------------- | ----------------------------------------------------------------------------------------------------------------- |
| `guard.go`      | `LicenseGuard` struct. Module ID: `http.handlers.license_guard`. `Provision()` inits cache + watcher. `ServeHTTP()` checks cache → bypass/inject/block. `Cleanup()` stops watcher. |
| `caddyfile.go`  | Registers `license_guard` directive ordered before `php_server`. Parses: `license_path`, `grace_period`, `bypass`. |
| `license.go`    | Ed25519 verify. INI parse. `readAndVerifyLicense()` → `LicenseState{Status, Payload, ExpiresAt, GraceExpiresAt}`. Status enum: Valid, GracePeriod, Expired, InvalidSignature, OrgMismatch, HardwareMismatch, Missing, Error. |
| `cache.go`      | `getState()` — RLock, return cached (hot path ~0.01ms). `revalidate()` — WLock, re-read files, re-verify. fsnotify with 500ms debounce. 60s periodic timer safety net. |
| `errorpage.go`  | `//go:embed errorpage.html`. Serves 403/503 with `{{.Message}}` substitution.                                     |

**Public key compiled into binary:**

```go
var publicKeyHex string // primary: set via -ldflags -X at build time

const compiledPublicKeyHex = "" // fallback: generated const file during build

func resolvePublicKey() (ed25519.PublicKey, error) {
    hex := publicKeyHex
    if hex == "" { hex = compiledPublicKeyHex }
    if hex == "" { return nil, fmt.Errorf("no public key") }
    return decodeHexKey(hex)
}
```

**Headers injected on valid requests:**

```
X-License-Organization: Acme Corp
X-License-Email: admin@acme.com
X-License-Expires: 2027-01-01
X-License-Max-Users: 50
X-License-Features: gantt,timesheet,invoice
X-License-Subscription: Professional
X-License-Warning: expires in 5 days      (grace period only)
```

**Caddyfile config:**

```caddyfile
license_guard {
    license_path {$OCDPATH:/data/license}
    grace_period {$LICENSE_GRACE_PERIOD:30d}
    bypass /healthz
    bypass /api/license/status
    bypass /install/*
}
```

**Verify:** Unit tests with mock states for all 8 status codes. Bypass path tests. Header injection tests.

### Phase 3: PHP Migration (3 days)

Replace the PHP license enforcement with header reads. The binary does all validation — PHP just reads the result.

**Files to modify in `apps/durango-pg/`:**

| File                                             | Change                                                                                                                  |
| ------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------- |
| `src/Service/LicenseService.php`                 | **Rewrite.** Remove all crypto. New methods read `X-License-*` from request headers. Keep `getLicenseDetails()` returning same structure for backward compat with templates. |
| `src/Controller/AppController.php:185-187`       | Replace `isLicenseValid()` call with header check: `$this->request->getHeaderLine('X-License-Organization') !== ''`      |
| `src/Controller/AppController.php:1588-1600`     | `isLicenseValid()` — check `X-License-Expires` header instead of decrypting license file                                |
| `src/Controller/AppController.php:91-120`        | `setOCDetail()` — read `X-License-Max-Users` and `X-License-Subscription` headers instead of parsing `OCDPATH` INI       |
| `src/Controller/InstallController.php:245-264`   | `checkLicense()` — simplified: save uploaded file to `/data/license/license.key`, middleware revalidates via fsnotify     |
| `src/Controller/InstallController.php:178-195`   | `renew()` — read license details from headers instead of `LicenseService::getLicenseDetails()`                           |
| `config/globalVars.php:63`                       | `OCDPATH` constant — change to `/data/license` (or read from env)                                                       |
| `templates/Install/license.php`                  | Simplify form: just file upload to `/data/license/`. Remove license code field (no longer needed for AES key derivation) |
| `public.pem`                                     | **Delete.** Public key is now in the binary.                                                                             |
| `webroot/os.ini`                                 | **Delete.** Replaced by `license.ini` + `X-License-*` headers.                                                          |

**New `LicenseService.php` (header-based):**

```php
class LicenseService
{
    private ServerRequestInterface $request;

    public function __construct(ServerRequestInterface $request)
    {
        $this->request = $request;
    }

    public function isLicenseValid(): bool
    {
        return $this->request->getHeaderLine('X-License-Organization') !== '';
    }

    public function getOrganization(): string
    {
        return $this->request->getHeaderLine('X-License-Organization');
    }

    public function getMaxUsers(): int
    {
        return (int) ($this->request->getHeaderLine('X-License-Max-Users') ?: 0);
    }

    public function getFeatures(): array
    {
        $features = $this->request->getHeaderLine('X-License-Features');
        return $features ? explode(',', $features) : [];
    }

    public function getExpires(): ?string
    {
        return $this->request->getHeaderLine('X-License-Expires') ?: null;
    }

    public function getSubscription(): string
    {
        return $this->request->getHeaderLine('X-License-Subscription') ?: '';
    }

    public function getWarning(): ?string
    {
        $warning = $this->request->getHeaderLine('X-License-Warning');
        return $warning ?: null;
    }

    public function getLicenseDetails(): array
    {
        return [
            'email' => $this->request->getHeaderLine('X-License-Email'),
            'company_name' => $this->getOrganization(),
            'user_limit' => $this->getMaxUsers(),
            'expires_at' => strtotime($this->getExpires() ?? ''),
            'orangescrum_version' => trim(file_get_contents(ROOT . DS . 'VERSION.txt') ?: ''),
            'status' => $this->isLicenseValid() ? 'valid' : 'expired',
            'subscription' => $this->getSubscription(),
            'features' => $this->getFeatures(),
        ];
    }
}
```

**Verify:** Existing renewal page renders with header data. Upload new license.key triggers revalidation. Feature gating works via headers.

### Phase 4: Build Integration (2 days)

| File                                               | Change                                                                                       |
| -------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| `cloud-builder/build.conf`                         | Add `[license]` section: `caddy_module`, `public_key_hex`, `local_source`                     |
| `cloud-builder/lib/config.py`                      | Extend `BuildConfig` with license fields. Export in `build_env()`. Generate `XCADDY_ARGS`.    |
| `cloud-builder/builder/docker-compose.yaml`        | Pass `XCADDY_ARGS` and `LICENSE_PUBLIC_KEY_HEX` as build args                                 |
| `cloud-builder/builder/base-build.Dockerfile`      | Accept `XCADDY_ARGS` ARG → `SPC_CMD_VAR_FRANKENPHP_XCADDY_MODULES`. Accept ldflags.          |
| `cloud-builder/builder/Caddyfile`                  | Add `license_guard` block before `php_server`                                                 |
| `cloud-builder/orangescrum-cloud/Dockerfile`       | Mount `/data/license` as a volume                                                             |
| `cloud-builder/orangescrum-cloud/docker-compose.yaml` | Add `/data/license` volume mount                                                           |

**XCADDY_ARGS** (must include defaults + license module):

```text
--with github.com/dunglas/mercure/caddy
--with github.com/dunglas/vulcain/caddy
--with github.com/dunglas/caddy-cbrotli
--with github.com/orangescrum/caddy-license-guard
```

**ldflags caveat:** If spc doesn't forward `XCADDY_GO_BUILD_FLAGS`, generate a `pubkey_compiled.go` const file during build. Test early.

**Verify:** `python3 build.py --rebuild-base --skip-deploy` succeeds. `./osv4-prod list-modules` shows `http.handlers.license_guard`.

### Phase 5: Testing & Hardening (2 days)

| Test                              | Method                                                                  |
| --------------------------------- | ----------------------------------------------------------------------- |
| Valid license → PHP gets headers   | `curl -I localhost:8080/` — check X-License-* headers present           |
| Expired past grace → 403           | Issue expired license, verify 403 HTML response                         |
| Missing license.key → 503          | Remove file, verify 503                                                 |
| Tampered payload → 403             | Modify base64 payload, verify rejection                                 |
| Org mismatch → 403                 | license.ini org differs from signed payload                             |
| Bypass /healthz → 200              | Always passes regardless of license state                               |
| Bypass /install/* → 200            | Installation flow works without license                                 |
| Hot-reload: drop new license.key   | Replace file, verify new state within 2s                                |
| Renewal flow: upload via PHP UI    | Upload new license.key via form, verify immediate revalidation          |
| Max users: header consumed by PHP  | Set X-License-Max-Users=5, verify PHP enforces limit                    |
| Feature gating                     | Set X-License-Features=gantt, verify timesheet feature hidden           |
| Performance                        | Benchmark: cached check < 0.1ms per request                            |
| Docker volume inotify              | Test fsnotify works with Docker bind mount                              |

---

## Key Technical Decisions

1. **Binary replaces PHP enforcement** — `LicenseService` becomes a thin header reader, not a crypto engine
2. **Caddy middleware, not Go PHP extension** — blocks at HTTP layer before PHP, pure Go, unbypassable
3. **Ed25519 replaces RSA + AES** — simpler (one algorithm, no encryption layer), faster, Go stdlib
4. **Public key in binary, not on disk** — can't be replaced without recompilation
5. **fsnotify + 60s refresh** — hot-reload for license upgrades/renewals without restart
6. **Bypass /install/*** — installation flow must work before a license exists
7. **Duplicated `LicensePayload` struct** — keeps Go modules independent (no shared dep)
8. **Directive ordering: `before php_server`** — guarantees middleware runs first

---

## Risks

| Risk                                       | Likelihood | Mitigation                                     |
| ------------------------------------------ | ---------- | ---------------------------------------------- |
| spc doesn't forward XCADDY_GO_BUILD_FLAGS  | Medium     | Generated const file fallback                  |
| fsnotify fails on Docker volumes           | Low        | 60s periodic refresh timer                     |
| Header spoofing (attacker injects headers) | Low        | Middleware strips X-License-* before injecting  |
| Directive ordering conflict                | Low        | Test with exact module set in build             |
| xcaddy can't fetch private Git repo        | Medium     | `local_source` in build.conf, vendor the module |

---

## Security: Header Spoofing Prevention

The middleware must **strip any incoming `X-License-*` headers** before injecting its own. Otherwise an attacker behind a misconfigured proxy could inject fake license headers:

```go
func (lg *LicenseGuard) ServeHTTP(w http.ResponseWriter, r *http.Request, next caddyhttp.Handler) error {
    // Strip any client-provided license headers (prevent spoofing)
    for key := range r.Header {
        if strings.HasPrefix(strings.ToLower(key), "x-license-") {
            r.Header.Del(key)
        }
    }

    // ... validation + inject real headers ...
}
```

---

## Migration Checklist

### PHP Code Changes

- [ ] Rewrite `src/Service/LicenseService.php` — header-based (remove all crypto)
- [ ] Update `src/Controller/AppController.php:185` — check header presence
- [ ] Update `src/Controller/AppController.php:1588` — `isLicenseValid()` reads headers
- [ ] Update `src/Controller/AppController.php:91` — `setOCDetail()` reads `X-License-Max-Users`
- [ ] Simplify `src/Controller/InstallController.php` — checkLicense saves file, renew reads headers
- [ ] Update `config/globalVars.php:63` — point OCDPATH to `/data/license`
- [ ] Simplify `templates/Install/license.php` — remove license code field
- [ ] Delete `public.pem` from app root
- [ ] Delete `webroot/os.ini`
- [ ] Remove `openssl` dependency from LicenseService

### New Go Code

- [ ] `license/license-gen/` — CLI tool (keygen, issue, verify, inspect)
- [ ] `license/caddy-license-guard/` — Caddy middleware (8 Go files + HTML)

### Build Integration

- [ ] `cloud-builder/build.conf` — add `[license]` section
- [ ] `cloud-builder/lib/config.py` — extend BuildConfig
- [ ] `cloud-builder/builder/*` — Dockerfile, compose, Caddyfile patches
- [ ] Docker volumes — `/data/license` mount

---

## Verification (End-to-End)

```bash
# 1. Build CLI tool
cd license/license-gen && go build -o license-gen . && go test ./...

# 2. Generate test keypair + license
./license-gen keygen --output /tmp/keys
./license-gen issue --private-key /tmp/keys/private.key \
    --org "Test Corp" --email "admin@test.com" --expires "2027-01-01" \
    --max-users 50 --features "gantt,timesheet" --subscription "Professional" \
    --output /tmp/license.key
./license-gen verify --public-key /tmp/keys/public.key --license /tmp/license.key

# 3. Test middleware
cd license/caddy-license-guard && go test ./...

# 4. Build FrankenPHP with license module
cd cloud-builder
# Add public key hex to build.conf
python3 build.py --rebuild-base --skip-deploy

# 5. Deploy and test
mkdir -p /data/license
cp /tmp/license.key /data/license/
echo "organization = Test Corp\nemail = admin@test.com" > /data/license/license.ini
./deploy.sh

# 6. Verify
curl -I http://localhost:8080/          # Should have X-License-* headers
curl http://localhost:8080/healthz      # Should always return 200

# 7. Test hot-reload
./license-gen issue ... --max-users 100 --output /data/license/license.key
sleep 2
curl -I http://localhost:8080/          # X-License-Max-Users should be 100

# 8. Test expiry
./license-gen issue ... --expires "2020-01-01" --output /data/license/license.key
sleep 2
curl http://localhost:8080/             # Should return 403
```
