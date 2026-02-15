# Architecture Overview

This project follows a layered Flask architecture:

## Layers

### Routes
- Handle HTTP requests
- No business logic
- Call services

### Services
- Business rules
- Database transactions
- Reusable logic

### Models
- Database schema
- Relationships only

## Why This Matters

- Easier testing
- Safer refactoring
- Clear ownership of logic

## App Factory and Wiring

- `src/autoshop_crm/app.py` builds the app in `create_app()`.
- Config class is selected by `FLASK_ENV` via `src/autoshop_crm/config.py`.
- Extensions are initialized in this order:
  - `db` (`Flask-SQLAlchemy`)
  - `migrate` (`Flask-Migrate`)
  - `login_manager` (`Flask-Login`)
- Blueprints are registered for:
  - Auth (`/login`, `/logout`)
  - Customers (`/customers`)
  - Vehicles (`/vehicles`)
  - Jobs (`/jobs`)

## Data Ownership

- `Customer` owns many `Vehicle` records.
- `Vehicle` owns many `Job` records.
- `User` is used for login/authentication.

For complete route/service/model breakdown, see `docs/developer-guide.md`.
