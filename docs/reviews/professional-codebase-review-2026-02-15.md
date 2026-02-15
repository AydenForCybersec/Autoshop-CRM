# Professional Codebase Review: Autoshop CRM

- Review date: February 15, 2026
- Reviewer mode: Repository-based technical assessment (code, tests, docs, scripts)
- Primary weighting: Product + Usability
- Secondary weighting: Security, reliability, and operational safety

## 1. Executive Overview

Autoshop CRM is a server-rendered Flask application for independent auto shop operations: customer records, vehicle history, work orders, accounting snapshots, role-based access control (RBAC), first-run admin setup, in-app help center, and a git-backed update console.

Current maturity: **Early production-capable for small teams**, with good functional coverage and clear layer separation, but with several high-risk guardrail gaps before broad production rollout.

Readiness status for real shop operations:
- Core workflows are present and coherent end-to-end.
- Test suite passes cleanly (`33 passed`) with broad behavior checks.
- Usability is generally clear for day-to-day use, especially customer -> vehicle -> job flow.
- Security hardening is incomplete for an internet-exposed deployment (notably CSRF and update-surface risk).
- Ops tooling/docs are directionally helpful but have production-safety inconsistencies.

## 2. System Overview

### Architecture map

- App composition is centralized in an application factory with blueprints for each domain area (`src/autoshop_crm/app.py:27`).
- Layering is mostly clean:
- HTTP routing and request parsing in `src/autoshop_crm/routes/`.
- Business/data behavior in `src/autoshop_crm/services/`.
- Persistence in SQLAlchemy models under `src/autoshop_crm/models/`.
- UI in Jinja templates + a single main stylesheet.
- Authentication is enforced globally in `before_request` with first-run bootstrap logic (`src/autoshop_crm/app.py:99`).
- Authorization is permission-based with route decorators (`src/autoshop_crm/services/authorization.py:138`).

### Data flow snapshot

1. Request enters route handler.
2. Route validates/normalizes form data.
3. Service writes through SQLAlchemy session and commits.
4. Route redirects to canonical page and uses flash messaging for user feedback.

### Deployment model

- Config-driven environment setup (`src/autoshop_crm/config.py:33`).
- Migration-backed schema management via Flask-Migrate/Alembic.
- Includes a privileged setup helper script for host bootstrap (`scripts/setup.sh:1`).
- Includes in-app git update/rollback manager via admin UI (`src/autoshop_crm/routes/updates.py:31`).

### Functional map

- First-run onboarding: `/setup-admin` -> creates first admin and shop profile.
- Auth lifecycle: `/login`, `/logout`.
- Ops workflow: `/customers/` -> customer profile -> add vehicles -> add jobs.
- Financial reporting: `/accounting/` with date filters and CSV export.
- Governance: `/settings` for business profile, theme, users, and permission overrides.
- In-app support: `/help` articles from curated markdown.
- Maintenance: `/updates` for git fetch/apply/rollback.

## 3. Usability Assessment (Primary)

### Strengths

- Clear information hierarchy and consistent visual language across screens (`src/autoshop_crm/templates/layouts/base.html:39`, `src/autoshop_crm/static/css/main.css:1`).
- Workflow continuity is strong for service-desk operations (customer -> vehicle -> job creation).
- Duplicate detection flows reduce accidental data proliferation (`src/autoshop_crm/routes/customers.py:57`, `src/autoshop_crm/routes/vehicles.py:60`).
- Settings tab model is understandable and segmented by admin task area (`src/autoshop_crm/templates/settings/index.html:13`).
- Mobile breakpoints exist and adapt major two-column layouts (`src/autoshop_crm/static/css/main.css:735`).

### Usability friction points

- Customer directory lacks search/filter/sort controls, increasing retrieval time at scale (`src/autoshop_crm/templates/customers/list.html:19`).
- Several views emphasize IDs instead of human-friendly references (for example, vehicle and accounting rows), reducing operator readability (`src/autoshop_crm/templates/vehicles/detail.html:10`, `src/autoshop_crm/templates/accounting/index.html:48`).
- Flash messaging has one visual severity treatment (red/error-like) for all outcomes, including success states (`src/autoshop_crm/static/css/main.css:521`).
- Post-login ignores original destination (`next`), forcing context loss for users arriving from protected deep links (`src/autoshop_crm/services/authorization.py:151`, `src/autoshop_crm/routes/auth.py:33`).
- Update actions (apply/rollback) are high-impact with no confirmation barrier in the UI (`src/autoshop_crm/templates/updates/index.html:56`).

