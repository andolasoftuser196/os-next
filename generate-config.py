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
        'docker-compose.yml',
        'traefik/dynamic.yml',
        'config/durango-apache.conf',
        'config/orangescrum-apache.conf',
        'php-trust-certs.sh',
        'generate-certs.sh'
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


def generate_configurations(domain, dry_run=False, interactive=False):
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
    
    print_header("OrangeScrum Docker Configuration Generator")
    print(f"Domain: {domain}")
    print(f"LAN IP: {lan_ip}")
    print(f"Mode: {'Dry run (review only)' if dry_run else 'Apply configurations'}\n")
    
    # Ask about docker-compose.override.yml
    generate_override = False
    if not dry_run:
        try:
            response = input("Generate docker-compose.override.yml for port mappings? (y/N): ").strip().lower()
            generate_override = response in ['y', 'yes']
        except (EOFError, KeyboardInterrupt):
            print()  # New line after interrupted input
    
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
    
    # Template context
    context = {
        'domain': domain,
        'generated_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'traefik_ip': '172.25.0.10',
        'builder_uid': '${BUILDER_UID:-1000}',
        'lan_ip': lan_ip
    }
    # Default services selection (enable common services)
    context['services'] = {
        'durango_pg': True,
        'orangescrum_v4': True,
        'orangescrum': True,
        'postgres16': True,
        'mysql': True,
        'redis_durango': True,
        'memcached_orangescrum': True,
        'memcached_durango': True,
        'minio': True,
        'mailhog': True,
        'browser': False
    }

    # Interactive selection of services
    if interactive and not dry_run:
        print_colored('\nInteractive service selection:', Colors.BLUE)
        for key in list(context['services'].keys()):
            default = context['services'][key]
            try:
                resp = input(f"Enable {key.replace('_', ' ')}? [{'Y' if default else 'y'}/n]: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                resp = ''
            if resp == 'n' or resp == 'no':
                context['services'][key] = False
            elif resp == 'y' or resp == 'yes' or resp == '':
                context['services'][key] = True

    
    # Configuration files to generate
    configs = [
        {
            'template': 'docker-compose.yml.j2',
            'output': 'docker-compose.yml',
            'label': 'docker-compose.yml'
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
            'template': 'oschrome.desktop.j2',
            'output': f'launchers/linux-{domain}-local.desktop',
            'label': f'launchers/linux-{domain}-local.desktop',
            'extra_context': {'target_ip': '127.0.0.1', 'profile': 'local'}
        },
        {
            'template': 'oschrome.desktop.j2',
            'output': f'launchers/linux-{domain}-lan.desktop',
            'label': f'launchers/linux-{domain}-lan.desktop',
            'extra_context': {'target_ip': lan_ip, 'profile': 'lan'}
        },
        {
            'template': 'oschrome.bat.j2',
            'output': f'launchers/windows-{domain}-local.bat',
            'label': f'launchers/windows-{domain}-local.bat',
            'extra_context': {'target_ip': '127.0.0.1', 'profile': 'local'}
        },
        {
            'template': 'oschrome.bat.j2',
            'output': f'launchers/windows-{domain}-lan.bat',
            'label': f'launchers/windows-{domain}-lan.bat',
            'extra_context': {'target_ip': lan_ip, 'profile': 'lan'}
        }
    ]
    
    # Add docker-compose.override.yml if requested
    if generate_override:
        configs.append({
            'template': 'docker-compose.override.yml.j2',
            'output': 'docker-compose.override.yml',
            'label': 'docker-compose.override.yml'
        })
    
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
            if output_path.suffix in ['.sh', ''] and config['output'].endswith('.sh.new'):
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

    # Ensure generated env files exist where docker-compose expects them:
    required_envs = ['os-v2/.env', 'os-v4/.env', 'os-pg/.env']

    if not dry_run:
        for src in required_envs:
            s = Path(src)
            if s.exists():
                print_colored(f"✓ Env present: {src}", Colors.GREEN)
                continue

            # If missing, try to create from .env.example in the same folder
            example = s.parent / '.env.example'
            if example.exists():
                try:
                    shutil.copy2(example, s)
                    print_colored(f"Created env from example: {s}", Colors.GREEN)
                except Exception as e:
                    print_colored(f"Could not create {s} from {example}: {e}", Colors.YELLOW)
            else:
                print_colored(f"⚠ Missing env: {src} (no .env.example found)", Colors.YELLOW)

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
        print_next_steps(domain)
    
    print()


def print_next_steps(domain):
    """Print next steps after configuration"""
    # Access point configuration
    access_points = [
        {"name": "V2 (Orangescrum)", "url": f"https://app.{domain}"},
        {"name": "V4 (OrangeScrum)", "url": f"https://v4.{domain}"},
        {"name": "V4 (Durango PG)", "url": f"https://selfhosted.{domain}"},
        {"name": "MailHog", "url": f"https://mail.{domain}"},
        {"name": "Storage (MinIO)", "url": f"https://storage.{domain}"},
        {"name": "Storage Console", "url": f"https://console.{domain}"},
        {"name": "Traefik Dashboard", "url": f"https://traefik.{domain}"}
    ]
    
    # Load and render template
    templates_dir = Path('templates')
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        trim_blocks=True,
        lstrip_blocks=True
    )
    
    template = env.get_template('next-steps.txt.j2')
    output = template.render(domain=domain, access_points=access_points)
    print(output)


