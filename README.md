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

## Quick Start

```zsh
cp .env.example .env
flask --app autoshop_crm:create_app db upgrade
flask --app autoshop_crm:create_app run --host=0.0.0.0 --port=5000
```

Use `DATABASE_URL` in `.env` as the canonical DB connection setting.

## Testing

```zsh
pytest
```

