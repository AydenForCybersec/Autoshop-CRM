# Autoshop CRM

Autoshop CRM is a shop management app for customer records, vehicle history, work orders, and day-to-day service operations.

## Start Here

- Non-technical staff: `docs/user-guide/getting-started.md`
- Admins and owners: `docs/admin-guide/initial-setup.md`
- Developers: `docs/developer-guide/local-development.md`
- Full docs map: `docs/index.md`

## Quick Run

```zsh
cp .env.example .env
export PYTHONPATH="$(pwd)/src:${PYTHONPATH:-}"
flask --app autoshop_crm:create_app db upgrade
flask --app autoshop_crm:create_app run --host=0.0.0.0 --port=5000
```

## In-App Help Center

When the server is running, authenticated users can open:

- `GET /help` for Help home
- `GET /help/<slug>` for help articles

The in-app Help content is curated from repository documentation and is designed for non-technical users.

## Testing

```zsh
pytest
```