def main():
    parser = argparse.ArgumentParser(
        description='Generate Docker configurations for multi-domain setup',
        epilog='Example: %(prog)s ossiba.local'
    )
    parser.add_argument(
        'domain',
        nargs='?',
        default=None,
        help='Base domain for the setup (e.g., ossiba.local, ossiba.com)'
    )
    parser.add_argument(
        '--reset',
        action='store_true',
        help='Backup and remove previously generated configuration files'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Generate .new files for review without applying'
    )
    parser.add_argument(
        '-y', '--yes',
        action='store_true',
        help='Assume yes for prompts (no-op compatibility flag)'
    )
    parser.add_argument(
        '--apply-env',
        action='store_true',
        help='Compatibility flag: apply generated env files (handled by generator by default)'
    )
    parser.add_argument(
        '-i', '--interactive',
        action='store_true',
        help='Interactive mode: prompt for service selection and options'
    )
    
    args = parser.parse_args()
    
    # Change to script directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)

    # Handle reset operation (no domain required)
    if args.reset:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = f"backups/{timestamp}"
        print_header("Reset: backing up and removing generated files")
        backed_up = backup_files(backup_dir)
        if backed_up:
            print_colored(f"Backed up {len(backed_up)} files to {backup_dir}", Colors.GREEN)
        else:
            print_colored("No generated config files found to backup.", Colors.YELLOW)

        # Files to remove (mirror the backup list)
        files_to_remove = [
            'docker-compose.yml',
            'docker-compose.override.yml',
            'traefik/dynamic.yml',
            'config/durango-apache.conf',
            'config/orangescrum-apache.conf',
            'php-trust-certs.sh',
            'generate-certs.sh'
        ]
        # Also remove generated launchers for any domain patterns and env files
        files_to_remove.extend(['os-v2/.env', 'os-v4/.env', 'os-pg/.env'])

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
        # Also remove generated launcher files (desktop and bat)
        try:
            launcher_dir = Path('launchers')
            if launcher_dir.exists():
                for pattern in ('linux-*.desktop', 'windows-*.bat'):
                    for lf in launcher_dir.glob(pattern):
                        try:
                            lf.unlink()
                            print_colored(f"Removed: {lf}", Colors.GREEN)
                        except Exception as e:
                            print_colored(f"Could not remove {lf}: {e}", Colors.YELLOW)
        except Exception:
            pass
        # Also remove any generated .new files from dry-run
        try:
            new_files = list(Path('.').rglob('*.new'))
            for nf in new_files:
                # Skip any files inside the backups directory to preserve archives
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
        sys.exit(0)

    # Domain is required for normal generation
    if not args.domain:
        parser.print_usage()
        print_colored("Error: domain is required unless --reset is used.", Colors.RED)
        sys.exit(2)

    generate_configurations(args.domain, args.dry_run, args.interactive)


if __name__ == '__main__':
    main()