## 4. Engineering Quality Assessment

### Security

- CSRF protection is not wired despite many mutating POST endpoints and forms.
- No `CSRFProtect` extension in app init (`src/autoshop_crm/extensions.py:1`, `src/autoshop_crm/app.py:35`).
- Multiple mutating forms submit without CSRF token fields (`src/autoshop_crm/templates/settings/index.html:21`, `src/autoshop_crm/templates/customers/list.html:41`, `src/autoshop_crm/templates/updates/index.html:52`).
- Secret key has unsafe fallback (`dev-secret-key`) in code (`src/autoshop_crm/config.py:36`).
- Brute-force protection and login throttling are not present in auth path (`src/autoshop_crm/routes/auth.py:26`).
- In-app updater can execute configured shell commands and hard reset git state; this is high-privilege behavior surfaced via web UI (`src/autoshop_crm/services/updater.py:212`, `src/autoshop_crm/services/updater.py:171`).

### Reliability and data integrity

- Job status updates accept arbitrary strings from form payload and persist directly (`src/autoshop_crm/routes/jobs.py:52`, `src/autoshop_crm/services/jobs.py:44`).
- Service writes commit directly without centralized transaction/error handling; uniqueness collisions can leak as 500s (example: customer email uniqueness at model level + direct commit) (`src/autoshop_crm/models/customer.py:18`, `src/autoshop_crm/services/customers.py:56`).
- Date/time usage relies on `datetime.utcnow()` across model/service/report flows, already surfacing deprecation warnings under Python 3.14 test runs.

### Maintainability

- Architecture and naming are mostly consistent and approachable for contributors.
- Permission matrix docs drift from code by omitting `manage_updates` permission (`src/autoshop_crm/services/authorization.py:28`, `docs/reference/permission-matrix.md:13`).
- Docs index contains an inconsistent link style (`[[docs/user-guide/]]`) that differs from the rest of docs and may break some renderers (`docs/index.md:13`).
- Legacy/duplicate deprecated doc stubs remain in top-level docs, increasing navigation noise (`docs/setup.md:1`, `docs/deployment.md:1`, `docs/architecture.md:1`).

### Operational readiness

- Setup automation script is powerful but unsafe for modern production defaults:
- requires root and configures service to run as root (`scripts/setup.sh:16`, `scripts/setup.sh:173`).
- uses Flask dev server as long-running production service (`scripts/setup.sh:177`).
- writes generated DB credentials to stdout at end (`scripts/setup.sh:199`).
- Test baseline is strong but skewed toward `LOGIN_DISABLED=True` in common fixtures, reducing auth/permission regression sensitivity (`tests/conftest.py:17`).

## 5. Findings Register (Severity-Ordered)

## Critical

### F-01: Missing CSRF protections on mutating routes
- Impacted workflow: Settings changes, user management, updates, customer/vehicle/job writes.
- Technical cause: No CSRF middleware/token validation wired into app/forms.
- User/business impact: Cross-site request forgery could trigger unauthorized operational and administrative actions in authenticated sessions.
- Evidence: `src/autoshop_crm/extensions.py:1`, `src/autoshop_crm/app.py:35`, `src/autoshop_crm/templates/settings/index.html:21`, `src/autoshop_crm/templates/updates/index.html:52`.
- Recommended fix direction: Add `CSRFProtect`, migrate mutating forms to Flask-WTF or inject/validate CSRF token globally, and add negative CSRF tests for all POST endpoints.

## High

### F-02: In-app update console exposes high-impact git and shell operations
- Impacted workflow: Maintenance and release updates.
- Technical cause: Admin web route triggers `git merge/reset` and optional shell commands.
- User/business impact: Any admin session compromise or misconfiguration can lead to code execution/state corruption.
- Evidence: `src/autoshop_crm/routes/updates.py:31`, `src/autoshop_crm/services/updater.py:171`, `src/autoshop_crm/services/updater.py:212`.
- Recommended fix direction: Disable by default in production, gate behind explicit env + network restrictions, add second-factor/confirm step, and restrict/whitelist post commands.

### F-03: Production setup script runs service as root with dev server
- Impacted workflow: Deployment and operations.
- Technical cause: Automated service unit uses `User=root` and `flask run`.
- User/business impact: Expanded blast radius for compromise and weak production serving characteristics.
- Evidence: `scripts/setup.sh:173`, `scripts/setup.sh:177`.
- Recommended fix direction: Replace with non-root dedicated service user + Gunicorn/Uvicorn process model + reverse proxy template.

