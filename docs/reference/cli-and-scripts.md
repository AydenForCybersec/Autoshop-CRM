# Reference: CLI and Scripts

## Who this is for
Admins and developers running maintenance commands.

## Before you start
- Activate virtualenv and set `PYTHONPATH`.

## Step-by-step
1. Run tests: `pytest`
2. Apply DB changes: `flask --app autoshop_crm:create_app db upgrade`
3. Use helper scripts:
   - `scripts/setup.sh` for host bootstrap
   - `scripts/backup_db.sh` for DB backup
   - `scripts/uninstall.sh` for local reset

## If this fails
- Script permission denied: run `chmod +x scripts/<name>.sh`.
- Missing env values: verify `.env` and shell exports.

## Done when
- Commands complete without errors and expected outcomes are visible.
