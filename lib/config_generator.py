"""Configuration generator — template rendering, backups, domain changes, reset."""

import hashlib
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from .output import Colors, print_colored, print_header, print_banner
from .registry import (
    DEFAULT_SOURCE_PATHS,
    detect_current_domain, load_registry, reset_registry,
)


def validate_domain(domain):
    pattern = r'^[a-z0-9.-]+\.[a-z]{2,}$'
    return re.match(pattern, domain) is not None


def backup_files(backup_dir):
    files_to_backup = [
        '.env',
        'docker-compose.yml',
        'docker-compose.override.yml',
        'traefik/dynamic.yml',
        'config/durango-apache.conf',
        'config/orangescrum-apache.conf',
        'php-trust-certs.sh',
        'generate-certs.sh',
        'build-images.sh',
        'Dockerfile.base',
        'Dockerfile.php7.2',
        'Dockerfile.php8.3',
    ]

    backup_path = Path(backup_dir)
    backup_path.mkdir(parents=True, exist_ok=True)

    backed_up = []
    for file_path in files_to_backup:
        if Path(file_path).exists():
            dest = backup_path / Path(file_path).name
            shutil.copy2(file_path, dest)
            backed_up.append(file_path)

    return backed_up


def backup_old_domain_files(old_domain, backup_dir):
    old_files = list(Path('launchers').glob(f'*{old_domain}*'))
    old_files.extend(Path('certs').glob(f'{old_domain}.*'))

    if not old_files:
        return

    backup_path = Path(backup_dir)
    print_colored(f"\nBacking up old domain files ({old_domain})...", Colors.YELLOW)
    for file in old_files:
        if file.exists():
            dest = backup_path / file.name
            shutil.copy2(file, dest)
            file.unlink()
            print(f"  Archived: {file.name}")


