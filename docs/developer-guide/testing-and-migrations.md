# Developer Guide: Testing and Migrations

## Who this is for
Developers changing behavior or schema.

## Before you start
- Local environment is configured.
- You know whether your change affects data model.

## Step-by-step
1. Run full tests:
   `pytest`
2. If schema changed, create migration:
   `flask --app autoshop_crm:create_app db migrate -m "describe change"`
3. Apply migration:
   `flask --app autoshop_crm:create_app db upgrade`
4. Re-run tests.
5. Review migration for safety before commit.

## If this fails
- Migration drift: inspect `migrations/versions/` for conflicts.
- Test failures: reproduce with narrowed test target first.
- SQLite/MySQL behavior mismatch: validate against target DB backend.

## Done when
- Tests pass.
- Migration applies cleanly on fresh and existing databases.
