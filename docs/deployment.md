# Deployment

## Production Stack

Recommended baseline:
- Gunicorn as WSGI server
- systemd for service supervision
- MySQL/MariaDB or PostgreSQL for persistent storage
- Reverse proxy (Nginx/Caddy) for TLS and public ingress

## Build and Runtime Prerequisites

- Python 3.10+
- Virtual environment with `requirements.txt` installed
- `PYTHONPATH` must include `src/` unless you package/install the project

Example:

```zsh
export PYTHONPATH="/opt/autoshop-crm/src:${PYTHONPATH:-}"
```

## Required Environment Variables

- `FLASK_APP=autoshop_crm:create_app`
- `FLASK_ENV=production`
- `SECRET_KEY=<strong-random-value>`
- `DATABASE_URL=<sqlalchemy-url>`

Optional:
- `HOST`
- `PORT`
- `LOG_FILE`

## Database Migration Step

Run on each deploy that changes schema:

```zsh
flask --app autoshop_crm:create_app db upgrade
```

## Gunicorn Example

```zsh
gunicorn "autoshop_crm:create_app()" --bind 0.0.0.0:5000 --workers 2
```

## systemd Example

Use a unit similar to:

```ini
[Unit]
Description=AutoShop CRM
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/autoshop-crm
Environment="PATH=/opt/autoshop-crm/venv/bin"
Environment="PYTHONPATH=/opt/autoshop-crm/src"
Environment="FLASK_APP=autoshop_crm:create_app"
Environment="FLASK_ENV=production"
EnvironmentFile=/opt/autoshop-crm/.env
ExecStart=/opt/autoshop-crm/venv/bin/gunicorn "autoshop_crm:create_app()" --bind 0.0.0.0:5000 --workers 2
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

## Scripts

- `scripts/setup.sh`: full host bootstrap for Debian/Ubuntu style systems (root required).
- `scripts/backup_db.sh`: runs `mysqldump` using `DB_*` env vars.

## Deployment Notes

- Back up the database before migration.
- Keep `.env` out of version control.
- Prefer serving Flask behind a reverse proxy.
- See `docs/developer-guide.md` for a full runbook and troubleshooting.
