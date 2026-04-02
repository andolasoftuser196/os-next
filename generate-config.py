#!/usr/bin/env python3
"""
Configuration Generator for Multi-Domain Docker Setup
Usage: ./generate-config.py <domain> [--apply]

This script uses a Python virtual environment. Run ./setup-venv.sh first.
"""

import os
import sys
import shutil
import argparse
from pathlib import Path
from datetime import datetime

# Ensure we're using the venv if available
script_dir = Path(__file__).parent
venv_python = script_dir / '.venv' / 'bin' / 'python3'
if venv_python.exists() and sys.executable != str(venv_python):
    # Re-execute with venv python
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

# ANSI color codes
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color


def print_colored(text, color):
    """Print colored text"""
    print(f"{color}{text}{Colors.NC}")


def print_header(text):
    """Print a formatted header"""
    print("\n" + "=" * 50)
    print_colored(text, Colors.BLUE)
    print("=" * 50 + "\n")


def validate_domain(domain):
    """Validate domain format"""
    import re
    pattern = r'^[a-z0-9.-]+\.[a-z]{2,}$'
    return re.match(pattern, domain) is not None


def backup_files(backup_dir):
    """Backup existing configuration files"""
    files_to_backup = [
        '.env',
        'docker-compose.yml',
        'docker-compose.override.yml',
        'MULTI_TENANT.md',
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


def detect_current_domain():
    """Detect current domain from existing docker-compose.yml"""
    compose_file = Path('docker-compose.yml')
    if not compose_file.exists():
        return None
    
    try:
        import re
        content = compose_file.read_text()
        # Look for domain in comments or traefik labels
        match = re.search(r'# Domain: ([a-z0-9.-]+\.[a-z]{2,})', content)
        if match:
            return match.group(1)
        match = re.search(r'Host\(`v4\.([a-z0-9.-]+\.[a-z]{2,})`\)', content)
        if match:
            return match.group(1)
    except:
        pass
    return None


def backup_old_domain_files(old_domain, backup_dir):
    """Backup and remove old domain-specific files"""
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
    
    # Validate domain
    if not validate_domain(domain):
        print_colored("Error: Invalid domain format. Please use a valid domain (e.g., ossiba.local, example.com)", Colors.RED)
        sys.exit(1)
    
    # Check if domain is changing
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
    import subprocess
    try:
        result = subprocess.run(['hostname', '-I'], capture_output=True, text=True, check=True)
        lan_ips = result.stdout.strip().split()
        lan_ip = lan_ips[0] if lan_ips else '192.168.1.100'
    except:
        lan_ip = '192.168.1.100'
    
    # Generate unique port offset based on domain hash (for multi-tenant setups)
    # This ensures each domain gets its own port range automatically
    import hashlib
    domain_hash = int(hashlib.md5(domain.encode()).hexdigest()[:4], 16)
    port_offset = (domain_hash % 100) * 100  # Generates offsets like 0, 100, 200, ... 9900
    
    # Create a short prefix for container names from domain
    # Convert domain to safe container name prefix (remove dots, keep alphanumeric)
    domain_prefix = domain.replace('.', '-').replace('_', '-')
    
    # Base ports (these will be offset for each domain)
    base_traefik_http = 8800 + port_offset
    base_traefik_https = 8800 + port_offset + 43  # Keep the 43 offset
    base_traefik_dashboard = 8000 + port_offset
    base_mysql = 3300 + port_offset
    base_postgres = 5400 + port_offset
    base_redis = 6300 + port_offset
    base_minio_api = 9000 + port_offset
    base_minio_console = 9000 + port_offset + 1
    base_memcached_durango = 11200 + port_offset
    base_memcached_orangescrum = 11200 + port_offset + 1
    
    print_header("OrangeScrum Docker Configuration Generator")
    print(f"Domain: {domain}")
    print(f"LAN IP: {lan_ip}")
    print(f"HTTPS: {'Enabled' if enable_https else 'Disabled (use --no-https to disable)'}")
    print(f"Mode: {'Dry run (review only)' if dry_run else 'Apply configurations'}\n")
    
    # # Ask about docker-compose.override.yml
    # generate_override = False
    # if not dry_run:
    #     try:
    #         response = input("Generate docker-compose.override.yml for port mappings? (y/N): ").strip().lower()
    #         generate_override = response in ['y', 'yes']
    #     except (EOFError, KeyboardInterrupt):
    #         print()  # New line after interrupted input
    
    # Create backup
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = f"backups/{timestamp}"
    
    print_colored("Backing up existing configurations...", Colors.YELLOW)
    backed_up = backup_files(backup_dir)
    if backed_up:
        print_colored(f"✓ Backups saved to {backup_dir}", Colors.GREEN)
        for file in backed_up:
            print(f"  - {file}")
    
    # Backup old domain files if domain changed
    if current_domain and current_domain != domain:
        backup_old_domain_files(current_domain, backup_dir)
    
    print()
    
    # Setup Jinja2 environment
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
    
    # Generate security salt compatible with CakePHP 4
    # CakePHP uses: hash('sha256', Security::randomBytes(64)) -> 64-char hex string
    import hashlib
    try:
        import secrets
        security_salt = hashlib.sha256(secrets.token_bytes(64)).hexdigest()
    except Exception:
        # Fallback to openssl if secrets isn't available. Generate 64 random bytes as hex
        try:
            raw_hex = subprocess.run(['openssl', 'rand', '-hex', '64'], capture_output=True, text=True, check=True).stdout.strip()
            raw_bytes = bytes.fromhex(raw_hex)
            security_salt = hashlib.sha256(raw_bytes).hexdigest()
        except Exception:
            # Last-resort fallback: hash of two UUID4 values
            import uuid
            security_salt = hashlib.sha256(uuid.uuid4().bytes + uuid.uuid4().bytes).hexdigest()
    
    # Template context
    context = {
        'domain': domain,
        'domain_prefix': domain_prefix,
        'public_domain': domain.replace('.local', '.com'),  # For LAN access (ossiba.local -> ossiba.com)
        'generation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'generated_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'builder_uid': '${BUILDER_UID:-1000}',
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
        'node_version': '20'
    }
    # Default services selection
    # If interactive mode: start with None (ask user)
    # If regular mode: enable common services by default
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
        # Default: enable common services (V4/selfhosted are dynamic instances)
        default_services = {
            'orangescrum': True,
            'postgres16': True,
            'mysql': True,
            'redis_durango': True,
            'memcached_orangescrum': True,
            'memcached_durango': False,  # Use redis instead
            'minio': False,
            'mailhog': True,
            'browser': True,
        }
    
    context['services'] = default_services
    
    # Service dependencies map - if a service is enabled, its dependencies must also be enabled
    # Note: For cache/queue, pick ONE: either redis_durango OR memcached_durango (redis takes precedence)
    # V4/selfhosted apps are dynamic instances managed via 'instance' subcommand
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
    
    # Function to resolve dependencies
    def resolve_dependencies(services, dependencies_map):
        """Ensure all required dependencies are enabled"""
        changed = True
        while changed:
            changed = False
            for service, deps in dependencies_map.items():
                if services.get(service, False):  # If service is enabled
                    for dep in deps:
                        if not services.get(dep, False):  # And dependency is disabled
                            services[dep] = True  # Enable it
                            changed = True
        return services

    # Interactive selection of services
    if interactive and not dry_run:
        print_colored('\n' + '='*60, Colors.BLUE)
        print_colored('Interactive Service Configuration', Colors.BLUE)
        print_colored('='*60, Colors.BLUE)
        
        # Step 1: Select base services
        print_colored('\nStep 1: Base Applications', Colors.BLUE)
        print("V4/selfhosted apps are managed as dynamic instances (see: ./generate-config.py instance create)")
        print()

        try:
            resp_v2 = input("  Run OrangeScrum V2 (legacy version)? [Y/n]: ").strip().lower()
            context['services']['orangescrum'] = resp_v2 in ['', 'y', 'yes']
        except (EOFError, KeyboardInterrupt):
            pass

        # Step 2: Configure cache/queue for instances
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

        # Step 3: Additional services
        print()
        print_colored('Step 3: Additional Services', Colors.BLUE)

        try:
            resp_mail = input("  Enable MailHog (email testing)? [Y/n]: ").strip().lower()
            context['services']['mailhog'] = resp_mail in ['', 'y', 'yes']

            resp_minio = input("  Enable MinIO (S3-compatible storage)? [y/N]: ").strip().lower()
            context['services']['minio'] = resp_minio in ['y', 'yes']
        except (EOFError, KeyboardInterrupt):
            context['services']['mailhog'] = True
        
    # Always resolve dependencies - enable any required dependencies
    context['services'] = resolve_dependencies(context['services'], service_dependencies)
    
    # Show final service configuration in interactive mode
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
            for svc in disabled[:5]:  # Show first 5
                print(f"  • {svc}")
            if len(disabled) > 5:
                print(f"  ... and {len(disabled)-5} more")
        
        print()

    
    # Configuration files to generate
    configs = [
        {
            'template': '.env.j2',
            'output': '.env',
            'label': '.env'
        },
        {
            'template': 'Dockerfile.base.j2',
            'output': 'Dockerfile.base',
            'label': 'Dockerfile.base'
        },
        {
            'template': 'Dockerfile.php7.2.j2',
            'output': 'Dockerfile.php7.2',
            'label': 'Dockerfile.php7.2'
        },
        {
            'template': 'Dockerfile.php8.3.j2',
            'output': 'Dockerfile.php8.3',
            'label': 'Dockerfile.php8.3'
        },
        {
            'template': 'build-images.sh.j2',
            'output': 'build-images.sh',
            'label': 'build-images.sh'
        },
        {
            'template': 'docker-compose.yml.j2',
            'output': 'docker-compose.yml',
            'label': 'docker-compose.yml'
        },
        {
            'template': 'docker-compose.override.yml.j2',
            'output': 'docker-compose.override.yml',
            'label': 'docker-compose.override.yml'
        },
        {
            'template': 'MULTI_TENANT.md.j2',
            'output': 'MULTI_TENANT.md',
            'label': 'MULTI_TENANT.md'
        },
        {
            'template': 'traefik-dynamic.yml.j2',
            'output': 'traefik/dynamic.yml',
            'label': 'traefik/dynamic.yml'
        },
        {
            'template': 'durango-apache.conf.j2',
            'output': 'config/durango-apache.conf',
            'label': 'config/durango-apache.conf'
        },
        {
            'template': 'orangescrum-apache.conf.j2',
            'output': 'config/orangescrum-apache.conf',
            'label': 'config/orangescrum-apache.conf'
        },
        {
            'template': 'php-trust-certs.sh.j2',
            'output': 'php-trust-certs.sh',
            'label': 'php-trust-certs.sh'
        },
        {
            'template': 'generate-certs.sh.j2',
            'output': 'generate-certs.sh',
            'label': 'generate-certs.sh'
        },
        {
            'template': 'os-v2.env.j2',
            'output': 'os-v2/.env',
            'label': 'os-v2/.env'
        },
        {
            'template': 'dnsmasq.conf.j2',
            'output': 'config/dnsmasq.conf',
            'label': 'config/dnsmasq.conf'
        },
        {
            'template': 'browser-trust-certs.sh.j2',
            'output': 'entrypoints/browser-trust-certs.sh',
            'label': 'entrypoints/browser-trust-certs.sh'
        },
        {
            'template': 'instance-apache.conf.j2',
            'output': 'config/instance-apache.conf',
            'label': 'config/instance-apache.conf'
        },
    ]
    
    # Add .new suffix for dry run
    if dry_run:
        for config in configs:
            config['output'] = config['output'] + '.new'
    
    # Generate each configuration file
    generated_files = []
    for config in configs:
        try:
            print_colored(f"Generating {config['label']}...", Colors.BLUE)
            
            template = env.get_template(config['template'])
            
            # Merge extra context if provided
            render_context = context.copy()
            if 'extra_context' in config:
                render_context.update(config['extra_context'])
            
            output_content = template.render(render_context)
            
            output_path = Path(config['output'])
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            output_path.write_text(output_content)
            
            # Make shell scripts executable
            if output_path.suffix == '.sh' or (output_path.suffix == '.new' and '.sh' in config['output']):
                output_path.chmod(0o755)
            
            generated_files.append(config['output'])
            print_colored(f"✓ Generated {config['output']}", Colors.GREEN)
            
        except Exception as e:
            print_colored(f"✗ Error generating {config['label']}: {e}", Colors.RED)
            sys.exit(1)
    
    # Attempt to place service .env files into mounted app folders so containers
    # pick them up automatically (avoid manual host copy).
    def safe_copy_env(src_path, target_path):
        src = Path(src_path)
        tgt = Path(target_path)
        if not src.exists():
            return False
        # Backup existing target if present
        if tgt.exists():
            bkp = Path(backup_dir) / f"{tgt.name}.bak"
            shutil.copy2(tgt, bkp)
        tgt.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, tgt)
        return True

    # .env files are now generated from templates above, no need to create from examples
    if not dry_run:
        # Ensure app logs directories exist (so apps can write logs inside mounted folders)
        for app_logs in ['apps/orangescrum-v4/logs', 'apps/orangescrum/logs', 'apps/durango-pg/logs']:
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
    
    # Show next steps or review message
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
    """Print next steps after configuration"""
    protocol = 'https' if enable_https else 'http'
    # Access point configuration
    access_points = [
        {"name": "V2 (Orangescrum)", "url": f"{protocol}://app.{domain}"},
        {"name": "MailHog", "url": f"{protocol}://mail.{domain}"},
        {"name": "Storage (MinIO)", "url": f"{protocol}://storage.{domain}"},
        {"name": "Storage Console", "url": f"{protocol}://console.{domain}"},
        {"name": "Traefik Dashboard", "url": f"{protocol}://traefik.{domain}"},
        {"name": "VNC Browser", "url": "http://localhost:3000"},
    ]
    
    # Load and render template
    templates_dir = Path('templates')
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        trim_blocks=True,
        lstrip_blocks=True
    )
    
    template = env.get_template('next-steps.txt.j2')
    output = template.render(domain=domain, access_points=access_points, services=services)
    print(output)