def generate_configurations(domain, dry_run=False, interactive=False, enable_https=False):
    """Generate all configuration files from templates"""

    if not validate_domain(domain):
        print_colored("Error: Invalid domain format. Please use a valid domain (e.g., ossiba.local, example.com)", Colors.RED)
        sys.exit(1)

    current_domain = detect_current_domain()
    if current_domain and current_domain != domain:
        print_colored(f"\n⚠ Warning: Domain change detected!", Colors.YELLOW)
        print(f"  Current: {current_domain}")
        print(f"  New:     {domain}")
        print("\nThis will:")
        print(f"  - Backup old configs to backups/")
        print(f"  - Remove old domain files ({current_domain})")
        print(f"  - Generate new configs for {domain}")

        response = input(f"\nContinue? [y/N]: ").strip().lower()
        if response not in ['y', 'yes']:
            print_colored("Aborted.", Colors.RED)
            sys.exit(0)

    # Get LAN IP
    try:
        result = subprocess.run(['hostname', '-I'], capture_output=True, text=True, check=True)
        lan_ips = result.stdout.strip().split()
        lan_ip = lan_ips[0] if lan_ips else '192.168.1.100'
    except Exception:
        lan_ip = '192.168.1.100'

    # Unique port offset from domain hash
    domain_hash = int(hashlib.md5(domain.encode()).hexdigest()[:4], 16)
    port_offset = (domain_hash % 100) * 100

    domain_prefix = domain.replace('.', '-').replace('_', '-')

    # Base ports
    base_traefik_http = 8800 + port_offset
    base_traefik_https = 8800 + port_offset + 43
    base_traefik_dashboard = 8000 + port_offset
    base_mysql = 3300 + port_offset
    base_postgres = 5400 + port_offset
    base_redis = 6300 + port_offset
    base_minio_api = 9000 + port_offset
    base_minio_console = 9000 + port_offset + 1
    base_memcached_durango = 11200 + port_offset
    base_memcached_orangescrum = 11200 + port_offset + 1

    print_banner()
    print(f"Domain: {domain}")
    print(f"LAN IP: {lan_ip}")
    print(f"HTTPS: {'Enabled' if enable_https else 'Disabled (use --no-https to disable)'}")
    print(f"Mode: {'Dry run (review only)' if dry_run else 'Apply configurations'}\n")

    # Create backup
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = f"backups/{timestamp}"

    print_colored("Backing up existing configurations...", Colors.YELLOW)
    backed_up = backup_files(backup_dir)
    if backed_up:
        print_colored(f"✓ Backups saved to {backup_dir}", Colors.GREEN)
        for file in backed_up:
            print(f"  - {file}")

    if current_domain and current_domain != domain:
        backup_old_domain_files(current_domain, backup_dir)

    print()

    # Setup Jinja2
    templates_dir = Path('templates')
    if not templates_dir.exists():
        print_colored(f"Error: Templates directory not found: {templates_dir}", Colors.RED)
        sys.exit(1)

    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True
    )

    # Generate security salt
    try:
        import secrets
        security_salt = hashlib.sha256(secrets.token_bytes(64)).hexdigest()
    except Exception:
        try:
            raw_hex = subprocess.run(['openssl', 'rand', '-hex', '64'], capture_output=True, text=True, check=True).stdout.strip()
            raw_bytes = bytes.fromhex(raw_hex)
            security_salt = hashlib.sha256(raw_bytes).hexdigest()
        except Exception:
            import uuid
            security_salt = hashlib.sha256(uuid.uuid4().bytes + uuid.uuid4().bytes).hexdigest()

    context = {
        'domain': domain,
        'domain_prefix': domain_prefix,
        'public_domain': domain.replace('.local', '.com'),
        'generation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'generated_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'builder_uid': os.getuid(),
        'lan_ip': lan_ip,
        'security_salt': security_salt,
        'port_offset': port_offset,
        'traefik_http_port': base_traefik_http,
        'traefik_https_port': base_traefik_https,
        'traefik_dashboard_port': base_traefik_dashboard,
        'mysql_port': base_mysql,
        'postgres_port': base_postgres,
        'redis_port': base_redis,
        'minio_api_port': base_minio_api,
        'minio_console_port': base_minio_console,
        'memcached_durango_port': base_memcached_durango,
        'memcached_orangescrum_port': base_memcached_orangescrum,
        'enable_https': enable_https,
        'node_version': '20',
        'project_root': str(Path.cwd()),
    }

    # Default services selection
    if interactive and not dry_run:
        default_services = {
            'orangescrum': False,
            'postgres16': False,
            'mysql': False,
            'redis_durango': False,
            'memcached_orangescrum': False,
            'memcached_durango': False,
            'minio': False,
            'mailhog': False,
            'browser': True,
        }
    else:
        default_services = {
            'orangescrum': True,
            'postgres16': True,
            'mysql': True,
            'redis_durango': True,
            'memcached_orangescrum': True,
            'memcached_durango': False,
            'minio': False,
            'mailhog': True,
            'browser': True,
        }

    context['services'] = default_services

    service_dependencies = {
        'orangescrum': ['mysql', 'memcached_orangescrum'],
        'minio': [],
        'mailhog': [],
        'browser': [],
        'postgres16': [],
        'mysql': [],
        'redis_durango': [],
        'memcached_orangescrum': [],
        'memcached_durango': [],
    }

    def resolve_dependencies(services, dependencies_map):
        changed = True
        while changed:
            changed = False
            for service, deps in dependencies_map.items():
                if services.get(service, False):
                    for dep in deps:
                        if not services.get(dep, False):
                            services[dep] = True
                            changed = True
        return services

    # Interactive selection
    if interactive and not dry_run:
        print_colored('\n' + '='*60, Colors.BLUE)
        print_colored('Interactive Service Configuration', Colors.BLUE)
        print_colored('='*60, Colors.BLUE)

        print_colored('\nStep 1: Base Applications', Colors.BLUE)
        print("V4/selfhosted apps are managed as dynamic instances (see: ./ssmd instance create)")
        print()

        try:
            resp_v2 = input("  Run OrangeScrum V2 (legacy version)? [Y/n]: ").strip().lower()
            context['services']['orangescrum'] = resp_v2 in ['', 'y', 'yes']
        except (EOFError, KeyboardInterrupt):
            pass

        print()
        print_colored('Step 2: Cache Engine for V4/Selfhosted Instances', Colors.BLUE)
        print("Dynamic instances need a cache engine (shared):")
        print("  - Redis: Recommended (better performance, supports distributed caching)")
        print("  - Memcached: Simple alternative (single-node only)")
        print()

        try:
            cache_choice = input("  Use Redis for instances? [Y/n]: ").strip().lower()
            if cache_choice in ['', 'y', 'yes']:
                context['services']['redis_durango'] = True
                context['services']['memcached_durango'] = False
            else:
                context['services']['redis_durango'] = False
                context['services']['memcached_durango'] = True
        except (EOFError, KeyboardInterrupt):
            context['services']['redis_durango'] = True

        print()
        print_colored('Step 3: Additional Services', Colors.BLUE)

        try:
            resp_mail = input("  Enable MailHog (email testing)? [Y/n]: ").strip().lower()
            context['services']['mailhog'] = resp_mail in ['', 'y', 'yes']

            resp_minio = input("  Enable MinIO (S3-compatible storage)? [y/N]: ").strip().lower()
            context['services']['minio'] = resp_minio in ['y', 'yes']
        except (EOFError, KeyboardInterrupt):
            context['services']['mailhog'] = True

    context['services'] = resolve_dependencies(context['services'], service_dependencies)

    if interactive and not dry_run:
        print()
        print_colored('='*60, Colors.BLUE)
        print_colored('Final Service Configuration', Colors.BLUE)
        print_colored('='*60, Colors.BLUE)

        enabled = [k.replace('_', ' ').title() for k, v in context['services'].items() if v]
        disabled = [k.replace('_', ' ').title() for k, v in context['services'].items() if not v]

        if enabled:
            print_colored('✓ Enabled Services:', Colors.GREEN)
            for svc in enabled:
                print(f"  • {svc}")
        else:
            print_colored('⚠ No services selected', Colors.YELLOW)

        if disabled:
            print_colored('✗ Disabled Services:', Colors.YELLOW)
            for svc in disabled[:5]:
                print(f"  • {svc}")
            if len(disabled) > 5:
                print(f"  ... and {len(disabled)-5} more")

        print()

    # Derive cache_engine
    if context['services'].get('redis_durango'):
        context['cache_engine'] = 'redis'
    elif context['services'].get('memcached_durango'):
        context['cache_engine'] = 'memcached'
    else:
        context['cache_engine'] = 'file'

    configs = [
        {'template': '.env.j2', 'output': '.env', 'label': '.env'},
        {'template': 'shared.env.j2', 'output': 'instances/shared.env', 'label': 'instances/shared.env'},
        {'template': 'Dockerfile.base.j2', 'output': 'Dockerfile.base', 'label': 'Dockerfile.base'},
        {'template': 'Dockerfile.php7.2.j2', 'output': 'Dockerfile.php7.2', 'label': 'Dockerfile.php7.2'},
        {'template': 'Dockerfile.php8.3.j2', 'output': 'Dockerfile.php8.3', 'label': 'Dockerfile.php8.3'},
        {'template': 'build-images.sh.j2', 'output': 'build-images.sh', 'label': 'build-images.sh'},
        {'template': 'docker-compose.yml.j2', 'output': 'docker-compose.yml', 'label': 'docker-compose.yml'},
        {'template': 'docker-compose.override.yml.j2', 'output': 'docker-compose.override.yml', 'label': 'docker-compose.override.yml'},
        {'template': 'traefik-dynamic.yml.j2', 'output': 'traefik/dynamic.yml', 'label': 'traefik/dynamic.yml'},
        {'template': 'durango-apache.conf.j2', 'output': 'config/durango-apache.conf', 'label': 'config/durango-apache.conf'},
        {'template': 'orangescrum-apache.conf.j2', 'output': 'config/orangescrum-apache.conf', 'label': 'config/orangescrum-apache.conf'},
        {'template': 'php-trust-certs.sh.j2', 'output': 'php-trust-certs.sh', 'label': 'php-trust-certs.sh'},
        {'template': 'generate-certs.sh.j2', 'output': 'generate-certs.sh', 'label': 'generate-certs.sh'},
        {'template': 'os-v2.env.j2', 'output': 'os-v2/.env', 'label': 'os-v2/.env'},
        {'template': 'dnsmasq.conf.j2', 'output': 'config/dnsmasq.conf', 'label': 'config/dnsmasq.conf'},
        {'template': 'browser-trust-certs.sh.j2', 'output': 'entrypoints/browser-trust-certs.sh', 'label': 'entrypoints/browser-trust-certs.sh'},
        {'template': 'instance-apache.conf.j2', 'output': 'config/instance-apache.conf', 'label': 'config/instance-apache.conf'},
    ]

    if dry_run:
        for config in configs:
            config['output'] = config['output'] + '.new'

    generated_files = []
    for config in configs:
        try:
            print_colored(f"Generating {config['label']}...", Colors.BLUE)

            template = env.get_template(config['template'])

            render_context = context.copy()
            if 'extra_context' in config:
                render_context.update(config['extra_context'])

            output_content = template.render(render_context)

            output_path = Path(config['output'])
            output_path.parent.mkdir(parents=True, exist_ok=True)

            output_path.write_text(output_content)

            if output_path.suffix == '.sh' or (output_path.suffix == '.new' and '.sh' in config['output']):
                output_path.chmod(0o755)

            generated_files.append(config['output'])
            print_colored(f"✓ Generated {config['output']}", Colors.GREEN)

        except Exception as e:
            print_colored(f"✗ Error generating {config['label']}: {e}", Colors.RED)
            sys.exit(1)

    def safe_copy_env(src_path, target_path):
        src = Path(src_path)
        tgt = Path(target_path)
        if not src.exists():
            return False
        if tgt.exists():
            bkp = Path(backup_dir) / f"{tgt.name}.bak"
            shutil.copy2(tgt, bkp)
        tgt.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, tgt)
        return True

    if not dry_run:
        for app_logs in ['apps/orangescrum-v4/logs', 'apps/orangescrum/logs', 'apps/durango-pg/logs', '.composer-cache', 'snapshots']:
            try:
                p = Path(app_logs)
                p.mkdir(parents=True, exist_ok=True)
                print_colored(f"✓ Ensured logs dir: {app_logs}", Colors.GREEN)
            except Exception:
                print_colored(f"✗ Could not create logs dir: {app_logs}", Colors.YELLOW)

    # Summary
    print_header("Configuration Generation Complete!")
    print("Generated files:")
    for file in generated_files:
        print(f"  - {file}")
    print(f"\nBackups saved to: {backup_dir}\n")

    if dry_run:
        print_colored("Review the generated files (*.new) before applying.", Colors.YELLOW)
        print(f"\nTo apply the configurations, run:")
        print(f"  {sys.argv[0]} {domain}")
        print("\nOr manually:")
        for config in configs:
            src = config['output']
            dest = src.replace('.new', '')
            print(f"  mv {src} {dest}")
    else:
        print_colored("✓ Configurations applied!", Colors.GREEN)
        print_next_steps(domain, context['services'], enable_https)

    print()


