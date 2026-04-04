"""Integration tests for the Controller API — full dev cycle.

Requires: base services running, controller healthy.
Run:  pytest tests/test_controller_api.py -v
"""

import os
import subprocess
import sqlite3
import time
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
API_URL = os.environ.get("API_URL", "http://127.0.0.1:8900")
BRANCH_NAME = "feat/pytest-verify"


# ─── Helpers ─────────────────────────────────────────────────────────────────


def api_get(api, path):
    return api.get(f"{API_URL}{path}")


def api_post(api, path, json=None):
    return api.post(f"{API_URL}{path}", json=json)


def api_delete(api, path):
    return api.delete(f"{API_URL}{path}")


def wait_healthy(api, name, timeout=120):
    """Poll GET /api/instances until the named instance is healthy."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = api_get(api, "/api/instances")
            for inst in r.json().get("instances", []):
                if inst["name"] == name and inst["container_health"] == "healthy":
                    return True
        except Exception:
            pass  # controller may be restarting
        time.sleep(5)
    return False


# ─── Phase 1: System health ─────────────────────────────────────────────────


class TestSystemHealth:
    def test_status(self, api):
        r = api_get(api, "/api/status")
        assert r.status_code == 200
        data = r.json()
        assert data["domain"]
        assert data["protocol"] in ("http", "https")
        assert "postgres16" in data["services"]
        assert data["services"]["postgres16"]["status"] == "running"

    def test_instances_endpoint(self, api):
        r = api_get(api, "/api/instances")
        assert r.status_code == 200
        assert r.json()["domain"]

    def test_snapshots_endpoint(self, api):
        r = api_get(api, "/api/snapshots")
        assert r.status_code == 200


# ─── Phase 2: Instance lifecycle ─────────────────────────────────────────────


class TestInstanceLifecycle:
    """Create a plain instance, verify it starts, stop it, start it, destroy it."""

    NAME = "pytest-main"

    def test_create(self, api):
        r = api_post(api, "/api/instances", {
            "name": self.NAME,
            "type": "v4",
            "subdomain": "pytest-main",
        })
        assert r.status_code == 200, r.text
        assert "created" in r.json()["message"]
        assert "pytest-main" in r.json()["url"]

    def test_wait_healthy(self, api):
        assert wait_healthy(api, self.NAME), f"{self.NAME} did not become healthy"

    def test_listed(self, api):
        r = api_get(api, "/api/instances")
        names = [i["name"] for i in r.json()["instances"]]
        assert self.NAME in names

    def test_logs(self, api):
        r = api_get(api, f"/api/instances/{self.NAME}/logs?tail=5")
        assert r.status_code == 200
        assert len(r.json()["lines"]) > 0

    def test_stats(self, api):
        r = api_get(api, f"/api/instances/{self.NAME}/stats")
        assert r.status_code == 200
        assert r.json()["mem_limit_mb"] > 0

    def test_stop(self, api):
        r = api_post(api, f"/api/instances/{self.NAME}/stop")
        assert r.status_code == 200
        r = api_get(api, "/api/instances")
        inst = next(i for i in r.json()["instances"] if i["name"] == self.NAME)
        assert inst["container_status"] != "running"

    def test_start(self, api):
        r = api_post(api, f"/api/instances/{self.NAME}/start")
        assert r.status_code == 200
        assert wait_healthy(api, self.NAME), "Failed to restart"

    def test_destroy(self, api):
        r = api_delete(api, f"/api/instances/{self.NAME}?drop_db=true")
        assert r.status_code == 200
        r = api_get(api, "/api/instances")
        names = [i["name"] for i in r.json()["instances"]]
        assert self.NAME not in names


# ─── Phase 3: Branch instance + isolation ────────────────────────────────────


class TestBranchIsolation:
    """Create a feature branch instance, verify worktree, code isolation, cleanup."""

    MAIN = "pytest-shared"
    FEAT = "pytest-branch"

    def test_create_main(self, api):
        r = api_post(api, "/api/instances", {
            "name": self.MAIN,
            "type": "v4",
            "subdomain": "pytest-shared",
        })
        assert r.status_code == 200, r.text

    def test_create_branch(self, api):
        r = api_post(api, "/api/instances", {
            "name": self.FEAT,
            "type": "v4",
            "subdomain": "pytest-branch",
            "branch": BRANCH_NAME,
        })
        assert r.status_code == 200, r.text

    def test_both_healthy(self, api):
        assert wait_healthy(api, self.MAIN), f"{self.MAIN} not healthy"
        assert wait_healthy(api, self.FEAT, timeout=180), f"{self.FEAT} not healthy"

    def test_branch_listed_correctly(self, api):
        r = api_get(api, "/api/instances")
        instances = {i["name"]: i for i in r.json()["instances"]}
        assert instances[self.MAIN]["branch"] == ""
        assert instances[self.FEAT]["branch"] == BRANCH_NAME

    def test_worktree_exists(self):
        branch_dir = BRANCH_NAME.replace("/", "-")
        wt = PROJECT_ROOT / "apps" / "worktrees" / "orangescrum-v4" / branch_dir
        assert wt.exists(), f"Worktree not found: {wt}"
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=str(wt), capture_output=True, text=True,
        )
        assert result.stdout.strip() == BRANCH_NAME

    def test_worktree_not_prunable(self):
        """Worktree should use host paths, not /project paths."""
        result = subprocess.run(
            ["git", "worktree", "list"],
            cwd=str(PROJECT_ROOT / "apps" / "orangescrum-v4"),
            capture_output=True, text=True,
        )
        assert "prunable" not in result.stdout, f"Worktree is prunable:\n{result.stdout}"

    def test_code_isolation(self):
        """Write a marker in the feature worktree, verify main is unaffected."""
        branch_dir = BRANCH_NAME.replace("/", "-")
        wt = PROJECT_ROOT / "apps" / "worktrees" / "orangescrum-v4" / branch_dir
        main_src = PROJECT_ROOT / "apps" / "orangescrum-v4"

        marker = "<!-- PYTEST_ISOLATION_MARKER -->"
        feat_file = wt / "webroot" / "index.php"
        main_file = main_src / "webroot" / "index.php"

        original = feat_file.read_text()
        feat_file.write_text(marker + "\n" + original)

        try:
            assert marker in feat_file.read_text()
            assert marker not in main_file.read_text()
        finally:
            feat_file.write_text(original)

    def test_container_isolation(self):
        """Feature container sees the worktree, main sees shared source."""
        feat_inspect = subprocess.run(
            ["docker", "inspect", "user196-online-pytest-branch",
             "--format", '{{range .Mounts}}{{if eq .Destination "/var/www/html"}}{{.Source}}{{end}}{{end}}'],
            capture_output=True, text=True,
        )
        main_inspect = subprocess.run(
            ["docker", "inspect", "user196-online-pytest-shared",
             "--format", '{{range .Mounts}}{{if eq .Destination "/var/www/html"}}{{.Source}}{{end}}{{end}}'],
            capture_output=True, text=True,
        )
        assert feat_inspect.stdout.strip() != main_inspect.stdout.strip()

    def test_registry_correct(self):
        """SQLite registry has both instances with correct metadata."""
        db = sqlite3.connect(str(PROJECT_ROOT / "instances" / "registry.db"))
        db.row_factory = sqlite3.Row
        rows = {r["name"]: dict(r) for r in db.execute("SELECT * FROM instances").fetchall()}
        db.close()

        assert self.MAIN in rows
        assert self.FEAT in rows
        assert rows[self.FEAT]["branch"] == BRANCH_NAME
        assert rows[self.FEAT]["worktree_path"] != ""
        assert rows[self.MAIN]["branch"] == ""
        assert rows[self.MAIN]["worktree_path"] == ""

    def test_destroy_branch(self, api):
        r = api_delete(api, f"/api/instances/{self.FEAT}?drop_db=true")
        assert r.status_code == 200

        branch_dir = BRANCH_NAME.replace("/", "-")
        wt = PROJECT_ROOT / "apps" / "worktrees" / "orangescrum-v4" / branch_dir
        time.sleep(1)
        assert not wt.exists(), f"Worktree not cleaned up: {wt}"

    def test_destroy_main(self, api):
        r = api_delete(api, f"/api/instances/{self.MAIN}?drop_db=true")
        assert r.status_code == 200

    def test_all_cleaned_up(self, api):
        r = api_get(api, "/api/instances")
        names = [i["name"] for i in r.json()["instances"]]
        assert self.MAIN not in names
        assert self.FEAT not in names


# ─── Phase 4: Validation & edge cases ───────────────────────────────────────


class TestEdgeCases:
    def test_create_reserved_subdomain(self, api):
        r = api_post(api, "/api/instances", {
            "name": "pytest-bad",
            "type": "v4",
            "subdomain": "control",
        })
        assert r.status_code == 400

    def test_create_duplicate_name(self, api):
        api_post(api, "/api/instances", {"name": "pytest-dup", "type": "v4", "subdomain": "pytest-dup"})
        r = api_post(api, "/api/instances", {"name": "pytest-dup", "type": "v4", "subdomain": "pytest-dup2"})
        assert r.status_code == 409
        api_delete(api, "/api/instances/pytest-dup?drop_db=true")

    def test_destroy_nonexistent(self, api):
        r = api_delete(api, "/api/instances/does-not-exist")
        assert r.status_code == 404

    def test_invalid_instance_type(self, api):
        r = api_post(api, "/api/instances", {
            "name": "pytest-bad",
            "type": "invalid",
            "subdomain": "pytest-bad",
        })
        assert r.status_code == 422

    def test_services_stats(self, api):
        r = api_get(api, "/api/services/stats")
        assert r.status_code == 200
        assert "postgres16" in r.json()