## ============================================================
## Instance Management
## ============================================================

RESERVED_SUBDOMAINS = {'www', 'app', 'mail', 'traefik', 'storage', 'console', 'old-selfhosted'}
REGISTRY_FILE = Path('instances/registry.json')
DEFAULT_SOURCE_PATHS = {
    'v4': './apps/orangescrum-v4',
    'selfhosted': './apps/durango-pg',
}


def load_registry():
    """Load instance registry from JSON file"""
    if not REGISTRY_FILE.exists():
        return {'domain': detect_current_domain(), 'instances': {}}
    import json
    reg = json.loads(REGISTRY_FILE.read_text())
    # Backfill domain if missing
    if not reg.get('domain'):
        reg['domain'] = detect_current_domain()
    return reg


def save_registry(registry):
    """Save instance registry to JSON file"""
    import json
    REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_FILE.write_text(json.dumps(registry, indent=2) + '\n')


def get_project_context():
    """Load project context from generated .env file and detect domain"""
    domain = detect_current_domain()
    if not domain:
        print_colored("Error: No domain configured. Run './generate-config.py <domain>' first.", Colors.RED)
        sys.exit(1)

    # Load .env for port config
    env_file = Path('.env')
    env_vars = {}
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                env_vars[k.strip()] = v.strip()

    domain_prefix = domain.replace('.', '-').replace('_', '-')

    # Detect HTTPS from traefik/dynamic.yml
    enable_https = False
    dynamic_yml = Path('traefik/dynamic.yml')
    if dynamic_yml.exists():
        content = dynamic_yml.read_text()
        enable_https = 'websecure' in content

    # Detect cache engine from base compose
    cache_engine = 'redis'  # default
    compose_file = Path('docker-compose.yml')
    if compose_file.exists():
        content = compose_file.read_text()
        if 'redis-durango' in content:
            cache_engine = 'redis'
        elif 'memcached-durango' in content:
            cache_engine = 'memcached'

    return {
        'domain': domain,
        'domain_prefix': domain_prefix,
        'enable_https': enable_https,
        'cache_engine': cache_engine,
        'project_root': str(Path.cwd()),
        'env_vars': env_vars,
    }