### F-04: Authentication hardening gaps (rate limiting/lockout)
- Impacted workflow: Login.
- Technical cause: Direct password checks with no throttle/backoff/captcha.
- User/business impact: Increased brute-force risk on exposed instances.
- Evidence: `src/autoshop_crm/routes/auth.py:26`.
- Recommended fix direction: Add IP/user-based throttling, lockout policy, and audit logging for failed attempts.

## Medium

### F-05: Job status accepts unvalidated free-form values
- Impacted workflow: Work order lifecycle and dashboard/accounting accuracy.
- Technical cause: Request value persisted directly without enum validation.
- User/business impact: Inconsistent status taxonomy and reporting drift.
- Evidence: `src/autoshop_crm/routes/jobs.py:52`, `src/autoshop_crm/services/jobs.py:46`.
- Recommended fix direction: Enforce allowed status enum at route and model levels; reject unknown states.

### F-06: Post-login deep-link intent is dropped
- Impacted workflow: Permission redirects, direct links from docs/bookmarks.
- Technical cause: `next` parameter added by permission decorator but ignored by login handler.
- User/business impact: Friction and extra navigation for users.
- Evidence: `src/autoshop_crm/services/authorization.py:151`, `src/autoshop_crm/routes/auth.py:33`.
- Recommended fix direction: Honor safe local `next` target in login success flow.

### F-07: Directory usability degrades with scale (no search/filter)
- Impacted workflow: Front-desk customer lookup.
- Technical cause: Paginated list only, no filtering controls.
- User/business impact: Slower retrieval and increased handling time on busy shops.
- Evidence: `src/autoshop_crm/templates/customers/list.html:19`.
- Recommended fix direction: Add indexed search (name/email/phone), quick filters, and keyboard-first navigation.

### F-08: Success and error flashes share error-like styling
- Impacted workflow: All form submissions.
- Technical cause: Single red flash treatment for all messages.
- User/business impact: Ambiguous feedback and confidence erosion after successful actions.
- Evidence: `src/autoshop_crm/templates/layouts/base.html:70`, `src/autoshop_crm/static/css/main.css:521`.
- Recommended fix direction: Add categorized flash levels (`success`, `warning`, `error`, `info`) and matching styles.

### F-09: Docs/code permission drift (`manage_updates` missing in matrix)
- Impacted workflow: Admin governance and audits.
- Technical cause: Reference docs not updated with new permission constant.
- User/business impact: Misconfigured role expectations and approval mistakes.
- Evidence: `src/autoshop_crm/services/authorization.py:28`, `docs/reference/permission-matrix.md:13`.
- Recommended fix direction: Regenerate permission docs from source constants or add CI doc-consistency check.

### F-10: Deprecated doc stubs and inconsistent link syntax add navigation noise
- Impacted workflow: Onboarding and contributor ramp-up.
- Technical cause: Multiple deprecated pages retained + mixed link formats.
- User/business impact: Slower doc discovery and trust reduction.
- Evidence: `docs/setup.md:1`, `docs/deployment.md:1`, `docs/architecture.md:1`, `docs/index.md:13`.
- Recommended fix direction: Consolidate deprecated stubs into one migration note and normalize markdown links.

### F-11: Naive UTC APIs trigger warnings and future compatibility risk
- Impacted workflow: Timestamps in customers/vehicles/jobs/reports.
- Technical cause: `datetime.utcnow()` usage across service/report code.
- User/business impact: Pending runtime breakage risk in future Python/SQLAlchemy upgrades.
- Evidence: `src/autoshop_crm/services/customers.py:55`, `src/autoshop_crm/services/vehicles.py:78`, `src/autoshop_crm/services/jobs.py:37`, `src/autoshop_crm/services/reports.py:19`.
- Recommended fix direction: Migrate to timezone-aware UTC (`datetime.now(datetime.UTC)`), standardize serialization and DB handling.

### F-12: Core tests often bypass authentication by default
- Impacted workflow: Release confidence for auth/RBAC regressions.
- Technical cause: Base fixture sets `LOGIN_DISABLED=True` for most tests.
- User/business impact: Security-relevant regressions can slip through broader suite.
- Evidence: `tests/conftest.py:17`.
- Recommended fix direction: Keep fast unit tests, but add mandatory auth-on integration suite for protected routes.

