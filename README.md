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

## Demo quickstart

After installation, initialize and seed the database with demo records:

```zsh
flask db upgrade
flask seed-demo-data
python run.py
```

The seed command creates:
- one login user (`demo` / `demo123` by default)
- several customers
- multiple vehicles per customer
- jobs with mixed statuses (`open`, `in_progress`, `completed`, `on_hold`)

You can also override demo credentials:

```zsh
flask seed-demo-data --username shopadmin --password 'ChangeMe123!'
```

