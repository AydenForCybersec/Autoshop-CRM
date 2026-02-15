# Developer Guide: Deployment

## Who this is for
Developers or operators deploying production.

## Before you start
- Production `.env` is prepared.
- Backup plan is verified.

## Step-by-step
1. Install dependencies in production virtualenv.
2. Set env vars (`FLASK_APP`, `FLASK_ENV`, `SECRET_KEY`, `DATABASE_URL`).
3. Set `PYTHONPATH` to include `/opt/autoshop-crm/src`.
4. Run `flask --app autoshop_crm:create_app db upgrade`.
5. Run Gunicorn behind reverse proxy.
6. Validate login, dashboard, customers, and settings pages.

## If this fails
- App fails to boot: inspect service logs and env file.
- Migration failure: restore backup and fix schema mismatch.
- Static asset issues: verify static path and reverse proxy config.

## Done when
- Service is healthy after restart.
- Core pages and workflows are operational.