def print_next_steps(domain, services, enable_https=True):
    protocol = 'https' if enable_https else 'http'
    access_points = [
        {"name": "V2 (Orangescrum)", "url": f"{protocol}://app.{domain}"},
        {"name": "MailHog", "url": f"{protocol}://mail.{domain}"},
        {"name": "Storage (MinIO)", "url": f"{protocol}://storage.{domain}"},
        {"name": "Storage Console", "url": f"{protocol}://console.{domain}"},
        {"name": "Traefik Dashboard", "url": f"{protocol}://traefik.{domain}"},
        {"name": "Controller", "url": f"{protocol}://control.{domain}"},
        {"name": "VNC Browser", "url": "http://localhost:3000"},
    ]

    templates_dir = Path('templates')
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        trim_blocks=True,
        lstrip_blocks=True
    )

    template = env.get_template('next-steps.txt.j2')
    output = template.render(domain=domain, access_points=access_points, services=services)
    print(output)


def handle_reset():
    """Handle reset operation"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = f"backups/{timestamp}"
    print_header("Reset: backing up and removing generated files")
    backed_up = backup_files(backup_dir)
    if backed_up:
        print_colored(f"Backed up {len(backed_up)} files to {backup_dir}", Colors.GREEN)
    else:
        print_colored("No generated config files found to backup.", Colors.YELLOW)

    # Stop base services
    compose_file = Path('docker-compose.yml')
    if compose_file.exists():
        print_colored("Stopping base services and removing volumes...", Colors.BLUE)
        try:
            subprocess.run(
                ['docker', 'compose', 'down', '-v'],
                capture_output=True, text=True
            )
            print_colored("  Base services stopped, volumes removed.", Colors.GREEN)
        except Exception:
            print_colored("  Warning: Could not stop base services.", Colors.YELLOW)

    files_to_remove = [
        '.env',
        'docker-compose.yml',
        'docker-compose.override.yml',
        'traefik/dynamic.yml',
        'config/durango-apache.conf',
        'config/orangescrum-apache.conf',
        'config/instance-apache.conf',
        'config/dnsmasq.conf',
        'php-trust-certs.sh',
        'generate-certs.sh',
        'build-images.sh',
        'entrypoints/browser-trust-certs.sh',
        'Dockerfile.base',
        'Dockerfile.php7.2',
        'Dockerfile.php8.3',
        'os-v2/.env',
    ]

    for f in files_to_remove:
        p = Path(f)
        try:
            if p.exists():
                if p.is_dir():
                    shutil.rmtree(p)
                else:
                    p.unlink()
                print_colored(f"Removed: {f}", Colors.GREEN)
        except Exception as e:
            print_colored(f"Could not remove {f}: {e}", Colors.YELLOW)

    # Stop and remove all instances
    registry = load_registry()
    for inst_name, inst in registry.get('instances', {}).items():
        inst_dir = Path(f'instances/{inst_name}')
        inst_compose = inst_dir / 'docker-compose.yml'
        if inst_compose.exists():
            print_colored(f"Stopping instance '{inst_name}'...", Colors.BLUE)
            try:
                subprocess.run(
                    ['docker', 'compose', '-f', str(inst_compose), 'down'],
                    capture_output=True, text=True
                )
            except Exception:
                pass

        worktree_path = inst.get('worktree_path')
        if worktree_path and Path(worktree_path).exists():
            base_source = DEFAULT_SOURCE_PATHS.get(inst['type'], DEFAULT_SOURCE_PATHS['v4'])
            try:
                subprocess.run(
                    ['git', 'worktree', 'remove', '--force', str(Path(worktree_path).resolve())],
                    cwd=str(Path(base_source).resolve()),
                    capture_output=True, text=True
                )
            except Exception:
                pass
            if Path(worktree_path).exists():
                shutil.rmtree(worktree_path, ignore_errors=True)
            print_colored(f"  Removed worktree: {worktree_path}", Colors.GREEN)

        if inst_dir.exists():
            shutil.rmtree(inst_dir)
            print_colored(f"  Removed instances/{inst_name}/", Colors.GREEN)

    # Reset registry
    reset_registry()
    print_colored("Instance registry reset.", Colors.GREEN)

    # Remove generated instance traefik configs
    try:
        traefik_dir = Path('traefik')
        if traefik_dir.exists():
            for lf in traefik_dir.glob('instance-*.yml'):
                try:
                    lf.unlink()
                    print_colored(f"Removed: {lf}", Colors.GREEN)
                except Exception as e:
                    print_colored(f"Could not remove {lf}: {e}", Colors.YELLOW)
    except Exception:
        pass

    # Remove worktrees directory
    worktrees_dir = Path('apps') / 'worktrees'
    if worktrees_dir.exists():
        shutil.rmtree(worktrees_dir, ignore_errors=True)
        print_colored(f"Removed: apps/worktrees/", Colors.GREEN)

    # Remove any generated .new files
    try:
        new_files = list(Path('.').rglob('*.new'))
        for nf in new_files:
            if 'backups' in nf.parts:
                continue
            try:
                nf.unlink()
                print_colored(f"Removed: {nf}", Colors.GREEN)
            except Exception as e:
                print_colored(f"Could not remove {nf}: {e}", Colors.YELLOW)
    except Exception:
        pass

    print_colored("Reset complete.", Colors.BLUE)
