# Reference: Environment Variables

## Who this is for
Admins and developers configuring runtime.

## Before you start
- Confirm `.env` file location.

## Step-by-step
1. Set required values:
   - `FLASK_APP=autoshop_crm:create_app`
   - `SECRET_KEY=<strong-random-value>`
   - `DATABASE_URL=<sqlalchemy-url>`
2. Optional values:
   - `FLASK_ENV` (`development` or `production`)
   - `HOST`, `PORT`, `LOG_FILE` (if used in your host scripts)
   - Update manager:
     - `UPDATE_ENABLED` (`true`/`false`, default `true`)
     - `UPDATE_REPO_PATH` (git checkout path; defaults to project root)
     - `UPDATE_REMOTE` (default `origin`)
     - `UPDATE_BRANCH` (optional; defaults to current checked-out branch)
     - `UPDATE_ALLOW_DIRTY` (`true`/`false`, default `false`)
     - `UPDATE_ROLLBACK_LIMIT` (default `6`)
     - `UPDATE_COMMAND_TIMEOUT` (seconds, default `300`)
     - `UPDATE_POST_UPDATE_COMMANDS` (comma-separated shell commands)
     - `UPDATE_POST_ROLLBACK_COMMANDS` (comma-separated shell commands)

## If this fails
- Invalid DB URL: test connection with DB client first.
- Secret key missing: app may start with weak fallback in development only.

## Done when
- All required variables are present and correct for your environment.
