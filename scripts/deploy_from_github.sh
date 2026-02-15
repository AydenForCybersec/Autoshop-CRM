#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'HELP'
Usage: scripts/deploy_from_github.sh [options]

Fast-forward deploy from GitHub and run post-pull app steps.

Options:
  --remote <name>      Git remote to pull from (default: origin or REMOTE env var).
  --branch <name>      Branch to deploy (default: current branch or BRANCH env var).
  --skip-pull          Skip git fetch/merge (useful after in-app updater already merged).
  --skip-restart       Skip systemd restart.
  -h, --help           Show this help.
HELP
}

remote="${REMOTE:-origin}"
branch="${BRANCH:-}"
skip_pull=false
skip_restart=false

while (($#)); do
  case "$1" in
    --remote)
      remote="$2"
      shift 2
      ;;
    --branch)
      branch="$2"
      shift 2
      ;;
    --skip-pull)
      skip_pull=true
      shift
      ;;
    --skip-restart)
      skip_restart=true
      shift
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
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd -- "${script_dir}/.." && pwd)"
cd "$project_root"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Repository is not a git checkout: $project_root"
  exit 1
fi

if [[ -z "$branch" ]]; then
  branch="$(git rev-parse --abbrev-ref HEAD)"
fi

if [[ "$skip_pull" == false ]]; then
  if [[ -n "$(git status --porcelain)" ]]; then
    echo "Refusing deploy with a dirty working tree. Commit or stash changes first."
    exit 1
  fi

  echo "Fetching ${remote}/${branch}..."
  git fetch --prune "$remote" "$branch"
  echo "Applying fast-forward merge..."
  git merge --ff-only "${remote}/${branch}"
fi

venv_bin=""
for candidate in ".venv/bin" "venv/bin"; do
  if [[ -x "${candidate}/python" ]]; then
    venv_bin="$candidate"
    break
  fi
done

if [[ -z "$venv_bin" ]]; then
  echo "No virtualenv found (.venv/bin or venv/bin)."
  exit 1
fi

echo "Installing/updating Python dependencies..."
"${venv_bin}/pip" install -r requirements.txt

export PYTHONPATH="$project_root/src:${PYTHONPATH:-}"

echo "Applying database migrations..."
"${venv_bin}/flask" --app autoshop_crm:create_app db upgrade

if [[ "$skip_restart" == false ]]; then
  if command -v systemctl >/dev/null 2>&1 && systemctl list-unit-files | grep -q '^autoshop\.service'; then
    if [[ "${EUID}" -eq 0 ]]; then
      echo "Restarting autoshop.service..."
      systemctl restart autoshop.service
      systemctl --no-pager --full status autoshop.service | sed -n '1,12p'
    else
      echo "autoshop.service detected, but root privileges are required to restart it."
      echo "Run: sudo systemctl restart autoshop.service"
    fi
  else
    echo "No autoshop.service unit found. Skipping service restart."
  fi
fi

echo "Deploy step complete for branch '${branch}'."
