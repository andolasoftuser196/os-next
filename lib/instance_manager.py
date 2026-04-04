"""Instance lifecycle — create, destroy, start, stop, list, logs, shell."""

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from .output import Colors, print_colored, print_header
from .registry import (
    RESERVED_SUBDOMAINS, DEFAULT_SOURCE_PATHS,
    load_registry, save_registry, get_project_context,
)
from .database import instance_db_restore


def instance_create(args):
    """Create a new dynamic instance"""
    name = args.name
    instance_type = args.type
    subdomain = args.subdomain or name
    source = args.source
    branch = getattr(args, 'branch', None)

    if not re.match(r'^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$', name):
        print_colored("Error: Instance name must be lowercase alphanumeric with hyphens (e.g., 'v4-main', 'next')", Colors.RED)
        sys.exit(1)

    if subdomain in RESERVED_SUBDOMAINS:
        print_colored(f"Error: Subdomain '{subdomain}' is reserved. Reserved: {', '.join(sorted(RESERVED_SUBDOMAINS))}", Colors.RED)
        sys.exit(1)

    registry = load_registry()

    if name in registry.get('instances', {}):
        print_colored(f"Error: Instance '{name}' already exists. Use 'instance destroy' first.", Colors.RED)
        sys.exit(1)

    for inst_name, inst in registry.get('instances', {}).items():
        if inst.get('subdomain') == subdomain:
            print_colored(f"Error: Subdomain '{subdomain}' already used by instance '{inst_name}'.", Colors.RED)
            sys.exit(1)

    ctx = get_project_context()
    domain = ctx['domain']
    domain_prefix = ctx['domain_prefix']

    if not source:
        source = DEFAULT_SOURCE_PATHS.get(instance_type, DEFAULT_SOURCE_PATHS['v4'])

    if not Path(source).exists():
        print_colored(f"Error: Source path '{source}' does not exist.", Colors.RED)
        sys.exit(1)

    # If --branch is specified, create a git worktree under apps/worktrees/<repo>/<branch>
    worktree_path = None
    if branch:
        repo_name = Path(source).name
        branch_dir = branch.replace('/', '-')
        worktree_dir = Path('apps') / 'worktrees' / repo_name
        worktree_dir.mkdir(parents=True, exist_ok=True)
        worktree_path = worktree_dir / branch_dir

        if worktree_path.exists():
            print_colored(f"Error: Worktree path '{worktree_path}' already exists.", Colors.RED)
            sys.exit(1)

        print_colored(f"Creating git worktree for branch '{branch}'...", Colors.BLUE)
        source_repo = str(Path(source).resolve())
        try:
            subprocess.run(
                ['git', 'fetch', '--all'],
                cwd=source_repo, capture_output=True, text=True
            )
            result = subprocess.run(
                ['git', 'worktree', 'add', str(worktree_path.resolve()), branch],
                cwd=source_repo, capture_output=True, text=True
            )
            if result.returncode != 0:
                result = subprocess.run(
                    ['git', 'worktree', 'add', '-b', branch, str(worktree_path.resolve()), 'main'],
                    cwd=source_repo, capture_output=True, text=True
                )
                if result.returncode != 0:
                    print_colored(f"Error: Could not create worktree: {result.stderr.strip()}", Colors.RED)
                    print_colored(f"  Available branches: git -C {source} branch -a", Colors.YELLOW)
                    sys.exit(1)
                print_colored(f"  Created new branch '{branch}' from main", Colors.GREEN)
            print_colored(f"  Worktree created at {worktree_path} (branch: {branch})", Colors.GREEN)

            # Copy composer.lock so worktree uses `composer install` (fast) not `composer update`
            lock_file = Path(source_repo) / 'composer.lock'
            if lock_file.exists():
                shutil.copy2(str(lock_file), str(worktree_path / 'composer.lock'))
                print_colored(f"  Copied composer.lock from source repo", Colors.GREEN)
        except subprocess.CalledProcessError as e:
            print_colored(f"Error: Could not create worktree: {e.stderr.strip()}", Colors.RED)
            sys.exit(1)

        source = str(worktree_path)

    source_abs = str(Path(source).resolve())

    db_name = f"{instance_type}_{name}".replace('-', '_')
    db_user = 'postgres'
    db_password = 'postgres'

    try:
        import secrets
        security_salt = hashlib.sha256(secrets.token_bytes(64)).hexdigest()
    except Exception:
        import uuid
        security_salt = hashlib.sha256(uuid.uuid4().bytes + uuid.uuid4().bytes).hexdigest()

    print_header(f"Creating Instance: {name}")
    print(f"Type: {instance_type}")
    print(f"Subdomain: {subdomain}.{domain}")
    print(f"Source: {source}")
    if branch:
        print(f"Branch: {branch} (worktree)")
    print(f"Database: {db_name}")
    print()

    templates_dir = Path('templates')
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True
    )

    template_context = {
        'instance_name': name,
        'instance_type': instance_type,
        'instance_subdomain': subdomain,
        'domain': domain,
        'domain_prefix': domain_prefix,
        'enable_https': ctx['enable_https'],
        'source_path': source_abs,
        'project_root': ctx['project_root'],
        'db_name': db_name,
        'db_user': db_user,
        'db_password': db_password,
        'security_salt': security_salt,
        'cache_engine': ctx['cache_engine'],
        'generated_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'node_version': '20',
        'restricted': getattr(args, 'restricted', False),
    }

    shared_env = Path('instances/shared.env')
    if not shared_env.exists():
        print_colored("Warning: instances/shared.env not found. Run './generate-config.py <domain>' to generate it.", Colors.YELLOW)

    instance_dir = Path(f'instances/{name}')
    instance_dir.mkdir(parents=True, exist_ok=True)

    print_colored("Generating instance .env...", Colors.BLUE)
    tpl = env.get_template('instance.env.j2')
    (instance_dir / '.env').write_text(tpl.render(template_context))
    print_colored(f"  Generated instances/{name}/.env", Colors.GREEN)

    print_colored("Generating instance docker-compose.yml...", Colors.BLUE)
    tpl = env.get_template('instance-docker-compose.yml.j2')
    (instance_dir / 'docker-compose.yml').write_text(tpl.render(template_context))
    print_colored(f"  Generated instances/{name}/docker-compose.yml", Colors.GREEN)

    print_colored("Generating Traefik routing config...", Colors.BLUE)
    tpl = env.get_template('instance-traefik.yml.j2')
    traefik_file = Path(f'traefik/instance-{name}.yml')
    traefik_file.write_text(tpl.render(template_context))
    print_colored(f"  Generated traefik/instance-{name}.yml (auto-discovered by Traefik)", Colors.GREEN)

    # Create database
    print_colored("Creating PostgreSQL database...", Colors.BLUE)
    pg_container = f"{domain_prefix}-postgres16"
    try:
        subprocess.run([
            'docker', 'exec', pg_container, 'psql', '-U', 'postgres', '-c',
            f"DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '{db_user}') "
            f"THEN CREATE ROLE {db_user} WITH LOGIN PASSWORD '{db_password}'; END IF; END $$;"
        ], check=True, capture_output=True, text=True)

        result = subprocess.run([
            'docker', 'exec', pg_container, 'psql', '-U', 'postgres', '-tAc',
            f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'"
        ], capture_output=True, text=True)

        if '1' not in result.stdout:
            subprocess.run([
                'docker', 'exec', pg_container, 'psql', '-U', 'postgres', '-c',
                f"CREATE DATABASE {db_name} OWNER {db_user};"
            ], check=True, capture_output=True, text=True)
            print_colored(f"  Created database: {db_name}", Colors.GREEN)
        else:
            print_colored(f"  Database already exists: {db_name}", Colors.YELLOW)

        subprocess.run([
            'docker', 'exec', pg_container, 'psql', '-U', 'postgres', '-c',
            f"GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {db_user};"
        ], check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print_colored(f"  Warning: Could not create database (is postgres16 running?): {e}", Colors.YELLOW)
        print_colored("  Run 'docker compose up -d postgres16' first, then './generate-config.py instance db-setup --name " + name + "'", Colors.YELLOW)
    except FileNotFoundError:
        print_colored("  Warning: Docker not found. Database will be created when you run db-setup.", Colors.YELLOW)

    # Start instance
    print_colored("Starting instance...", Colors.BLUE)
    try:
        subprocess.run([
            'docker', 'compose', '-f', str(instance_dir / 'docker-compose.yml'), 'up', '-d'
        ], check=True, capture_output=True, text=True)
        print_colored(f"  Instance started: {name}", Colors.GREEN)
    except subprocess.CalledProcessError as e:
        print_colored(f"  Warning: Could not start instance: {e.stderr}", Colors.YELLOW)
        print_colored(f"  Start manually: docker compose -f instances/{name}/docker-compose.yml up -d", Colors.YELLOW)
    except FileNotFoundError:
        print_colored("  Warning: Docker not found. Start manually when ready.", Colors.YELLOW)

    # Restore from snapshot if requested
    from_snapshot = getattr(args, 'from_snapshot', None)
    if from_snapshot:
        if not Path(from_snapshot).exists():
            print_colored(f"Warning: Snapshot file not found: {from_snapshot}", Colors.YELLOW)
        else:
            print_colored(f"Restoring database from snapshot: {from_snapshot}...", Colors.BLUE)
            restore_args = argparse.Namespace(name=name, snapshot=from_snapshot, drop_existing=False)
            instance_db_restore(restore_args)

    # Update registry
    registry['domain'] = domain
    registry.setdefault('instances', {})
    inst_record = {
        'type': instance_type,
        'subdomain': subdomain,
        'db_name': db_name,
        'db_user': db_user,
        'container_name': f"{domain_prefix}-{name}",
        'source_path': source_abs,
        'created_at': datetime.now().isoformat(),
        'status': 'running',
        'restricted': getattr(args, 'restricted', False),
    }
    if branch:
        inst_record['branch'] = branch
        inst_record['worktree_path'] = str(worktree_path)
    registry['instances'][name] = inst_record
    save_registry(registry)

    protocol = 'https' if ctx['enable_https'] else 'http'
    print()
    print_colored("Instance created successfully!", Colors.GREEN)
    print(f"  URL: {protocol}://{subdomain}.{domain}")
    print(f"  Database: {db_name}")
    print(f"  Container: {domain_prefix}-{name}")
    print(f"  Compose: instances/{name}/docker-compose.yml")
    print()
    print("Next steps:")
    print(f"  Run migrations: ./generate-config.py instance db-setup --name {name}")
    print(f"  View logs: docker compose -f instances/{name}/docker-compose.yml logs -f")
    print()


def instance_list(args):
    """List all instances"""
    registry = load_registry()
    instances = registry.get('instances', {})

    if not instances:
        print_colored("No instances found.", Colors.YELLOW)
        print("Create one with: ./generate-config.py instance create --name <name> --type <v4|selfhosted>")
        return

    domain = registry.get('domain', 'unknown')
    ctx = get_project_context()
    protocol = 'https' if ctx['enable_https'] else 'http'

    print_header("Dynamic Instances")
    print(f"{'Name':<16} {'Type':<12} {'Branch':<16} {'URL':<32} {'Database':<24} {'Status'}")
    print("-" * 116)
    for name, inst in instances.items():
        subdomain = inst.get('subdomain', name)
        url = f"{protocol}://{subdomain}.{domain}"
        branch = inst.get('branch', '(shared)')
        print(f"{name:<16} {inst['type']:<12} {branch:<16} {url:<32} {inst['db_name']:<24} {inst.get('status', 'unknown')}")
    print()


def instance_start(args):
    """Start a stopped instance"""
    registry = load_registry()
    name = args.name

    if name not in registry.get('instances', {}):
        print_colored(f"Error: Instance '{name}' not found.", Colors.RED)
        sys.exit(1)

    instance_dir = Path(f'instances/{name}')
    compose_file = instance_dir / 'docker-compose.yml'
    if not compose_file.exists():
        print_colored(f"Error: Compose file not found: {compose_file}", Colors.RED)
        sys.exit(1)

    print_colored(f"Starting instance '{name}'...", Colors.BLUE)
    subprocess.run(['docker', 'compose', '-f', str(compose_file), 'up', '-d'], check=True)

    registry['instances'][name]['status'] = 'running'
    save_registry(registry)
    print_colored(f"Instance '{name}' started.", Colors.GREEN)


def instance_stop(args):
    """Stop a running instance"""
    registry = load_registry()
    name = args.name

    if name not in registry.get('instances', {}):
        print_colored(f"Error: Instance '{name}' not found.", Colors.RED)
        sys.exit(1)

    instance_dir = Path(f'instances/{name}')
    compose_file = instance_dir / 'docker-compose.yml'
    if not compose_file.exists():
        print_colored(f"Error: Compose file not found: {compose_file}", Colors.RED)
        sys.exit(1)

    print_colored(f"Stopping instance '{name}'...", Colors.BLUE)
    subprocess.run(['docker', 'compose', '-f', str(compose_file), 'down'], check=True)

    registry['instances'][name]['status'] = 'stopped'
    save_registry(registry)
    print_colored(f"Instance '{name}' stopped.", Colors.GREEN)


def instance_destroy(args):
    """Destroy an instance (remove container, config, optionally database)"""
    registry = load_registry()
    name = args.name

    if name not in registry.get('instances', {}):
        print_colored(f"Error: Instance '{name}' not found.", Colors.RED)
        sys.exit(1)

    inst = registry['instances'][name]
    ctx = get_project_context()

    print_header(f"Destroying Instance: {name}")

    instance_dir = Path(f'instances/{name}')
    compose_file = instance_dir / 'docker-compose.yml'
    if compose_file.exists():
        print_colored("Stopping container...", Colors.BLUE)
        try:
            subprocess.run(['docker', 'compose', '-f', str(compose_file), 'down'], check=True, capture_output=True, text=True)
            print_colored("  Container stopped.", Colors.GREEN)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print_colored("  Warning: Could not stop container.", Colors.YELLOW)

    traefik_file = Path(f'traefik/instance-{name}.yml')
    if traefik_file.exists():
        traefik_file.unlink()
        print_colored(f"  Removed traefik/instance-{name}.yml", Colors.GREEN)

    if args.drop_db:
        db_name = inst.get('db_name', '')
        if db_name:
            pg_container = f"{ctx['domain_prefix']}-postgres16"
            print_colored(f"Dropping database: {db_name}...", Colors.BLUE)
            try:
                subprocess.run([
                    'docker', 'exec', pg_container, 'psql', '-U', 'postgres', '-c',
                    f"DROP DATABASE IF EXISTS {db_name};"
                ], check=True, capture_output=True, text=True)
                print_colored(f"  Database '{db_name}' dropped.", Colors.GREEN)
            except (subprocess.CalledProcessError, FileNotFoundError):
                print_colored(f"  Warning: Could not drop database '{db_name}'.", Colors.YELLOW)

    worktree_path = inst.get('worktree_path')
    if worktree_path:
        wt = Path(worktree_path)
        base_source = DEFAULT_SOURCE_PATHS.get(inst['type'], DEFAULT_SOURCE_PATHS['v4'])
        source_repo = str(Path(base_source).resolve())
        print_colored(f"Removing git worktree: {worktree_path}...", Colors.BLUE)
        try:
            subprocess.run(
                ['git', 'worktree', 'remove', '--force', str(wt.resolve())],
                cwd=source_repo, check=True, capture_output=True, text=True
            )
            print_colored(f"  Worktree removed.", Colors.GREEN)
        except (subprocess.CalledProcessError, FileNotFoundError):
            if wt.exists():
                try:
                    shutil.rmtree(wt)
                except PermissionError:
                    # Root-owned files from containers — remove via docker
                    subprocess.run(
                        ["docker", "run", "--rm", "-v", f"{wt.resolve()}:/cleanup", "alpine", "rm", "-rf", "/cleanup"],
                        capture_output=True, text=True,
                    )
                    if wt.exists():
                        wt.rmdir()
            print_colored(f"  Worktree directory removed (manual cleanup).", Colors.YELLOW)

    if instance_dir.exists():
        shutil.rmtree(instance_dir)
        print_colored(f"  Removed instances/{name}/", Colors.GREEN)

    del registry['instances'][name]
    save_registry(registry)

    print()
    print_colored(f"Instance '{name}' destroyed.", Colors.GREEN)
    print()


def instance_logs(args):
    """View logs for an instance"""
    registry = load_registry()
    name = args.name

    if name not in registry.get('instances', {}):
        print_colored(f"Error: Instance '{name}' not found.", Colors.RED)
        sys.exit(1)

    instance_dir = Path(f'instances/{name}')
    compose_file = instance_dir / 'docker-compose.yml'
    cmd = ['docker', 'compose', '-f', str(compose_file), 'logs']
    if args.follow:
        cmd.append('-f')
    if args.tail:
        cmd.extend(['--tail', args.tail])
    os.execvp(cmd[0], cmd)


def instance_shell(args):
    """Open shell in instance container"""
    registry = load_registry()
    name = args.name

    if name not in registry.get('instances', {}):
        print_colored(f"Error: Instance '{name}' not found.", Colors.RED)
        sys.exit(1)

    ctx = get_project_context()
    container = f"{ctx['domain_prefix']}-{name}"
    os.execvp('docker', ['docker', 'exec', '-it', container, '/bin/bash'])
