# Developer Guide: Architecture

## Who this is for
Developers maintaining app internals.

## Before you start
- Read `src/autoshop_crm/app.py` for app factory wiring.
- Confirm route/service/model boundaries.

## Step-by-step
1. Routes in `src/autoshop_crm/routes/` handle HTTP and validation.
2. Services in `src/autoshop_crm/services/` hold business logic.
3. Models in `src/autoshop_crm/models/` define DB schema/relations.
4. Templates in `src/autoshop_crm/templates/` render UI.
5. Static assets in `src/autoshop_crm/static/` style the UI.

## If this fails
- Logic in routes: move behavior into service layer.
- Model side effects: isolate into service transactions.
- Template complexity: keep logic minimal and precompute in route/service.

## Done when
- Responsibility is clear at each layer.
- New features fit existing architecture.