def instance_create(args):
    """Create a new dynamic instance"""
    import hashlib
    import json
    import subprocess

    name = args.name
    instance_type = args.type
    subdomain = args.subdomain or name
    source = args.source

    # Validate name
    import re
    if not re.match(r'^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$', name):
        print_colored("Error: Instance name must be lowercase alphanumeric with hyphens (e.g., 'v4-main', 'next')", Colors.RED)
        sys.exit(1)

    # Validate subdomain not reserved
    if subdomain in RESERVED_SUBDOMAINS:
        print_colored(f"Error: Subdomain '{subdomain}' is reserved. Reserved: {', '.join(sorted(RESERVED_SUBDOMAINS))}", Colors.RED)
        sys.exit(1)

    # Load registry
    registry = load_registry()

    # Check for duplicate name
    if name in registry.get('instances', {}):
        print_colored(f"Error: Instance '{name}' already exists. Use 'instance destroy' first.", Colors.RED)
        sys.exit(1)

    # Check for duplicate subdomain
    for inst_name, inst in registry.get('instances', {}).items():
        if inst.get('subdomain') == subdomain:
            print_colored(f"Error: Subdomain '{subdomain}' already used by instance '{inst_name}'.", Colors.RED)
            sys.exit(1)

    ctx = get_project_context()
    domain = ctx['domain']
    domain_prefix = ctx['domain_prefix']

    # Resolve source path
    if not source:
        source = DEFAULT_SOURCE_PATHS.get(instance_type, DEFAULT_SOURCE_PATHS['v4'])
    source_abs = str(Path(source).resolve())

    if not Path(source).exists():
        print_colored(f"Error: Source path '{source}' does not exist.", Colors.RED)
        sys.exit(1)

    # Database naming
    db_name = f"{instance_type}_{name}".replace('-', '_')
    db_user = instance_type.replace('-', '_')  # 'orangescrum' for v4, 'durango' for selfhosted
    if instance_type == 'v4':
        db_user = 'orangescrum'
    elif instance_type == 'selfhosted':
        db_user = 'durango'
    db_password = db_user  # Dev environment default

    # Generate security salt
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
    print(f"Database: {db_name}")
    print()

    # Setup Jinja2
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
    }

    # Create instance directory
    instance_dir = Path(f'instances/{name}')
    instance_dir.mkdir(parents=True, exist_ok=True)

    # Generate instance .env
    print_colored("Generating instance .env...", Colors.BLUE)
    tpl = env.get_template('instance.env.j2')
    (instance_dir / '.env').write_text(tpl.render(template_context))
    print_colored(f"  Generated instances/{name}/.env", Colors.GREEN)

    # Generate instance docker-compose.yml
    print_colored("Generating instance docker-compose.yml...", Colors.BLUE)
    tpl = env.get_template('instance-docker-compose.yml.j2')
    (instance_dir / 'docker-compose.yml').write_text(tpl.render(template_context))
    print_colored(f"  Generated instances/{name}/docker-compose.yml", Colors.GREEN)

    # Generate Traefik routing config
    print_colored("Generating Traefik routing config...", Colors.BLUE)
    tpl = env.get_template('instance-traefik.yml.j2')
    traefik_file = Path(f'traefik/instance-{name}.yml')
    traefik_file.write_text(tpl.render(template_context))
    print_colored(f"  Generated traefik/instance-{name}.yml (auto-discovered by Traefik)", Colors.GREEN)

    # Create database
    print_colored("Creating PostgreSQL database...", Colors.BLUE)
    pg_container = f"{domain_prefix}-postgres16"
    try:
        # Create user if not exists
        subprocess.run([
            'docker', 'exec', pg_container, 'psql', '-U', 'postgres', '-c',
            f"DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '{db_user}') "
            f"THEN CREATE ROLE {db_user} WITH LOGIN PASSWORD '{db_password}'; END IF; END $$;"
        ], check=True, capture_output=True, text=True)

        # Create database if not exists
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

        # Grant privileges
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

    # Update registry
    registry['domain'] = domain
    registry.setdefault('instances', {})
    registry['instances'][name] = {
        'type': instance_type,
        'subdomain': subdomain,
        'db_name': db_name,
        'db_user': db_user,
        'container_name': f"{domain_prefix}-{name}",
        'source_path': source,
        'created_at': datetime.now().isoformat(),
        'status': 'running'
    }
    save_registry(registry)

    # Summary
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

    # Detect HTTPS
    ctx = get_project_context()
    protocol = 'https' if ctx['enable_https'] else 'http'

    print_header("Dynamic Instances")
    print(f"{'Name':<16} {'Type':<12} {'Subdomain':<24} {'Database':<24} {'Status'}")
    print("-" * 96)
    for name, inst in instances.items():
        subdomain = inst.get('subdomain', name)
        url = f"{protocol}://{subdomain}.{domain}"
        print(f"{name:<16} {inst['type']:<12} {url:<24} {inst['db_name']:<24} {inst.get('status', 'unknown')}")
    print()