## 6. Test and Validation Results

### Automated baseline (executed)

Command:
- `./.venv/bin/pytest -q`

Result:
- `33 passed, 70 warnings in 4.07s`

Signal quality:
- Pass rate is strong.
- Warning profile indicates technical debt in datetime and legacy ORM access patterns that should be scheduled for cleanup.

### Top user journeys validated via route/template and test-path inspection

- First-run setup and forced redirect behavior: covered by route logic and tests (`src/autoshop_crm/routes/auth.py:48`, `tests/test_auth_setup.py:34`).
- Login/logout flow: present and tested (`src/autoshop_crm/routes/auth.py:17`, `tests/test_rbac.py:43`).
- Customer -> vehicle -> job flow with duplicates/backdating/reporting: implemented and tested (`tests/test_duplicates_and_reports.py:9`).
- Accounting filters/export: implemented and tested (`src/autoshop_crm/routes/accounting.py:44`, `tests/test_duplicates_and_reports.py:90`).
- Permission gating: implemented and tested (`src/autoshop_crm/services/authorization.py:138`, `tests/test_rbac.py:56`, `tests/test_updates.py:158`).
- Update UI safety: route behavior tested with fake manager (`tests/test_updates.py:70`).

### Missing/weak automated coverage mapped to major findings

- F-01 CSRF: no tests asserting token rejection.
- F-02 updater hardening: no tests for production-disable policy or restricted command policy.
- F-04 auth throttling: no lockout/rate-limit tests (feature absent).
- F-05 job status enum: no negative tests for invalid statuses.
- F-06 login `next`: no redirect-intent preservation test.
- F-07 customer search/filter: no UX or query-level tests (feature absent).
- F-08 flash categories: no tests for message levels.
- F-09/F-10 docs consistency: no docs lint/link validation checks.

## 7. Action Roadmap

### 0-2 weeks (high-risk guardrails)

1. Add CSRF protection across all mutating endpoints.
- Effort: Medium.
- Dependencies: None.
- Acceptance check: POST without valid token returns 400; legitimate forms still pass.

2. Lock down update manager for production.
- Effort: Medium.
- Dependencies: Deployment config policy.
- Acceptance check: update UI disabled unless explicit secure flag; post-command whitelist enforced.

3. Replace root/dev-server production path in setup guidance.
- Effort: Medium.
- Dependencies: deployment docs and service template.
- Acceptance check: documented/systemd path uses dedicated service account + Gunicorn.

4. Add auth throttling and failed-login audit events.
- Effort: Medium.
- Dependencies: persistence/logging decision.
- Acceptance check: repeated failed attempts trigger backoff/lockout; tests verify behavior.

### 2-6 weeks (usability and workflow improvements)

1. Add customer search/filter and quick action ergonomics.
- Effort: Medium.
- Dependencies: DB indexing for query targets.
- Acceptance check: find customer by name/email/phone within 2 interactions.

2. Implement safe `next` redirect handling after login.
- Effort: Low.
- Dependencies: URL safety helper.
- Acceptance check: deep-link login returns user to intended page.

3. Add typed flash levels and UI styling.
- Effort: Low.
- Dependencies: template flash rendering update.
- Acceptance check: success/error/warning/info are visually distinct and semantically mapped.

4. Validate job status as strict enum.
- Effort: Low.
- Dependencies: shared status constants.
- Acceptance check: invalid status rejected with clear message; metrics remain consistent.

### 6+ weeks (hardening and long-term maintainability)

1. Standardize timezone-aware datetime handling and remove deprecation warnings.
- Effort: Medium.
- Dependencies: model/service/date helper alignment.
- Acceptance check: test suite warning count materially reduced and datetime policy documented.

2. Introduce transaction-safe service boundaries for writes.
- Effort: Medium.
- Dependencies: error mapping conventions.
- Acceptance check: user-friendly conflict handling for uniqueness/DB errors.

3. Add docs and policy consistency automation.
- Effort: Low.
- Dependencies: CI workflow additions.
- Acceptance check: permission matrix and link integrity validated in CI.

## 8. Public APIs / Interfaces / Types

No public API/interface/type changes were made in this review phase.

## 9. Assumptions and Defaults Applied

- Focus weighting is Product + Usability first.
- Assessment is repository-based and non-invasive (no runtime data mutation beyond read-only checks and tests).
- Recommendations prioritize minimizing operational risk before feature expansion.
