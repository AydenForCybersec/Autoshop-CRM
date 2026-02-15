# Developer Guide: Deployment

## Who this is for
Developers or operators deploying production.

## Before you start
- Production `.env` is prepared.
- Backup plan is verified.
- A dedicated Linux user and systemd service account strategy is decided.

## Step-by-step
1. Install dependencies in production virtualenv (`.venv` or `venv`).
2. Set env vars in `.env` (minimum: `FLASK_APP`, `FLASK_ENV=production`, `SECRET_KEY`, `DATABASE_URL`).
3. Ensure systemd service reads `.env` (`EnvironmentFile=/path/to/repo/.env`) and exports `PYTHONPATH=/path/to/repo/src`.
4. Run `flask --app autoshop_crm:create_app db upgrade`.
5. Run Gunicorn behind reverse proxy under a dedicated non-root service user.
6. Validate login, dashboard, customers, and settings pages.
7. Run the deploy helper for repeatable GitHub-based updates:
   - `python scripts/autoshopctl.py deploy --remote origin --branch <branch>`
8. Keep update manager disabled unless explicitly needed (`UPDATE_ENABLED=false` default in production).
9. If enabling in-app updates, restrict post commands:
   - `UPDATE_ALLOWED_COMMAND_PREFIXES=./scripts/autoshopctl.py`
   - `UPDATE_POST_UPDATE_COMMANDS=./scripts/autoshopctl.py deploy --skip-pull`

## If this fails
- App fails to boot: inspect service logs and env file.
- Migration failure: restore backup and fix schema mismatch.
- Static asset issues: verify static path and reverse proxy config.
- Production boot failure with `SECRET_KEY` error: set a non-placeholder secret in `.env`.

## Done when
- Service is healthy after restart.
- Core pages and workflows are operational.
- `python scripts/autoshopctl.py deploy` completes without errors.
