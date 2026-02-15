# Admin Guide: Initial Setup

## Who this is for
Owners/admins performing first-time setup.

## Before you start
- Python environment is installed.
- `.env` exists and has `SECRET_KEY`, `DATABASE_URL`, and `FLASK_APP`.

## Step-by-step
1. Create `.env` from `.env.example`.
2. Export Python path:
   `export PYTHONPATH="$(pwd)/src:${PYTHONPATH:-}"`
3. Run migrations:
   `flask --app autoshop_crm:create_app db upgrade`
4. Start server:
   `flask --app autoshop_crm:create_app run --host=0.0.0.0 --port=5000`
5. Open `/setup-admin` and create the first admin account.
6. Sign in and verify `Dashboard`, `Customers`, and `Settings` load.

## If this fails
- Migration errors: verify `DATABASE_URL` and DB credentials.
- Setup page loops: ensure no broken DB schema and rerun migrations.
- Login issues after setup: verify account is active in DB.

## Done when
- Admin account exists and can sign in.
- Settings and user management are accessible.
