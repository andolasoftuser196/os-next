"""Build configuration for OrangeScrum FrankenPHP Cloud Builder.

Reads VERSION file + build.conf + CLI args and produces a frozen BuildConfig
that every part of the build pipeline references. No globals, no hardcoded values.
"""

from __future__ import annotations

import configparser
import hashlib
import json
import os
import socket
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class BuildConfig:
    # Version & metadata
    version: str
    timestamp: str
    git_sha: str
    build_date: str
    builder_host: str

    # Paths (all resolved to absolute)
    root: Path              # cloud-builder/ directory
    repo: Path              # OrangeScrum V4 app source
    builder_dir: Path       # builder/ (Dockerfiles, Caddyfile, php.ini)
    package_dir: Path       # builder/package/ (temp extraction)
    common_dir: Path        # orangescrum-cloud-common/
    docker_source_dir: Path # orangescrum-cloud-docker/
    native_source_dir: Path # orangescrum-cloud-native/
    dist_base_dir: Path     # dist/{timestamp}/
    dist_docker_dir: Path   # dist/{timestamp}/dist-docker/
    dist_native_dir: Path   # dist/{timestamp}/dist-native/
    binary_path: Path       # orangescrum-cloud-common/orangescrum-app/<binary_name>

    # Build parameters
    frankenphp_version: str
    php_version: str
    php_extensions: str
    base_image: str         # full image name with tag (e.g. orangescrum-cloud-base:latest)
    app_image: str          # full image name with tag
    no_compress: int
    dist_keep_count: int
    binary_name: str

    # Runtime parameters
    uid: int
    gid: int

    # Builder compose file (derived)
    builder_compose_file: Path = field(default=Path("."))

    def __post_init__(self):
        # frozen=True prevents assignment, but we can use object.__setattr__ in __post_init__
        object.__setattr__(
            self, "builder_compose_file", self.builder_dir / "docker-compose.yaml"
        )

    @classmethod
    def from_args(
        cls,
        args,
        root: Path | None = None,
        config_path: Path | None = None,
    ) -> BuildConfig:
        """Build a config from CLI args + config files.

        Precedence (highest to lowest):
        1. CLI args
        2. Environment variables
        3. build.conf
        4. Compiled defaults
        """
        root = (root or Path(__file__).parent.parent).resolve()
        config_path = config_path or root / "build.conf"

        # Read build.conf
        cp = configparser.ConfigParser()
        if config_path.exists():
            cp.read(config_path)

        def conf(section: str, key: str, default: str = "") -> str:
            return cp.get(section, key, fallback=default).strip()

        # Version: CLI > env > VERSION file
        version = (
            getattr(args, "version", None)
            or os.environ.get("VERSION")
            or _read_version_file(root / "VERSION")
        )

        # Build parameters
        frankenphp_version = os.environ.get(
            "FRANKENPHP_VERSION", conf("build", "frankenphp_version", "1.11.1")
        )
        php_version = conf("build", "php_version", "8.3")
        base_image_name = os.environ.get(
            "BASE_IMAGE_NAME", conf("build", "base_image_name", "orangescrum-cloud-base")
        )
        app_image_name = os.environ.get(
            "APP_IMAGE_NAME", conf("build", "app_image_name", "orangescrum-cloud-app")
        )
        no_compress = int(conf("build", "no_compress", "1"))
        app_source = conf("build", "app_source", "../apps/orangescrum-v4")
        dist_keep_count = int(conf("build", "dist_keep_count", "3"))
        binary_name = conf("build", "binary_name", "osv4-prod")
        php_extensions = conf("php_extensions", "list", "")

        uid = int(conf("runtime", "uid", "1000"))
        gid = int(conf("runtime", "gid", "1000"))

        # Paths
        repo = (root / app_source).resolve()
        builder_dir = root / "builder"
        timestamp = time.strftime("%Y%m%d_%H%M%S")

        # Git SHA
        git_sha = _git_sha(repo)

        return cls(
            version=version,
            timestamp=timestamp,
            git_sha=git_sha,
            build_date=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            builder_host=socket.gethostname(),
            root=root,
            repo=repo,
            builder_dir=builder_dir,
            package_dir=builder_dir / "package",
            common_dir=root / "orangescrum-cloud-common",
            docker_source_dir=root / "orangescrum-cloud-docker",
            native_source_dir=root / "orangescrum-cloud-native",
            dist_base_dir=root / "dist" / timestamp,
            dist_docker_dir=root / "dist" / timestamp / "dist-docker",
            dist_native_dir=root / "dist" / timestamp / "dist-native",
            binary_path=(root / "orangescrum-cloud-common" / "orangescrum-app" / binary_name),
            frankenphp_version=frankenphp_version,
            php_version=php_version,
            php_extensions=php_extensions,
            base_image=f"{base_image_name}:latest",
            app_image=f"{app_image_name}:latest",
            no_compress=no_compress,
            dist_keep_count=dist_keep_count,
            binary_name=binary_name,
            uid=uid,
            gid=gid,
        )

    def build_env(self) -> dict[str, str]:
        """Return environment variables to pass to Docker build commands."""
        env = os.environ.copy()
        env["DOCKER_BUILDKIT"] = "1"
        env["BUILD_DATE"] = str(int(time.time()))
        env["FRANKENPHP_VERSION"] = self.frankenphp_version
        env["PHP_VERSION"] = self.php_version
        env["BASE_IMAGE_NAME"] = self.base_image.rsplit(":", 1)[0]
        env["APP_IMAGE_NAME"] = self.app_image.rsplit(":", 1)[0]
        env["NO_COMPRESS"] = str(self.no_compress)
        env["VERSION"] = self.version
        return env

    def dist_env(self) -> dict[str, str]:
        """Return environment variables for dist build scripts."""
        env = os.environ.copy()
        env["DIST_DOCKER_DIR"] = str(self.dist_docker_dir)
        env["DIST_NATIVE_DIR"] = str(self.dist_native_dir)
        env["BUILD_TIMESTAMP"] = self.timestamp
        env["VERSION"] = self.version
        return env

    def manifest(self) -> dict:
        """Generate a build manifest dict. Call after binary is built."""
        result = {
            "version": self.version,
            "git_sha": self.git_sha,
            "build_timestamp": self.build_date,
            "builder_host": self.builder_host,
            "frankenphp_version": self.frankenphp_version,
            "php_version": self.php_version,
            "binary_name": self.binary_name,
        }
        if self.binary_path.exists():
            result["binary_sha256"] = _sha256(self.binary_path)
            result["binary_size_bytes"] = self.binary_path.stat().st_size
        return result

    def write_manifest(self, dest_dir: Path) -> Path:
        """Write build-manifest.json to dest_dir and return the path."""
        dest_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = dest_dir / "build-manifest.json"
        manifest_path.write_text(json.dumps(self.manifest(), indent=2) + "\n")
        return manifest_path


def _read_version_file(path: Path) -> str:
    if path.exists():
        return path.read_text().strip()
    return "v0.0.0-unknown"


def _git_sha(repo: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(repo), "rev-parse", "--short", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return "unknown"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()
