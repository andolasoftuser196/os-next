#!/usr/bin/env python3
"""Build FrankenPHP embedded binary for OrangeScrum V4.

This script:
1) Archives the OrangeScrum V4 app from ../apps/orangescrum-v4
2) Builds the FrankenPHP embedded binary using the builder compose stack
3) Extracts the produced static binary into orangescrum-cloud/orangescrum-app/
4) Builds + starts the orangescrum-app service using orangescrum-cloud/docker-compose.yaml

Notes:
- Only builds the orangescrum-v4 application (not durango-pg or orangescrum v2)
- Database is expected to be external (PostgreSQL with orangescrum database)
- Base image build is skipped automatically if the image already exists
"""

from __future__ import annotations

import argparse
import io
import os
import shutil
import subprocess
import tarfile
import time
from pathlib import Path

import docker

ROOT = Path(__file__).parent.resolve()
REPO = (ROOT / "../apps/orangescrum-v4").resolve()
BUILDER = ROOT / "builder"
PACKAGE = BUILDER / "package"
BUILDER_COMPOSE_FILE = BUILDER / "docker-compose.yaml"

ORANGESCRUM_EE_DIR = ROOT / "orangescrum-cloud"
APP_COMPOSE_FILE = ORANGESCRUM_EE_DIR / "docker-compose.yaml"
APP_ENV_FILE_DEFAULT = ORANGESCRUM_EE_DIR / ".env"
APP_ENV_FILE_EXAMPLE = ORANGESCRUM_EE_DIR / ".env.example"
CONFIG_OVERRIDES_DIR = ORANGESCRUM_EE_DIR / "config"

ORANGESCRUM_EE_BINARY = ORANGESCRUM_EE_DIR / "orangescrum-app/osv4-prod"

FRANKENPHP_BASE_IMAGE = os.environ.get(
    "FRANKENPHP_BASE_IMAGE", "orangescrum-cloud-base:latest"
)


def _run_cmd(
    cmd: list[str], cwd: Path | None = None, env: dict[str, str] | None = None
):
    print(f"Running: {' '.join(cmd)}")
    subprocess.check_call(cmd, cwd=str(cwd) if cwd else None, env=env)


def _run_cmd_capture(
    cmd: list[str], cwd: Path | None = None, env: dict[str, str] | None = None
) -> str:
    print(f"Running: {' '.join(cmd)}")
    return subprocess.check_output(
        cmd, cwd=str(cwd) if cwd else None, env=env, text=True
    ).strip()


def _clean_dir(path: Path):
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def _copy_config_overrides():
    """Copy modified config files from orangescrum-cloud/config to package/config"""
    if not CONFIG_OVERRIDES_DIR.exists():
        print(f"Warning: Config overrides directory not found: {CONFIG_OVERRIDES_DIR}")
        return
    
    package_config = PACKAGE / "config"
    if not package_config.exists():
        print(f"Warning: Package config directory not found: {package_config}")
        return
    
    config_files = list(CONFIG_OVERRIDES_DIR.glob("*.example.php"))
    if not config_files:
        print(f"No config override files found in {CONFIG_OVERRIDES_DIR}")
        return
    
    print(f"Copying {len(config_files)} config override files...")
    for config_file in config_files:
        dest = package_config / config_file.name
        shutil.copy2(config_file, dest)
        print(f"  ✓ Copied {config_file.name}")