def instance_start(args):
    """Start a stopped instance"""
    import subprocess

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
    import subprocess

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
    import subprocess

    registry = load_registry()
    name = args.name

    if name not in registry.get('instances', {}):
        print_colored(f"Error: Instance '{name}' not found.", Colors.RED)
        sys.exit(1)

    inst = registry['instances'][name]
    ctx = get_project_context()

    print_header(f"Destroying Instance: {name}")

    # Stop container
    instance_dir = Path(f'instances/{name}')
    compose_file = instance_dir / 'docker-compose.yml'
    if compose_file.exists():
        print_colored("Stopping container...", Colors.BLUE)
        try:
            subprocess.run(['docker', 'compose', '-f', str(compose_file), 'down'], check=True, capture_output=True, text=True)
            print_colored("  Container stopped.", Colors.GREEN)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print_colored("  Warning: Could not stop container.", Colors.YELLOW)

    # Remove Traefik config
    traefik_file = Path(f'traefik/instance-{name}.yml')
    if traefik_file.exists():
        traefik_file.unlink()
        print_colored(f"  Removed traefik/instance-{name}.yml", Colors.GREEN)

    # Drop database if requested
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

    # Remove instance directory
    if instance_dir.exists():
        shutil.rmtree(instance_dir)
        print_colored(f"  Removed instances/{name}/", Colors.GREEN)

    # Update registry
    del registry['instances'][name]
    save_registry(registry)

    print()
    print_colored(f"Instance '{name}' destroyed.", Colors.GREEN)
    print()


