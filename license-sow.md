# Statement of Work (SOW)

**Project Title:** Offline License Validation System & Generator
**Target Ecosystem:** Standard PHP 8.1+, FrankenPHP, static-php-cli, CakePHP 4

## 1. Executive Summary

This project entails the development of a highly secure, offline-only software licensing system. The system consists of two primary components: a **C-based PHP Extension** that enforces license validity natively at the server level, and a **License Generation Service** responsible for issuing cryptographically signed license keys. The system is designed to protect a CakePHP 4 application without requiring modifications to the application's core codebase.

## 2. Scope of Work

The scope of this project is divided into three distinct pillars:

### 2.1. C-Level PHP Extension (`php_license_check`)

The core enforcement mechanism will be a custom PHP extension written in C.

* **Cryptographic Verification:** Implement Ed25519 signature verification using `libsodium`. The public key will be hardcoded directly into the C source code as a constant byte array to prevent tampering.
* **Flexible License Binding (Canonical Org/Email):** The primary mechanism for license validation will rely on validating the user's `Organization Name` and `Registered Email`.
  * The extension will parse the local `license.ini` (configured by the client) and strictly compare it against the cryptographically signed payload in `license.key`.
* **Optional Hardware Lock:** The system will retain the capability to extract machine identifiers (e.g., OS UUID or MAC address). This will only be enforced if the issued `license.key` payload specifically contains a `hardware_enforce: true` flag and an associated hardware hash.
* **Offline File Parsing:** The extension will read a custom environment variable (`OCDPATH`) to locate and parse two local files:
  * `license.ini`: Contains client-side configuration (Email, Organization).
  * `license.key`: Contains the JSON payload (Email, Organization, Optional Hardware ID hash, Expiry date) and the Ed25519 signature.
* **Zend Engine Interception:** Utilize the `PHP_RINIT_FUNCTION` (Request Initialization hook) to perform the license validation before the PHP interpreter parses any userland code.
* **Universal Compatibility:** Provide `config.m4` and `config.w32` scripts to ensure the extension can be compiled dynamically (`.so`/`.dll`) for standard PHP, and statically embedded into both **FrankenPHP** and **static-php-cli** builds.

### 2.2. License Generation Service

A secure, standalone tool utilized exclusively by the software vendor to issue new licenses.

* **Platform:** A lightweight CLI application written in PHP or Go.
* **Key Management:** The tool will hold the securely stored Ed25519 Private Key.
* **Payload Generation:** It will accept client parameters (Email, Organization Name, Expiry Date, Optional Target Hardware ID) and generate a standardized JSON payload.
* **Cryptographic Signing:** The tool will sign the JSON payload using the Private Key and output the final `license.key` file (a Base64 encoded string or binary file combining the payload and the signature).

### 2.3. CakePHP 4 Integration & Environment Setup

The deployment and execution strategy for the protected application.

* **Zero-Code Integration:** Because the extension operates at the Zend Engine RINIT phase, no custom middleware, bootstrapping, or component logic will be added to the CakePHP 4 application.
* **Environment Configuration:** Documentation and setup guides for injecting the `OCDPATH` environment variable into the various hosting environments:
  * Standard PHP-FPM / Nginx setups.
  * FrankenPHP (via Caddyfile environment directives).
  * Micro-binaries compiled via `static-php-cli`.

## 3. Out of Scope

* Development of a web-based SaaS dashboard for license management (the generator is CLI-only for this phase).
* Payment gateway integration for automated license purchasing.
* Obfuscation of the CakePHP 4 PHP source code (this SOW covers execution blocking via the extension, not source code encryption).

## 4. Deliverables

| Deliverable | Description | Format |
| :--- | :--- | :--- |
| **Extension Source Code** | Complete C source code, header files, and build configurations (`config.m4`, `config.w32`). | Source Repository |
| **License Generator Tool** | CLI utility for generating Ed25519 keypairs and signing `license.key` files. | Executable / Script |
| **Deployment Guide** | Documentation for compiling the extension across Standard PHP, FrankenPHP, and static-php-cli. | Markdown / PDF |
| **CakePHP Env Guide** | Instructions for setting up `OCDPATH` and managing the `license.ini` and `license.key` files in production. | Markdown / PDF |

## 5. Acceptance Criteria

* **Enforcement:** The CakePHP application fails to load (returning a fatal C-level error via `zend_bailout`) if `license.key` is missing, modified, or signed with an incorrect private key.
* **Canonical Validation Check:** The extension successfully denies execution if the Email or Organization in the local `license.ini` does not exactly match the signed data in `license.key`.
* **Hardware Lock (Optional):** When enabled via the payload flag, the extension successfully denies execution if the host machine's hardware fingerprint does not match the fingerprint hashed within the `license.key`.
* **Performance:** The RINIT hook executes the offline validation with negligible performance overhead (under 5ms) per request.
* **Build Success:** The extension cleanly compiles into a standard `.so` file, a FrankenPHP Docker image, and a `static-php-cli` micro-binary without compilation errors.