def _archive_repo() -> Path:
    """Archive OrangeScrum V4 app directory into a tar file."""
    print(f"Archiving OrangeScrum V4 from {REPO}...")
    
    if not REPO.exists():
        raise FileNotFoundError(f"OrangeScrum V4 directory not found: {REPO}")
    
    archive_path = BUILDER / "repo.tar"
    
    # Try git archive first (cleanest, only tracked files)
    git_dir = REPO / ".git"
    if git_dir.exists():
        print("Using git archive (only tracked files)...")
        try:
            _run_cmd(
                [
                    "git",
                    "-C",
                    str(REPO),
                    "archive",
                    "--format=tar",
                    "HEAD",
                    "-o",
                    str(archive_path),
                ]
            )
            print(f"✓ Created archive via git: {archive_path}")
            return archive_path
        except subprocess.CalledProcessError:
            print("Git archive failed, falling back to manual tar...")
    
    # Fallback: Create tar archive manually with exclusions
    print("Creating tar archive with exclusions...")
    
    # Define exclusion patterns (matches .dockerignore + common build artifacts)
    exclude_patterns = {
        '.git', '.github', '.gitignore', '.dockerignore',
        '.env', '.env.*',
        'vendor', 'node_modules',
        'tmp', 'logs', 'cache',
        '.idea', '.vscode', '.vs', '.settings',
        '*.log', '*.cache',
        '.ddev', '.devcontainer',
        'composer.lock', 'package-lock.json',
        '.phpunit.result.cache',
        '__pycache__', '*.pyc',
        '.DS_Store', 'Thumbs.db'
    }
    
    def tar_filter(tarinfo):
        """Filter function to exclude unwanted files/directories"""
        # Get relative path from REPO
        rel_path = Path(tarinfo.name).relative_to(REPO) if tarinfo.name.startswith(str(REPO)) else Path(tarinfo.name)
        
        # Check if any part of the path matches exclusion patterns
        parts = rel_path.parts
        for part in parts:
            # Exact match
            if part in exclude_patterns:
                return None
            # Pattern match (simple glob)
            for pattern in exclude_patterns:
                if '*' in pattern:
                    import fnmatch
                    if fnmatch.fnmatch(part, pattern):
                        return None
        
        return tarinfo
    
    with tarfile.open(archive_path, "w") as tar:
        tar.add(REPO, arcname=".", filter=tar_filter, recursive=True)
    
    print(f"✓ Created archive: {archive_path}")
    return archive_path


def _extract_archive(archive_path: Path, dest: Path):
    print(f"Extracting archive to {dest}...")
    with tarfile.open(archive_path, "r") as tar:
        tar.extractall(path=dest)
    print(f"✓ Extracted to {dest}")


def _ensure_base_image(docker_client: docker.DockerClient, rebuild: bool):
    if rebuild:
        try:
            docker_client.images.remove(FRANKENPHP_BASE_IMAGE, force=True)
            print(f"Removed existing base image: {FRANKENPHP_BASE_IMAGE}")
        except docker.errors.ImageNotFound:
            pass

    print(f"Checking for base image {FRANKENPHP_BASE_IMAGE}...")
    try:
        docker_client.images.get(FRANKENPHP_BASE_IMAGE)
        print("✓ Base image found; skipping base build.")
        return
    except docker.errors.ImageNotFound:
        pass

    print("Base image not found; building base FrankenPHP image (this may take a while)...")
    _run_cmd(
        [
            "docker",
            "compose",
            "-f",
            str(BUILDER_COMPOSE_FILE),
            "--profile",
            "base-build",
            "build",
            "frankenphp-base-builder",
        ],
        cwd=BUILDER,
    )
    print("✓ Base image built successfully")


def _build_app_embed():
    print("Embedding OrangeScrum V4 application into FrankenPHP...")
    env = os.environ.copy()
    env["BUILD_DATE"] = str(int(time.time()))
    env.setdefault("FRANKENPHP_BASE_IMAGE", FRANKENPHP_BASE_IMAGE)
    _run_cmd(
        [
            "docker",
            "compose",
            "-f",
            str(BUILDER_COMPOSE_FILE),
            "build",
            "orangescrum-app-builder",
        ],
        cwd=BUILDER,
        env=env,
    )
    print("✓ Application embedded successfully")


def _start_app_builder_container():
    print("Starting builder container...")
    _run_cmd(
        [
            "docker",
            "compose",
            "-f",
            str(BUILDER_COMPOSE_FILE),
            "up",
            "-d",
            "orangescrum-app-builder",
        ],
        cwd=BUILDER,
    )
    print("✓ Builder container started")