def instance_db_setup(args):
    """Run database migrations and seeds for an instance"""
    import subprocess

    registry = load_registry()
    name = args.name

    if name not in registry.get('instances', {}):
        print_colored(f"Error: Instance '{name}' not found.", Colors.RED)
        sys.exit(1)

    ctx = get_project_context()
    container = f"{ctx['domain_prefix']}-{name}"

    print_header(f"Database Setup: {name}")

    # Run migrations
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

    # Run seeders
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


def instance_logs(args):
    """View logs for an instance"""
    import subprocess

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
    import subprocess

    registry = load_registry()
    name = args.name

    if name not in registry.get('instances', {}):
        print_colored(f"Error: Instance '{name}' not found.", Colors.RED)
        sys.exit(1)

    ctx = get_project_context()
    container = f"{ctx['domain_prefix']}-{name}"
    os.execvp('docker', ['docker', 'exec', '-it', container, '/bin/bash'])


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

    files_to_remove = [
        '.env',
        'docker-compose.yml',
        'docker-compose.override.yml',
        'MULTI_TENANT.md',
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

    # Remove any generated .new files from dry-run
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


def build_instance_parser():
    """Build argparse parser for instance subcommands"""
    parser = argparse.ArgumentParser(
        prog='generate-config.py instance',
        description='Manage dynamic V4/selfhosted instances',
    )
    sub = parser.add_subparsers(dest='instance_command')

    # create
    p = sub.add_parser('create', help='Create a new instance')
    p.add_argument('--name', required=True, help='Instance name (e.g., v4-main, next, sh-client1)')
    p.add_argument('--type', required=True, choices=['v4', 'selfhosted'], help='Instance type')
    p.add_argument('--subdomain', help='Subdomain (default: same as name)')
    p.add_argument('--source', help='Path to app source (default: apps/orangescrum-v4 or apps/durango-pg)')

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
    parser = argparse.ArgumentParser(
        description='OrangeScrum Docker Configuration & Instance Manager',
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

    # Handle reset
    if args.reset:
        handle_reset()
        sys.exit(0)

    # Domain is required for config generation
    if not args.domain:
        parser.print_help()
        sys.exit(2)

    generate_configurations(args.domain, args.dry_run, args.interactive, not args.no_https)


if __name__ == '__main__':
    main()
