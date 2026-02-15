# Autoshop CRM Developer Guide

## 1. Scope

This document is the primary developer documentation for this repository. It covers:
- Repository layout
- Local setup and environment
- Runtime architecture
- Data model
- HTTP routes and behaviors
- Service layer contracts
- CLI commands
- Migrations and schema management
- Testing strategy
- Operational scripts
- Deployment and troubleshooting
- Current technical risks and known issues

## 2. Repository Layout

Top-level structure:

- `src/autoshop_crm/`: application package
- `src/autoshop_crm/app.py`: app factory (`create_app`)
- `src/autoshop_crm/config.py`: config classes + env selection
- `src/autoshop_crm/extensions.py`: Flask extension singletons
- `src/autoshop_crm/models/`: SQLAlchemy models
- `src/autoshop_crm/services/`: business logic and DB transactions
- `src/autoshop_crm/routes/`: Flask blueprints and HTTP endpoints
- `src/autoshop_crm/templates/`: Jinja templates
- `src/autoshop_crm/static/`: CSS assets
- `migrations/`: Alembic migration environment + revisions
- `tests/`: pytest suite
- `scripts/`: shell scripts for setup and backup
- `run.py`: direct local entrypoint wrapper around `create_app`
- `requirements.txt`: Python dependencies
- `.env.example`: environment variable template

## 3. Technology Stack

Core runtime:
- Flask
- Flask-SQLAlchemy
- Flask-Migrate (Alembic)
- Flask-Login
- Werkzeug password hashing

Testing:
- pytest

Database:
- SQLAlchemy URL via `DATABASE_URL`
- Defaults to SQLite if `DATABASE_URL` is unset
- `.env.example` uses MySQL dialect URL examples

## 4. Local Development Setup

### 4.1 Requirements

- Python 3.10+
- A virtualenv tool (`python -m venv`)
- Optional MySQL/MariaDB if not using SQLite

### 4.2 Install

```zsh
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4.3 Configure Environment

```zsh
cp .env.example .env
```

Required variables:
- `SECRET_KEY`
- `DATABASE_URL`
- `FLASK_APP`

Recommended `.env` baseline:

```env
FLASK_APP=autoshop_crm:create_app
FLASK_ENV=development
SECRET_KEY=change-me
DATABASE_URL=sqlite:///autoshop.db
```

### 4.4 `src/` Import Path Requirement

The package is inside `src/`, so import resolution requires either:
- `export PYTHONPATH="$(pwd)/src:${PYTHONPATH:-}"`, or
- packaging/installing the project as a Python package (not currently configured in repo)

Run this in each shell session before Flask commands:

```zsh
export PYTHONPATH="$(pwd)/src:${PYTHONPATH:-}"
```

### 4.5 Run Database Migrations

```zsh
flask --app autoshop_crm:create_app db upgrade
```

### 4.6 Start Development Server

```zsh
flask --app autoshop_crm:create_app run --host=0.0.0.0 --port=5000
```

### 4.7 Run Tests

```zsh
pytest
```

`pytest.ini` already sets `pythonpath = src`, so tests do not need manual `PYTHONPATH` export.

## 5. Application Initialization and Wiring

`create_app()` in `src/autoshop_crm/app.py` performs:

1. Creates Flask app instance.
2. Loads config class from `get_config()`.
3. Initializes extensions:
- `db`
- `migrate`
- `login_manager`
4. Registers CLI commands from `src/autoshop_crm/cli.py`.
5. Registers blueprints:
- `auth_bp` (no prefix)
- `customers_bp` at `/customers`
- `vehicles_bp` at `/vehicles`
- `jobs_bp` at `/jobs`

`login_manager.login_view` is set to `auth.login_view`.

## 6. Configuration Model

Config is selected by `FLASK_ENV`:
- `development` (default): `DevelopmentConfig` (`DEBUG=True`)
- `production`: `ProductionConfig` (`DEBUG=False`)

Base config values:
- `SECRET_KEY`: env or fallback `dev-secret-key`
- `SQLALCHEMY_DATABASE_URI`: `DATABASE_URL` env or `sqlite:///autoshop.db`
- `SQLALCHEMY_TRACK_MODIFICATIONS=False`
- `TEMPLATES_AUTO_RELOAD=True`

## 7. Data Model

Current SQLAlchemy models in `src/autoshop_crm/models/`:

### 7.1 `User`

Fields:
- `id` (PK)
- `username` (unique, required)
- `password_hash` (required)

Behavior:
- `set_password(password)` hashes via Werkzeug
- `check_password(password)` validates hash
- Flask-Login user loader fetches by integer ID

