# Reference: Environment Variables

## Who this is for
Admins and developers configuring runtime.

## Before you start
- Confirm `.env` file location.

## Step-by-step
1. Set required values:
   - `FLASK_APP=autoshop_crm:create_app`
   - `FLASK_ENV=production` for production hosts
   - `SECRET_KEY=<strong-random-value>`
   - `DATABASE_URL=<sqlalchemy-url>`
2. Optional values:
   - `FLASK_ENV` (`development` or `production`)
   - `HOST`, `PORT`, `LOG_FILE` (if used in your host scripts)
   - Session/security:
     - `SESSION_COOKIE_SECURE` (default `true` in production)
     - `REMEMBER_COOKIE_SECURE` (default `true` in production)
     - `SESSION_COOKIE_SAMESITE` (default `Lax`)
     - `REMEMBER_COOKIE_SAMESITE` (default `Lax`)
     - `PREFERRED_URL_SCHEME` (default `https` in production)
     - `MAX_CONTENT_LENGTH` (bytes; default `8388608`)
   - Update manager:
     - `UPDATE_ENABLED` (`true`/`false`, default `false` in production; `true` in development)
     - `UPDATE_REPO_PATH` (git checkout path; defaults to project root)
     - `UPDATE_REMOTE` (default `origin`)
     - `UPDATE_BRANCH` (optional; defaults to current checked-out branch)
     - `UPDATE_LOCAL_ONLY` (`true`/`false`, default `true`; restrict updates page to local requests)
     - `UPDATE_CONFIRM_PHRASE` (required phrase for apply/rollback actions, default `CONFIRM`)
     - `UPDATE_ALLOW_DIRTY` (`true`/`false`, default `false`)
     - `UPDATE_ROLLBACK_LIMIT` (default `6`)
     - `UPDATE_COMMAND_TIMEOUT` (seconds, default `300`)
     - `UPDATE_POST_UPDATE_COMMANDS` (comma-separated commands)
     - `UPDATE_POST_ROLLBACK_COMMANDS` (comma-separated commands)
     - `UPDATE_ALLOWED_COMMAND_PREFIXES` (comma-separated allowed command prefixes for post commands)
   - Login throttling:
     - `AUTH_MAX_ATTEMPTS` (default `5`)
     - `AUTH_WINDOW_SECONDS` (default `300`)
     - `AUTH_LOCKOUT_SECONDS` (default `900`)

## If this fails
- Invalid DB URL: test connection with DB client first.
- Production secret key errors: set `SECRET_KEY` to a non-placeholder value (for example not `change-me-in-production`).

## Done when
- All required variables are present and correct for your environment.
