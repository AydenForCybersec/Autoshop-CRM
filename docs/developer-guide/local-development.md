# Developer Guide: Local Development

## Who this is for
Developers running the project locally.

## Before you start
- Python 3.10+ is installed.
- Virtual environment is active.

## Step-by-step
1. Install dependencies:
   `pip install -r requirements.txt`
2. Create env file:
   `cp .env.example .env`
3. Export package path:
   `export PYTHONPATH="$(pwd)/src:${PYTHONPATH:-}"`
4. Apply migrations:
   `flask --app autoshop_crm:create_app db upgrade`
5. Start app:
   `flask --app autoshop_crm:create_app run --host=0.0.0.0 --port=5000`

## If this fails
- Import errors: confirm `PYTHONPATH` includes `src`.
- DB errors: verify `DATABASE_URL` value.
- Startup redirects: complete `/setup-admin` if first run.

## Done when
- App boots with no import or migration errors.
- You can log in and open dashboard pages.