def _stop_builder_stack():
    print("Stopping builder stack...")
    _run_cmd(
        [
            "docker",
            "compose",
            "-f",
            str(BUILDER_COMPOSE_FILE),
            "down",
            "--remove-orphans",
        ],
        cwd=BUILDER,
    )
    print("✓ Builder stack stopped")


def _copy_frankenphp_binary(docker_client: docker.DockerClient):
    print("Copying FrankenPHP binary from builder container...")
    ORANGESCRUM_EE_BINARY.parent.mkdir(parents=True, exist_ok=True)

    # Get container ID from docker compose
    container_id = _run_cmd_capture(
        [
            "docker",
            "compose",
            "-f",
            str(BUILDER_COMPOSE_FILE),
            "ps",
            "-q",
            "orangescrum-app-builder",
        ],
        cwd=BUILDER,
    )
    if not container_id:
        raise RuntimeError(
            "Could not find builder container id (docker compose ps -q returned empty)"
        )

    container = docker_client.containers.get(container_id)
    bits, _ = container.get_archive("/go/src/app/dist/frankenphp-linux-x86_64")

    tar_stream = io.BytesIO(b"".join(bits))
    with tarfile.open(fileobj=tar_stream) as tar:
        tar.extractall(path=ORANGESCRUM_EE_BINARY.parent)

    extracted_binary = ORANGESCRUM_EE_BINARY.parent / "frankenphp-linux-x86_64"
    if extracted_binary.exists():
        extracted_binary.rename(ORANGESCRUM_EE_BINARY)

    ORANGESCRUM_EE_BINARY.chmod(0o755)
    size_mb = ORANGESCRUM_EE_BINARY.stat().st_size / (1024 * 1024)
    print(f"✓ FrankenPHP binary extracted: {ORANGESCRUM_EE_BINARY} ({size_mb:.1f} MB)")


def _resolve_env_file(path_str: str | None) -> Path:
    """Resolve which .env file to use"""
    if path_str:
        return Path(path_str).expanduser().resolve()
    if APP_ENV_FILE_DEFAULT.exists():
        return APP_ENV_FILE_DEFAULT
    return APP_ENV_FILE_EXAMPLE


def _wait_for_app_healthy(
    docker_client: docker.DockerClient,
    timeout_s: int = 180,
):
    """Wait for orangescrum-app container to become healthy"""
    print("Waiting for orangescrum-app to become healthy...")

    start = time.time()
    while time.time() - start < timeout_s:
        try:
            # Try to get container by service name
            cid = _run_cmd_capture(
                ["docker", "compose", "-f", str(APP_COMPOSE_FILE), "ps", "-q", "orangescrum-app"],
                cwd=ORANGESCRUM_EE_DIR,
            )
            if not cid:
                time.sleep(2)
                continue
                
            container = docker_client.containers.get(cid)
        except Exception:
            time.sleep(2)
            continue

        state = container.attrs.get("State", {})
        health = state.get("Health", {})
        status = health.get("Status") or state.get("Status")

        if status == "healthy":
            print("✓ orangescrum-app is healthy")
            return True
        if status in {"exited", "dead"}:
            logs = container.logs(tail=50).decode("utf-8", errors="ignore")
            raise RuntimeError(
                f"orangescrum-app container is not running (status={status}). Logs:\n{logs}"
            )

        time.sleep(2)

    print(f"⚠️  orangescrum-app did not become healthy within {timeout_s}s")
    return False


def check_prerequisites() -> bool:
    """Run pre-flight checks before building"""
    print("Pre-flight checks...")

    ok = True

    # Docker daemon
    try:
        docker.from_env().ping()
        print("✓ Docker daemon is running")
    except Exception as e:
        print(f"✗ Docker daemon is not accessible: {e}")
        ok = False

    # OrangeScrum V4 repository
    if REPO.exists():
        print(f"✓ OrangeScrum V4 repository found at {REPO}")
    else:
        print(f"✗ OrangeScrum V4 repository not found at {REPO}")
        ok = False

    # Compose files
    if BUILDER_COMPOSE_FILE.exists():
        print(f"✓ Builder compose file found at {BUILDER_COMPOSE_FILE}")
    else:
        print(f"✗ Builder compose file not found at {BUILDER_COMPOSE_FILE}")
        ok = False

    if APP_COMPOSE_FILE.exists():
        print(f"✓ App compose file found at {APP_COMPOSE_FILE}")
    else:
        print(f"✗ App compose file not found at {APP_COMPOSE_FILE}")
        ok = False

    return ok


