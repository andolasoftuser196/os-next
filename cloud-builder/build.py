#!/usr/bin/env python3
"""Build FrankenPHP embedded binary for OrangeScrum V4.

Usage:
    python3 build.py                     # Build + deploy
    python3 build.py --skip-deploy       # Build only (production workflow)
    python3 build.py --check             # Pre-flight checks only
    python3 build.py --verify dist/...   # Verify a built dist package
    python3 build.py --rebuild-base      # Force recompile FrankenPHP base

All build parameters are read from VERSION + build.conf. No hardcoded values.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import time
from pathlib import Path

import docker

from lib.config import BuildConfig


# ---------------------------------------------------------------------------
# Utilities (stateless)
# ---------------------------------------------------------------------------

def _run(
    cmd: list[str], cwd: Path | None = None, env: dict[str, str] | None = None
):
    print(f"  $ {' '.join(cmd)}")
    subprocess.check_call(cmd, cwd=str(cwd) if cwd else None, env=env)


def _run_capture(
    cmd: list[str], cwd: Path | None = None, env: dict[str, str] | None = None
) -> str:
    return subprocess.check_output(
        cmd, cwd=str(cwd) if cwd else None, env=env, text=True
    ).strip()


def _clean_dir(path: Path):
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Builder class — all state lives here, zero globals
# ---------------------------------------------------------------------------

class Builder:
    def __init__(self, config: BuildConfig):
        self.c = config
        self._docker: docker.DockerClient | None = None
        self._step_num = 0

    @property
    def docker_client(self) -> docker.DockerClient:
        if self._docker is None:
            self._docker = docker.from_env()
        return self._docker

    def close(self):
        if self._docker:
            self._docker.close()

    # -- Step runner with timing ------------------------------------------

    def _step(self, name: str):
        """Print a step header and return the step number."""
        self._step_num += 1
        print(f"\n[Step {self._step_num}] {name}")
        return self._step_num

    # -- Pre-flight -------------------------------------------------------

    def check(self) -> bool:
        print("Pre-flight checks...")
        ok = True

        try:
            docker.from_env().ping()
            print("  [OK] Docker daemon is running")
        except Exception as e:
            print(f"  [FAIL] Docker daemon: {e}")
            ok = False

        if self.c.repo.exists():
            print(f"  [OK] App source: {self.c.repo}")
        else:
            print(f"  [FAIL] App source not found: {self.c.repo}")
            ok = False

        if self.c.builder_compose_file.exists():
            print(f"  [OK] Builder compose: {self.c.builder_compose_file}")
        else:
            print(f"  [FAIL] Builder compose not found: {self.c.builder_compose_file}")
            ok = False

        print(f"  [INFO] Version: {self.c.version}")
        print(f"  [INFO] FrankenPHP: {self.c.frankenphp_version}, PHP: {self.c.php_version}")
        print(f"  [INFO] Git SHA: {self.c.git_sha}")
        return ok

    # -- Archive -----------------------------------------------------------

    def archive_app(self) -> Path:
        """Archive OrangeScrum V4 app into a tar file."""
        archive_path = self.c.builder_dir / "repo.tar"

        git_dir = self.c.repo / ".git"
        if git_dir.exists():
            print("  Using git archive (tracked files only)...")
            try:
                _run(
                    ["git", "-C", str(self.c.repo), "archive", "--format=tar",
                     "HEAD", "-o", str(archive_path)]
                )
                return archive_path
            except subprocess.CalledProcessError:
                print("  Git archive failed, falling back to manual tar...")

        print("  Creating tar archive with exclusions...")
        exclude = {
            ".git", ".github", ".gitignore", ".dockerignore",
            ".env", ".env.*", "vendor", "node_modules",
            "tmp", "logs", "cache", ".idea", ".vscode",
            "composer.lock", "package-lock.json",
            "__pycache__", ".DS_Store",
        }

        def tar_filter(tarinfo):
            rel = Path(tarinfo.name)
            for part in rel.parts:
                if part in exclude:
                    return None
                if any(fnmatch.fnmatch(part, p) for p in exclude if "*" in p):
                    return None
            return tarinfo

        with tarfile.open(archive_path, "w") as tar:
            tar.add(self.c.repo, arcname=".", filter=tar_filter, recursive=True)
        return archive_path

    def extract_archive(self, archive_path: Path):
        with tarfile.open(archive_path, "r") as tar:
            tar.extractall(path=self.c.package_dir)

    def copy_config_overrides(self):
        config_dir = self.c.common_dir / "config"
        pkg_config = self.c.package_dir / "config"
        if not config_dir.exists() or not pkg_config.exists():
            return
        files = list(config_dir.glob("*.example.php"))
        if files:
            print(f"  Copying {len(files)} config override(s)...")
            for f in files:
                shutil.copy2(f, pkg_config / f.name)

    # -- Docker builds -----------------------------------------------------

    def ensure_base_image(self, rebuild: bool):
        if rebuild:
            try:
                self.docker_client.images.remove(self.c.base_image, force=True)
                print(f"  Removed existing: {self.c.base_image}")
            except docker.errors.ImageNotFound:
                pass

        try:
            self.docker_client.images.get(self.c.base_image)
            print(f"  Base image found: {self.c.base_image} (cached)")
            return
        except docker.errors.ImageNotFound:
            pass

        print("  Building base image (this may take 20-30 min on first run)...")
        _run(
            ["docker", "compose", "-f", str(self.c.builder_compose_file),
             "--profile", "base-build", "build", "frankenphp-base-builder"],
            cwd=self.c.builder_dir,
            env=self.c.build_env(),
        )

    def build_app_embed(self):
        _run(
            ["docker", "compose", "-f", str(self.c.builder_compose_file),
             "build", "orangescrum-app-builder"],
            cwd=self.c.builder_dir,
            env=self.c.build_env(),
        )

    def stop_builder_stack(self):
        _run(
            ["docker", "compose", "-f", str(self.c.builder_compose_file),
             "down", "--remove-orphans"],
            cwd=self.c.builder_dir,
        )

    # -- Binary extraction -------------------------------------------------

    def extract_binary(self):
        """Extract FrankenPHP binary using docker create + cp (no running container)."""
        binary_dir = self.c.binary_path.parent
        binary_dir.mkdir(parents=True, exist_ok=True)

        container_id = _run_capture(
            ["docker", "create", self.c.app_image, "true"]
        )
        try:
            _run([
                "docker", "cp",
                f"{container_id}:/go/src/app/dist/frankenphp-linux-x86_64",
                str(self.c.binary_path),
            ])
        finally:
            subprocess.call(
                ["docker", "rm", "-f", container_id], stdout=subprocess.DEVNULL
            )

        self.c.binary_path.chmod(0o755)
        size_mb = self.c.binary_path.stat().st_size / (1024 * 1024)
        print(f"  Binary: {self.c.binary_path} ({size_mb:.1f} MB)")

    def validate_binary(self):
        """Verify the extracted binary is a valid static ELF."""
        bp = self.c.binary_path
        if not bp.exists():
            raise RuntimeError(f"Binary not found: {bp}")

        size = bp.stat().st_size
        if size < 50 * 1024 * 1024:
            raise RuntimeError(f"Binary too small ({size} bytes), expected >50 MB")

        with open(bp, "rb") as f:
            magic = f.read(4)
        if magic != b"\x7fELF":
            raise RuntimeError(f"Not a valid ELF binary (magic: {magic!r})")

        result = subprocess.run(["file", str(bp)], capture_output=True, text=True)
        is_static = "statically linked" in result.stdout
        print(f"  ELF: valid, {size / (1024*1024):.1f} MB, "
              f"{'static' if is_static else 'DYNAMIC (warning)'}")

    # -- Deployment packages -----------------------------------------------

    def build_deployment_folders(self):
        self.c.dist_base_dir.mkdir(parents=True, exist_ok=True)
        env = self.c.dist_env()

        for name, source_dir in [
            ("Docker", self.c.docker_source_dir),
            ("Native", self.c.native_source_dir),
        ]:
            script = source_dir / "build.sh"
            if script.exists():
                print(f"  Building {name} deployment...")
                _run(["bash", str(script)], cwd=source_dir, env=env)
            else:
                print(f"  [WARN] {script} not found")

    def write_manifests(self):
        """Write build-manifest.json to both dist directories."""
        for d in [self.c.dist_docker_dir, self.c.dist_native_dir]:
            if d.exists():
                path = self.c.write_manifest(d)
                print(f"  Manifest: {path}")

    def write_checksums(self):
        """Write SHA256 checksum files next to the binaries in dist."""
        pairs = [
            (self.c.dist_docker_dir / "orangescrum-app" / self.c.binary_name,),
            (self.c.dist_native_dir / "bin" / "orangescrum",),
        ]
        for (binary,) in pairs:
            if binary.exists():
                sha = hashlib.sha256(binary.read_bytes()).hexdigest()
                checksum_file = binary.with_suffix(binary.suffix + ".sha256")
                checksum_file.write_text(f"{sha}  {binary.name}\n")
                print(f"  Checksum: {checksum_file.name}")

    def prune_old_dists(self):
        dist_root = self.c.root / "dist"
        if not dist_root.exists():
            return
        builds = sorted(
            [d for d in dist_root.iterdir() if d.is_dir()],
            key=lambda p: p.name, reverse=True,
        )
        to_remove = builds[self.c.dist_keep_count:]
        if to_remove:
            print(f"  Pruning {len(to_remove)} old build(s)...")
            for old in to_remove:
                shutil.rmtree(old)

    def verify_dist(self, dist_dir: Path) -> bool:
        """Verify a dist package against its manifest."""
        manifest_path = dist_dir / "build-manifest.json"
        if not manifest_path.exists():
            print(f"[FAIL] No build-manifest.json in {dist_dir}")
            return False

        manifest = json.loads(manifest_path.read_text())
        print(f"  Version: {manifest.get('version')}")
        print(f"  Git SHA: {manifest.get('git_sha')}")
        print(f"  Built: {manifest.get('build_timestamp')}")

        expected_sha = manifest.get("binary_sha256")
        if not expected_sha:
            print("  [WARN] No binary_sha256 in manifest")
            return True

        # Find the binary
        for candidate in [
            dist_dir / "orangescrum-app" / "osv4-prod",
            dist_dir / "bin" / "orangescrum",
        ]:
            if candidate.exists():
                actual_sha = hashlib.sha256(candidate.read_bytes()).hexdigest()
                if actual_sha == expected_sha:
                    print(f"  [OK] Binary SHA256 matches: {actual_sha[:16]}...")
                    return True
                else:
                    print(f"  [FAIL] SHA256 mismatch!")
                    print(f"    Expected: {expected_sha}")
                    print(f"    Actual:   {actual_sha}")
                    return False

        print("  [FAIL] Binary not found in dist")
        return False

    # -- Deploy (optional) -------------------------------------------------

    def deploy(self, env_file: Path, env_overrides: dict[str, str]):
        compose_file = self.c.dist_docker_dir / "docker-compose.yaml"
        env = self.c.build_env()
        env.update(env_overrides)

        _run(
            ["docker", "compose", "-f", str(compose_file),
             "--env-file", str(env_file), "up", "-d", "--build"],
            cwd=self.c.dist_docker_dir, env=env,
        )

    def wait_healthy(self, timeout_s: int = 180) -> bool:
        compose_file = self.c.dist_docker_dir / "docker-compose.yaml"
        print("  Waiting for healthy status...")
        start = time.time()
        while time.time() - start < timeout_s:
            try:
                cid = _run_capture(
                    ["docker", "compose", "-f", str(compose_file),
                     "ps", "-q", "orangescrum-app"],
                    cwd=self.c.dist_docker_dir,
                )
                if cid:
                    c = self.docker_client.containers.get(cid)
                    health = c.attrs.get("State", {}).get("Health", {}).get("Status")
                    if health == "healthy":
                        print("  [OK] Healthy")
                        return True
                    status = c.attrs.get("State", {}).get("Status")
                    if status in {"exited", "dead"}:
                        raise RuntimeError(f"Container {status}")
            except docker.errors.NotFound:
                pass
            except RuntimeError:
                raise
            time.sleep(3)
        print(f"  [WARN] Not healthy after {timeout_s}s")
        return False

    # -- Main build pipeline -----------------------------------------------

    def run(self, args) -> int:
        build_start = time.time()

        print("=" * 60)
        print(f"OrangeScrum V4 FrankenPHP Builder  {self.c.version}")
        print(f"  FrankenPHP {self.c.frankenphp_version} / PHP {self.c.php_version}")
        print(f"  Git: {self.c.git_sha}  Host: {self.c.builder_host}")
        print("=" * 60)

        if not self.check():
            print("\nPre-flight checks failed.")
            return 1

        try:
            # -- Prepare application source --
            if not args.skip_archive:
                self._step("Prepare package directory")
                _clean_dir(self.c.package_dir)

                self._step("Archive application source")
                archive = self.archive_app()

                self._step("Extract to package directory")
                self.extract_archive(archive)
                archive.unlink(missing_ok=True)

                self._step("Copy configuration overrides")
                self.copy_config_overrides()
            elif args.clean and self.c.package_dir.exists():
                _clean_dir(self.c.package_dir)

            # -- Build FrankenPHP --
            if not args.skip_base:
                self._step("Ensure FrankenPHP base image")
                self.ensure_base_image(args.rebuild_base)

            self._step("Embed application into FrankenPHP")
            self.build_app_embed()

            self._step("Extract binary")
            self.extract_binary()

            self._step("Validate binary")
            self.validate_binary()

            # -- Package --
            self._step("Build deployment packages")
            self.build_deployment_folders()

            self._step("Write manifests and checksums")
            self.write_manifests()
            self.write_checksums()

            self._step("Clean up builder")
            self.stop_builder_stack()

            self._step("Prune old builds")
            self.prune_old_dists()

            if not args.keep_package and self.c.package_dir.exists():
                shutil.rmtree(self.c.package_dir)

            # -- Optional deploy --
            if not args.skip_deploy:
                self._step("Deploy (Docker)")
                env_example = self.c.dist_docker_dir / ".env.example"
                env_default = self.c.dist_docker_dir / ".env"
                if not env_default.exists() and env_example.exists():
                    shutil.copy2(env_example, env_default)
                env_file = Path(args.env_file) if args.env_file else env_default
                overrides = _env_overrides_from_args(args)
                self.deploy(env_file, overrides)
                self.wait_healthy()

            # -- Summary --
            elapsed = time.time() - build_start
            print("\n" + "=" * 60)
            print(f"Build Complete!  ({elapsed:.0f}s)")
            print("=" * 60)
            print(f"\n  Binary:   {self.c.binary_path}")
            print(f"  Docker:   {self.c.dist_docker_dir}")
            print(f"  Native:   {self.c.dist_native_dir}")
            print(f"  Manifest: build-manifest.json")
            print(f"\n  Deploy:")
            print(f"    scp -r {self.c.dist_base_dir} user@server:/opt/orangescrum/")
            print(f"    cd /opt/orangescrum/{self.c.timestamp}/dist-docker")
            print(f"    cp .env.example .env && nano .env")
            print(f"    docker compose up -d")
            print()

        except Exception as e:
            print(f"\n[ERROR] {e}")
            return 1
        finally:
            self.close()

        return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _env_overrides_from_args(args) -> dict[str, str]:
    overrides: dict[str, str] = {}
    for attr, key in [
        ("app_port", "APP_PORT"), ("app_bind_ip", "APP_BIND_IP"),
        ("db_host", "DB_HOST"), ("db_port", "DB_PORT"),
        ("db_username", "DB_USERNAME"), ("db_password", "DB_PASSWORD"),
        ("db_name", "DB_NAME"),
    ]:
        val = getattr(args, attr, None)
        if val is not None:
            overrides[key] = str(val)
    return overrides


def parse_args():
    p = argparse.ArgumentParser(
        description="Build FrankenPHP embedded binary for OrangeScrum V4"
    )

    # Build control
    p.add_argument("--check", action="store_true",
                    help="Pre-flight checks only")
    p.add_argument("--verify", metavar="DIST_DIR",
                    help="Verify a built dist package")
    p.add_argument("--rebuild-base", action="store_true",
                    help="Force rebuild base image (~30 min)")
    p.add_argument("--skip-deploy", action="store_true",
                    help="Build only, don't deploy")
    p.add_argument("--skip-archive", action="store_true",
                    help="Skip git archive step")
    p.add_argument("--skip-base", action="store_true",
                    help="Skip base image check")
    p.add_argument("--keep-package", action="store_true",
                    help="Keep builder/package/ after build")
    p.add_argument("--clean", action="store_true",
                    help="Clean package dir before building")

    # Config
    p.add_argument("--config", metavar="PATH",
                    help="Path to build.conf (default: ./build.conf)")
    p.add_argument("--version", dest="version",
                    help="Override version from VERSION file")

    # Deploy options
    p.add_argument("--env-file", help="Path to .env file for deployment")
    p.add_argument("--app-port", type=int, help="App port")
    p.add_argument("--app-bind-ip", help="App bind IP")
    p.add_argument("--db-host", help="Database host")
    p.add_argument("--db-port", type=int, help="Database port")
    p.add_argument("--db-username", help="Database user")
    p.add_argument("--db-password", help="Database password")
    p.add_argument("--db-name", help="Database name")

    return p.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(__file__).parent.resolve()
    config_path = Path(args.config) if args.config else root / "build.conf"

    config = BuildConfig.from_args(args, root=root, config_path=config_path)
    builder = Builder(config)

    if args.check:
        return 0 if builder.check() else 1

    if args.verify:
        return 0 if builder.verify_dist(Path(args.verify).resolve()) else 1

    return builder.run(args)


if __name__ == "__main__":
    raise SystemExit(main())
