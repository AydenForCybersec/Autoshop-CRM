# Deployment

## Production Server

Recommended stack:
- Gunicorn
- systemd
- PostgreSQL

Example Gunicorn command:

```zsh
gunicorn "autoshop_crm:create_app()"
```
### systemd
A systemd service file is included in /systemd.
Ensure environment variables are set securely.


## 📄 Root `README.md` (Upgrade This)

This is what sells the project.

```markdown
# Autoshop CRM

A simple, maintainable CRM for automotive repair shops.

## Features
- Customer management
- Vehicle tracking
- Job/work order tracking
- Authentication
- Database migrations

## Tech Stack
- Flask
- SQLAlchemy
- Alembic
- pytest

## Project Structure

See `docs/architecture.md`.

## Setup

See `docs/setup.md`.