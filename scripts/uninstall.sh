#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/uninstall.sh [options]

Uninstall local Autoshop CRM app artifacts to allow a clean reinstall/testing cycle.

Options:
  --yes           Skip the confirmation prompt.
  --remove-env    Also remove .env.
  --keep-data     Keep runtime data directories (instance/, logs/, *.db).
  -h, --help      Show this help.
EOF
}

confirm=false
remove_env=false
keep_data=false

while (($#)); do
  case "$1" in
    --yes)
      confirm=true
      ;;
    --remove-env)
      remove_env=true
      ;;
    --keep-data)
      keep_data=true
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      usage
      exit 1
      ;;
  esac
  shift
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd -- "${script_dir}/.." && pwd)"
cd "$project_root"

if [[ ! -f "run.py" ]] || [[ ! -d "src/autoshop_crm" ]]; then
  echo "Run this script from the Autoshop CRM repository."
  exit 1
fi

targets=(
  "venv"
  ".venv"
  ".pytest_cache"
  ".mypy_cache"
  ".ruff_cache"
  ".coverage"
  "build"
  "dist"
)

if [[ "$keep_data" == false ]]; then
  targets+=(
    "instance"
    "logs"
    "autoshop.db"
  )
fi

if [[ "$remove_env" == true ]]; then
  targets+=(".env")
fi

echo "The following paths will be removed if they exist:"
for path in "${targets[@]}"; do
  echo "  - $path"
done
echo "  - all __pycache__ directories"
echo "  - all *.pyc/*.pyo files"
echo

if [[ "$confirm" == false ]]; then
  read -r -p "Continue uninstall? [y/N] " answer
  case "$answer" in
    y|Y|yes|YES)
      ;;
    *)
      echo "Aborted."
      exit 0
      ;;
  esac
fi

if command -v systemctl >/dev/null 2>&1 && systemctl list-unit-files | grep -q '^autoshop\.service'; then
  if [[ "${EUID}" -eq 0 ]]; then
    systemctl disable --now autoshop.service >/dev/null 2>&1 || true
    rm -f /etc/systemd/system/autoshop.service
    systemctl daemon-reload >/dev/null 2>&1 || true
    echo "Removed systemd unit: autoshop.service"
  else
    echo "systemd unit autoshop.service detected. Re-run with sudo to remove it."
  fi
fi

for path in "${targets[@]}"; do
  if [[ -e "$path" ]]; then
    rm -rf -- "$path"
    echo "Removed: $path"
  fi
done

find . -type d -name "__pycache__" -prune -exec rm -rf {} +
find . -type f \( -name "*.pyc" -o -name "*.pyo" \) -delete

echo
echo "Local uninstall complete."
echo "Reinstall quickly with:"
echo "  python -m venv venv"
echo "  source venv/bin/activate"
echo "  pip install -r requirements.txt"
echo "  export PYTHONPATH=\"\$(pwd)/src:\${PYTHONPATH:-}\""
echo
echo "Note: external databases (MySQL/MariaDB) are not dropped by this script."