def _ensure_app_env():
    """Ensure .env file exists for orangescrum-cloud deployment"""
    if not APP_ENV_FILE_DEFAULT.exists():
        print("Creating .env file from example...")
        if APP_ENV_FILE_EXAMPLE.exists():
            shutil.copy2(APP_ENV_FILE_EXAMPLE, APP_ENV_FILE_DEFAULT)
            print(f"✓ Created {APP_ENV_FILE_DEFAULT}")
            print("⚠ WARNING: Edit .env file to configure database and other settings!")
        else:
            print(f"⚠ WARNING: .env.example not found at {APP_ENV_FILE_EXAMPLE}")
    else:
        print(f"✓ .env file already exists: {APP_ENV_FILE_DEFAULT}")


def _deploy_orangescrum_app(docker_client: docker.DockerClient, env_file: Path, env_overrides: dict[str, str]):
    """Build and start the OrangeScrum app service"""
    print("Deploying OrangeScrum V4 application...")
    
    env = os.environ.copy()
    env["BUILD_DATE"] = str(int(time.time()))
    env.update(env_overrides)
    
    # Build and start the orangescrum-app service
    _run_cmd(
        [
            "docker",
            "compose",
            "-f",
            str(APP_COMPOSE_FILE),
            "--env-file",
            str(env_file),
            "up",
            "-d",
            "--build",
        ],
        cwd=ORANGESCRUM_EE_DIR,
        env=env,
    )
    
    print("✓ OrangeScrum V4 application deployed")


