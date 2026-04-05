#!/usr/bin/env python3
"""
ssmd — Spawn, Scope, Migrate, Destroy
Dynamic isolated dev instance manager.

Usage: ./ssmd <domain>           Generate base configs
       ./ssmd instance create    Create a new instance
       ./ssmd --reset            Remove all generated files

Legacy alias: ./generate-config.py still works.
This script uses a Python virtual environment. Run ./setup-venv.sh first.
"""

import os
import sys
import argparse
from pathlib import Path

# Ensure we're using the venv if available
script_dir = Path(__file__).parent
venv_python = script_dir / '.venv' / 'bin' / 'python3'
if venv_python.exists() and sys.executable != str(venv_python):
    os.execv(str(venv_python), [str(venv_python)] + sys.argv)

try:
    from jinja2 import Environment, FileSystemLoader, Template
except ImportError:
    print("\n" + "=" * 50)
    print("Error: Jinja2 is not installed")
    print("=" * 50)
    print("\nPlease run the setup script first:")
    print("  ./setup-venv.sh")
    print("\nOr install manually:")
    print("  pip3 install -r requirements.txt")
    print()
    sys.exit(1)

from lib.config_generator import generate_configurations, handle_reset
from lib.instance_manager import (
    instance_create, instance_list, instance_start, instance_stop,
    instance_destroy, instance_logs, instance_shell,
)
from lib.database import instance_db_setup, instance_db_snapshot, instance_db_restore


def build_instance_parser():
    """Build argparse parser for instance subcommands"""
    parser = argparse.ArgumentParser(
        prog=f'{Path(sys.argv[0]).name} instance',
        description='Manage dynamic V4/selfhosted instances',
    )
    sub = parser.add_subparsers(dest='instance_command')

    # create
    p = sub.add_parser('create', help='Create a new instance')
    p.add_argument('--name', required=True, help='Instance name (e.g., v4-main, next, sh-client1)')
    p.add_argument('--type', required=True, choices=['v4', 'selfhosted'], help='Instance type')
    p.add_argument('--subdomain', help='Subdomain (default: same as name)')
    p.add_argument('--branch', help='Git branch — creates a worktree so this instance runs its own branch')
    p.add_argument('--source', help='Path to app source (default: apps/orangescrum-v4 or apps/durango-pg)')
    p.add_argument('--from-snapshot', help='Restore this database snapshot instead of starting empty')
    p.add_argument('--restricted', action='store_true', help='Mark instance as restricted (IP-whitelisted, hidden from MCP tools)')

    # list
    sub.add_parser('list', help='List all instances')

    # start
    p = sub.add_parser('start', help='Start a stopped instance')
    p.add_argument('--name', required=True, help='Instance name')

    # stop
    p = sub.add_parser('stop', help='Stop a running instance')
    p.add_argument('--name', required=True, help='Instance name')

    # destroy
    p = sub.add_parser('destroy', help='Destroy an instance')
    p.add_argument('--name', required=True, help='Instance name')
    p.add_argument('--drop-db', action='store_true', help='Also drop the PostgreSQL database')

    # db-setup
    p = sub.add_parser('db-setup', help='Run migrations and seeds for an instance')
    p.add_argument('--name', required=True, help='Instance name')
    p.add_argument('--skip-seed', action='store_true', help='Skip database seeding')

    # db-snapshot
    p = sub.add_parser('db-snapshot', help='Take a pg_dump snapshot of an instance database')
    p.add_argument('--name', required=True, help='Instance name')
    p.add_argument('--output', help='Output file path (default: snapshots/<db_name>_<timestamp>.sql.gz)')

    # db-restore
    p = sub.add_parser('db-restore', help='Restore a database snapshot into an instance')
    p.add_argument('--name', required=True, help='Instance name')
    p.add_argument('--snapshot', required=True, help='Snapshot file path (.sql.gz)')
    p.add_argument('--drop-existing', action='store_true', help='Drop and recreate the database before restore')

    # logs
    p = sub.add_parser('logs', help='View instance logs')
    p.add_argument('--name', required=True, help='Instance name')
    p.add_argument('-f', '--follow', action='store_true', help='Follow log output')
    p.add_argument('--tail', default='100', help='Number of lines to show (default: 100)')

    # shell
    p = sub.add_parser('shell', help='Open shell in instance container')
    p.add_argument('--name', required=True, help='Instance name')

    return parser


def main():
    # Change to script directory first
    script_dir = Path(__file__).parent
    os.chdir(script_dir)

    # Route "instance" subcommand to its own parser
    if len(sys.argv) > 1 and sys.argv[1] == 'instance':
        inst_parser = build_instance_parser()
        args = inst_parser.parse_args(sys.argv[2:])

        dispatch = {
            'create': instance_create,
            'list': instance_list,
            'start': instance_start,
            'stop': instance_stop,
            'destroy': instance_destroy,
            'db-setup': instance_db_setup,
            'db-snapshot': instance_db_snapshot,
            'db-restore': instance_db_restore,
            'logs': instance_logs,
            'shell': instance_shell,
        }
        handler = dispatch.get(args.instance_command)
        if handler:
            handler(args)
        else:
            inst_parser.print_help()
        sys.exit(0)

    # Config generation parser
    from lib.output import BANNER
    banner = BANNER
    parser = argparse.ArgumentParser(
        description=banner,
        epilog='Examples:\n'
               '  %(prog)s user196.online                Generate base configs (HTTPS enabled)\n'
               '  %(prog)s user196.online --no-https     Generate without HTTPS\n'
               '  %(prog)s --reset                       Remove all generated files\n'
               '  %(prog)s instance create --name v4-main --type v4 --subdomain v4\n'
               '  %(prog)s instance list\n'
               '  %(prog)s instance destroy --name v4-main --drop-db\n',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('domain', nargs='?', default=None, help='Base domain (e.g., user196.online)')
    parser.add_argument('--reset', action='store_true', help='Backup and remove generated configuration files')
    parser.add_argument('--dry-run', action='store_true', help='Generate .new files for review without applying')
    parser.add_argument('-y', '--yes', action='store_true', help='Assume yes for prompts')
    parser.add_argument('-i', '--interactive', action='store_true', help='Interactive mode: prompt for service selection')
    parser.add_argument('--no-https', action='store_true', help='Disable HTTPS/TLS (default: HTTPS enabled)')

    args = parser.parse_args()

    if args.reset:
        handle_reset()
        sys.exit(0)

    if not args.domain:
        parser.print_help()
        sys.exit(2)

    generate_configurations(args.domain, args.dry_run, args.interactive, not args.no_https)


if __name__ == '__main__':
    main()