### 7.2 `Customer`

Fields:
- `id` (PK)
- `name` (required)
- `email` (unique, optional)
- `phone` (optional)

Relations:
- one-to-many with `Vehicle` (`customer.vehicles`)

### 7.3 `Vehicle`

Fields:
- `id` (PK)
- `customer_id` (FK -> customers.id, required)
- `make` (required)
- `model` (required)
- `year` (optional integer)

Relations:
- many-to-one with `Customer`
- one-to-many with `Job`

### 7.4 `Job`

Fields:
- `id` (PK)
- `vehicle_id` (FK -> vehicles.id, required)
- `description` (required text)
- `status` (default `open`)
- `cost` (optional float)

Relations:
- many-to-one with `Vehicle`

## 8. HTTP Routes and UI Flows

### 8.1 Auth Blueprint (`src/autoshop_crm/routes/auth.py`)

- `GET/POST /login`
  - GET renders login form.
  - POST calls `services.auth.login(username, password)`.
  - On success: redirect to customers list.
  - On failure: flash "Invalid username or password".
- `GET /logout`
  - Requires login.
  - Calls `services.auth.logout()` then redirects to login page.

Template:
- `templates/auth/login.html`

### 8.2 Customers Blueprint (`src/autoshop_crm/routes/customers.py`)

- `GET /customers/`
  - Query param: `page` (int, default 1).
  - Calls `get_customers_paginated(page)`.
  - Renders customers list + pagination.
- `GET /customers/<customer_id>`
  - Fetches single customer via `get_customer`.
  - Renders customer detail with vehicle list and add-vehicle form.
- `POST /customers/create`
  - Form fields: `name`, optional `email`, optional `phone`.
  - Calls `create_customer`.
  - Redirects to customers list.

Templates:
- `templates/customers/list.html`
- `templates/customers/detail.html`
- `templates/layouts/pagination.html`

### 8.3 Vehicles Blueprint (`src/autoshop_crm/routes/vehicles.py`)

- `GET /vehicles/<vehicle_id>`
  - Fetches vehicle and associated jobs.
  - Renders vehicle detail.
- `POST /vehicles/create`
  - Form fields: `customer_id`, `make`, `model`, optional `year`.
  - Calls `create_vehicle`.
  - Redirects to newly created vehicle detail.

Template:
- `templates/vehicles/detail.html`

### 8.4 Jobs Blueprint (`src/autoshop_crm/routes/jobs.py`)

- `POST /jobs/create`
  - Form fields: `vehicle_id`, `description`, optional `cost`.
  - Calls `create_job`.
  - Redirects to vehicle detail.
- `POST /jobs/<job_id>/status`
  - Form field: `status`.
  - Calls `update_job_status`.
  - Redirects to vehicle detail.

## 9. Service Layer Contracts

### 9.1 Customer Services (`services/customers.py`)

- `get_all_customers()` -> all customers sorted by name
- `get_customers_paginated(page, per_page=10)` -> Flask-SQLAlchemy Pagination
- `create_customer(name, email=None, phone=None)` -> persists customer
- `get_customer(customer_id)` -> `get_or_404`

### 9.2 Vehicle Services (`services/vehicles.py`)

- `get_vehicle(vehicle_id)` -> `get_or_404`
- `get_vehicles_for_customer(customer_id)` -> list
- `create_vehicle(customer_id, make, model, year=None)` -> persists vehicle

### 9.3 Job Services (`services/jobs.py`)

- `get_job(job_id)` -> `get_or_404`
- `get_jobs_for_vehicle(vehicle_id)` -> list
- `create_job(vehicle_id, description, cost=None)` -> persists job
- `update_job_status(job, status)` -> updates and commits

### 9.4 Auth Services (`services/auth.py`)

- `login(username, password)` -> bool, performs `login_user`
- `logout()` -> calls `logout_user`

## 10. CLI Commands

Defined in `src/autoshop_crm/cli.py` and registered during app creation.

- `flask --app autoshop_crm:create_app create-db`
  - Executes `db.create_all()`.
- `flask --app autoshop_crm:create_app seed-demo-data`
  - Seeds one user + customer/vehicle/job demo tree.
  - Options:
    - `--username` (default `demo`)
    - `--password` (default `demo123`)
  - Idempotent for user and customer-email keyed records.

## 11. Templates and Frontend

Layout:
- Base nav and flash-message rendering in `templates/layouts/base.html`.