def main():
    parser = argparse.ArgumentParser(
        description="Build FrankenPHP embedded binary for OrangeScrum V4"
    )
    
    parser.add_argument(
        "--check",
        action="store_true",
        help="Run pre-flight checks only"
    )
    
    parser.add_argument(
        "--rebuild-base",
        action="store_true",
        help="Force rebuild of base FrankenPHP image (slow)"
    )
    parser.add_argument(
        "--skip-deploy",
        action="store_true",
        help="Only build the binary, don't deploy the application"
    )
    parser.add_argument(
        "--skip-archive",
        action="store_true",
        help="Skip git archive/extract step"
    )
    parser.add_argument(
        "--skip-base",
        action="store_true",
        help="Skip building base FrankenPHP image"
    )
    parser.add_argument(
        "--keep-package",
        action="store_true",
        help="Keep the package directory after build (default is to delete)"
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean up package directory before building"
    )
    
    # Environment and configuration options
    parser.add_argument(
        "--env-file",
        help="Path to orangescrum-cloud env file (defaults to .env or .env.example)"
    )
    parser.add_argument(
        "--app-port",
        type=int,
        help="Expose app on this port"
    )
    parser.add_argument(
        "--app-bind-ip",
        help="Bind app port to this IP (default 0.0.0.0)"
    )
    
    # Database configuration options
    parser.add_argument("--db-host", help="Database hostname for the app")
    parser.add_argument("--db-port", type=int, help="Database port for the app")
    parser.add_argument("--db-username", help="Database username for the app")
    parser.add_argument("--db-password", help="Database password for the app")
    parser.add_argument("--db-name", help="Database name for the app")
    
    args = parser.parse_args()
    
    # Handle --check flag
    if args.check:
        raise SystemExit(0 if check_prerequisites() else 1)
    
    print("=" * 60)
    print("OrangeScrum V4 FrankenPHP Builder")
    print("=" * 60)
    print()
    
    # Run pre-flight checks
    if not check_prerequisites():
        print("\n❌ Pre-flight checks failed. Please fix the issues above.")
        return 1
    
    print()
    
    # Verify source directory exists
    if not REPO.exists():
        print(f"ERROR: OrangeScrum V4 directory not found: {REPO}")
        print("Please ensure ../apps/orangescrum-v4 exists with application code")
        return 1
    
    docker_client = docker.from_env()
    
    # Resolve environment file
    env_file = _resolve_env_file(args.env_file)
    
    # Build environment overrides from command-line args
    env_overrides: dict[str, str] = {}
    if args.app_port is not None:
        env_overrides["APP_PORT"] = str(args.app_port)
    if args.app_bind_ip:
        env_overrides["APP_BIND_IP"] = args.app_bind_ip
    
    if args.db_host:
        env_overrides["DB_HOST"] = args.db_host
    if args.db_port is not None:
        env_overrides["DB_PORT"] = str(args.db_port)
    if args.db_username:
        env_overrides["DB_USERNAME"] = args.db_username
    if args.db_password:
        env_overrides["DB_PASSWORD"] = args.db_password
    if args.db_name:
        env_overrides["DB_NAME"] = args.db_name
    
    try:
        # Step 1: Clean package directory if requested
        if args.clean and PACKAGE.exists():
            print("Cleaning package directory...")
            _clean_dir(PACKAGE)
            print("✓ Package directory cleaned\n")
        
        # Step 2: Prepare package directory (unless skipping archive)
        if not args.skip_archive:
            print("Step 1: Preparing package directory...")
            _clean_dir(PACKAGE)
            
            # Step 3: Archive the OrangeScrum V4 app
            print("\nStep 2: Archiving OrangeScrum V4 application...")
            archive_path = _archive_repo()
            
            # Step 4: Extract to package directory
            print("\nStep 3: Extracting to package directory...")
            _extract_archive(archive_path, PACKAGE)
            
            # Clean up archive
            archive_path.unlink(missing_ok=True)
            
            # Step 5: Copy config overrides
            print("\nStep 4: Copying configuration overrides...")
            _copy_config_overrides()
        
        # Step 6: Ensure base image exists (unless skipping)
        if not args.skip_base:
            print("\nStep 5: Ensuring FrankenPHP base image...")
            _ensure_base_image(docker_client, args.rebuild_base)
        
        # Step 7: Build app embedding
        print("\nStep 6: Building FrankenPHP embedded application...")
        _build_app_embed()
        
        # Step 8: Start builder container
        print("\nStep 7: Starting builder container...")
        _start_app_builder_container()
        
        # Step 9: Copy binary
        print("\nStep 8: Extracting FrankenPHP binary...")
        _copy_frankenphp_binary(docker_client)
        
        # Step 10: Stop builder
        print("\nStep 9: Cleaning up builder containers...")
        _stop_builder_stack()
        
        # Clean up package directory unless --keep-package
        if not args.keep_package and PACKAGE.exists():
            print(f"\nCleaning up package directory {PACKAGE}...")
            shutil.rmtree(PACKAGE)
        
        # Step 11: Deploy if not skipped
        if not args.skip_deploy:
            print("\nStep 10: Deploying OrangeScrum V4 application...")
            _ensure_app_env()
            _deploy_orangescrum_app(docker_client, env_file, env_overrides)
            
            # Wait for health check
            _wait_for_app_healthy(docker_client)
        
        print("\n" + "=" * 60)
        print("Build Complete!")
        print("=" * 60)
        print(f"\nFrankenPHP binary: {ORANGESCRUM_EE_BINARY}")
        
        if not args.skip_deploy:
            app_port = env_overrides.get("APP_PORT", "8080")
            print(f"\n🎉 OrangeScrum V4 is now running!")
            print(f"Access at: http://localhost:{app_port}")
            print("\nUseful commands:")
            print("  cd orangescrum-cloud && docker compose ps      # Check status")
            print("  cd orangescrum-cloud && docker compose logs -f # View logs")
        else:
            print("\nTo deploy the application:")
            print("  cd orangescrum-cloud")
            print("  cp .env.example .env  # Edit with your settings")
            print("  docker compose up -d")
        
        print()
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return 1
    finally:
        docker_client.close()
    
    return 0


if __name__ == "__main__":
    exit(main())
