# Reference: CLI and Scripts

## Who this is for
Admins and developers running maintenance commands.

## Before you start
- Activate virtualenv and set `PYTHONPATH`.

## Step-by-step
1. Run tests: `pytest`
2. Apply DB changes: `flask --app autoshop_crm:create_app db upgrade`
3. Use the unified CLI:
   - `python scripts/autoshopctl.py` (or `python scripts/autoshopctl.py status`) to check setup state
   - `python scripts/autoshopctl.py setup` for interactive local bootstrap (mode, DB, `.env`, and optional components)
   - `python scripts/autoshopctl.py setup --no-interactive --mode dev --db-url sqlite:///autoshop.db` for non-interactive bootstrap
   - `python scripts/autoshopctl.py setup --mode prod --with-systemd --with-tailscale --install-system-packages` for Linux production bootstrap
   - `python scripts/autoshopctl.py deploy --remote origin --branch <branch>` for fast-forward deploy + deps + migrations
   - `python scripts/autoshopctl.py backup --db-name <name> --db-user <user> --db-password <password>` for DB backup
   - `python scripts/autoshopctl.py uninstall --restore-env --remove-systemd --remove-tailscale --purge-system-packages` to revert install changes
4. Legacy wrappers still exist and route into `autoshopctl`:
   - `scripts/setup.sh`, `scripts/deploy_from_github.sh`, `scripts/backup_db.sh`, `scripts/uninstall.sh`

## If this fails
- Script permission denied: run `chmod +x scripts/<name>.sh`.
- Missing env values: verify `.env` and shell exports.

## Done when
- Commands complete without errors and expected outcomes are visible.
