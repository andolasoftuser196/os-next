"""Database operations — setup (migrations/seeds), snapshot, restore."""

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from .output import Colors, print_colored, print_header
from .registry import load_registry, get_project_context


def instance_db_setup(args):
    """Run database migrations and seeds for an instance"""
    registry = load_registry()
    name = args.name

    if name not in registry.get('instances', {}):
        print_colored(f"Error: Instance '{name}' not found.", Colors.RED)
        sys.exit(1)

    ctx = get_project_context()
    container = f"{ctx['domain_prefix']}-{name}"

    print_header(f"Database Setup: {name}")

    print_colored("Running migrations...", Colors.BLUE)
    try:
        result = subprocess.run([
            'docker', 'exec', container, 'php', 'bin/cake.php', 'migrations', 'migrate'
        ], check=True, capture_output=True, text=True)
        print(result.stdout)
        print_colored("  Migrations complete.", Colors.GREEN)
    except subprocess.CalledProcessError as e:
        print_colored(f"  Migration failed: {e.stderr}", Colors.RED)
        return

    if not args.skip_seed:
        print_colored("Running seeders...", Colors.BLUE)
        try:
            result = subprocess.run([
                'docker', 'exec', container, 'php', 'bin/cake.php', 'migrations', 'seed'
            ], check=True, capture_output=True, text=True)
            print(result.stdout)
            print_colored("  Seeders complete.", Colors.GREEN)
        except subprocess.CalledProcessError as e:
            print_colored(f"  Seeder warning: {e.stderr}", Colors.YELLOW)

    print()
    print_colored(f"Database setup complete for '{name}'.", Colors.GREEN)
    print()


def instance_db_snapshot(args):
    """Create a pg_dump snapshot of an instance's database"""
    registry = load_registry()
    name = args.name

    if name not in registry.get('instances', {}):
        print_colored(f"Error: Instance '{name}' not found.", Colors.RED)
        sys.exit(1)

    inst = registry['instances'][name]
    ctx = get_project_context()
    pg_container = f"{ctx['domain_prefix']}-postgres16"
    db_name = inst['db_name']
    db_user = inst.get('db_user', 'postgres')

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = args.output or f"snapshots/{db_name}_{timestamp}.sql.gz"
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)

    print_header(f"Database Snapshot: {name}")
    print(f"Database: {db_name}")
    print(f"Output: {output_file}")

    try:
        dump_cmd = subprocess.Popen(
            ['docker', 'exec', pg_container, 'pg_dump', '-U', db_user, '--no-owner', '--no-acl', db_name],
            stdout=subprocess.PIPE
        )
        with open(output_file, 'wb') as f:
            gzip_cmd = subprocess.Popen(['gzip'], stdin=dump_cmd.stdout, stdout=f)
            dump_cmd.stdout.close()
            gzip_cmd.communicate()

        if dump_cmd.wait() != 0:
            print_colored("Error: pg_dump failed.", Colors.RED)
            sys.exit(1)

        file_size = Path(output_file).stat().st_size
        print_colored(f"Snapshot saved: {output_file} ({file_size // 1024} KB)", Colors.GREEN)
    except Exception as e:
        print_colored(f"Error creating snapshot: {e}", Colors.RED)
        sys.exit(1)


def instance_db_restore(args):
    """Restore a pg_dump snapshot into an instance's database"""
    registry = load_registry()
    name = args.name
    snapshot = args.snapshot

    if name not in registry.get('instances', {}):
        print_colored(f"Error: Instance '{name}' not found.", Colors.RED)
        sys.exit(1)

    if not Path(snapshot).exists():
        print_colored(f"Error: Snapshot file not found: {snapshot}", Colors.RED)
        sys.exit(1)

    inst = registry['instances'][name]
    ctx = get_project_context()
    pg_container = f"{ctx['domain_prefix']}-postgres16"
    db_name = inst['db_name']
    db_user = inst.get('db_user', 'postgres')

    print_header(f"Database Restore: {name}")
    print(f"Database: {db_name}")
    print(f"Snapshot: {snapshot}")

    if args.drop_existing:
        print_colored("Dropping existing database...", Colors.BLUE)
        subprocess.run([
            'docker', 'exec', pg_container, 'psql', '-U', 'postgres', '-c',
            f"DROP DATABASE IF EXISTS {db_name};"
        ], capture_output=True, text=True)
        subprocess.run([
            'docker', 'exec', pg_container, 'psql', '-U', 'postgres', '-c',
            f"CREATE DATABASE {db_name} OWNER {db_user};"
        ], check=True, capture_output=True, text=True)
        subprocess.run([
            'docker', 'exec', pg_container, 'psql', '-U', 'postgres', '-c',
            f"GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {db_user};"
        ], check=True, capture_output=True, text=True)
        print_colored("  Database recreated.", Colors.GREEN)

    try:
        gunzip = subprocess.Popen(['gunzip', '-c', snapshot], stdout=subprocess.PIPE)
        psql = subprocess.Popen(
            ['docker', 'exec', '-i', pg_container, 'psql', '-U', db_user, '-d', db_name],
            stdin=gunzip.stdout, capture_output=True, text=True
        )
        gunzip.stdout.close()
        stdout, stderr = psql.communicate()

        if psql.returncode != 0:
            print_colored(f"Warning: psql returned {psql.returncode}", Colors.YELLOW)
            if stderr:
                print(stderr[:500])
        else:
            print_colored("Database restored successfully.", Colors.GREEN)
    except Exception as e:
        print_colored(f"Error restoring snapshot: {e}", Colors.RED)
        sys.exit(1)
