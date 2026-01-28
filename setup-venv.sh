#!/usr/bin/env bash
set -euo pipefail

# setup-venv.sh
# Creates a local Python virtual environment at .venv and installs requirements.

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$script_dir"

if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "Error: python3 is not installed. Install Python 3 and retry." >&2
  exit 1
fi

if [ -d ".venv" ]; then
  echo ".venv already exists — using existing virtualenv"
else
  echo "Creating virtualenv in .venv..."
  $PY -m venv .venv
fi

echo "Activating virtualenv and upgrading pip..."
# shellcheck source=/dev/null
. .venv/bin/activate

pip install --upgrade pip setuptools wheel

if [ -f requirements.txt ]; then
  echo "Installing Python dependencies from requirements.txt..."
  pip install -r requirements.txt
else
  echo "No requirements.txt found; skipping pip install."
fi

cat <<'EOF'

Done.
To use the virtualenv in your shell run:
  source .venv/bin/activate

You can run the generator as:
  python3 generate-config.py example.com --dry-run
or:
  ./generate-config.py example.com

EOF