Page templates:
- Login page
- Customer list and create form
- Customer detail and create vehicle form
- Vehicle detail, create job form, update-job-status form

Styling:
- Minimal CSS in `static/css/main.css`.

## 12. Migrations and Schema Management

Alembic environment lives in `migrations/` and is integrated through Flask-Migrate.

Key files:
- `migrations/env.py`
- `migrations/alembic.ini`
- `migrations/versions/*.py`

### Important Current Risk: Model/Migration Mismatch

The active models (`Customer`, `Vehicle`, `Job`, `User`) do not match the existing migration revision `265fe6e8833b`.

Examples of mismatch:
- Migration creates `repair_orders` and `settings`, but model layer uses `jobs` and has no `settings` model.
- Migration `users` fields differ (`name/email/role/...` vs model `username/password_hash`).
- Migration columns for `customers` and `vehicles` differ from current models.

Impact:
- `flask db upgrade` may produce a schema incompatible with runtime code.
- Runtime operations may fail against a DB created solely from current migration history.

Recommended remediation path:

1. Align migration history with current models.
2. Generate a new baseline migration from the current model metadata.
3. Validate `upgrade` and `downgrade` on a clean database.
4. Only then use migration-driven setup in production.

## 13. Testing Strategy

Test suite location:
- `tests/`

Pytest config:
- `pytest.ini` sets `pythonpath = src` and `testpaths = tests`.

Fixtures (`tests/conftest.py`):
- App fixture sets:
  - `TESTING=True`
  - in-memory SQLite
  - `LOGIN_DISABLED=True`
- Creates schema before each test and drops after.

Coverage in current tests:
- Customer service creation/listing
- Job creation/status updates
- Customers route returns HTTP 200
- CLI seed command behavior and idempotency

## 14. Scripts

### 14.1 `scripts/setup.sh`

Purpose:
- Full host bootstrap for Debian/Ubuntu-like systems.

What it does:
- Requires root.
- Installs system packages.
- Starts/enables MySQL.
- Creates DB/user with generated password.
- Creates virtualenv and installs dependencies.
- Writes `.env`.
- Runs migrations.
- Optionally installs a systemd unit in production mode.

Operational caveat:
- This script is infrastructure-invasive (package install, system services, DB user creation).
- Use only on controlled hosts, not on dev workstations unless intended.

### 14.2 `scripts/backup_db.sh`

Purpose:
- MySQL backup via `mysqldump`.

Expected env vars:
- `DB_NAME`
- `DB_USER` (default `root`)
- `DB_PASSWORD`
- Optional `DB_HOST`, `DB_PORT`

Output:
- SQL dump under `/root/Autoshop-CRM/backups`.

## 15. Security Notes

Current state:
- Passwords are hashed, not stored in plaintext.
- `SECRET_KEY` has an unsafe fallback (`dev-secret-key`) if unset.

Risks to address:
- Most business routes are not protected with `@login_required`.
- No CSRF protection is implemented on forms.
- No role/authorization model beyond login existence.
- Demo user defaults are public and predictable.

Minimum production hardening checklist:
- Set strong `SECRET_KEY`.
- Remove predictable default credentials.
- Add `@login_required` to CRM data routes.
- Add CSRF protection (Flask-WTF or equivalent).
- Enforce HTTPS at reverse proxy.

## 16. Known Issues and Technical Debt

- Merge-conflict artifacts existed previously in docs/scripts; verify they remain resolved before release.
- `services/customers.py` currently defines `get_all_customers()` twice.
- Migration history does not reflect active model schema.
- `scripts/setup.sh` and `.env.example` have historically mixed MySQL driver dialects.
- Type coercion for `year` and `cost` relies on SQLAlchemy casting from form strings.

## 17. Recommended Next Engineering Steps

1. Rebuild migration baseline to match current models.
2. Add route-level auth protection for customers/vehicles/jobs.
3. Introduce CSRF validation on forms.
4. Remove duplicate function definitions and add linting.
5. Add package metadata (`pyproject.toml`) or standardized startup wrapper to remove manual `PYTHONPATH` requirement.
6. Expand tests for auth flows, validation failures, and migration compatibility.

## 18. Quick Command Reference

```zsh
# One-time shell prep
source venv/bin/activate
export PYTHONPATH="$(pwd)/src:${PYTHONPATH:-}"

# Run migrations
flask --app autoshop_crm:create_app db upgrade

# Start app
flask --app autoshop_crm:create_app run --host=0.0.0.0 --port=5000

# Seed demo data
flask --app autoshop_crm:create_app seed-demo-data

# Run tests
pytest
```

