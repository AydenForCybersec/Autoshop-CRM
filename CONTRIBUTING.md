# Contributing

## Documentation Changes
- Follow `docs/policies/doc-writing-style.md`.
- Keep `/docs` limited to technical workflows (CLI usage, deployment, file/config edits).
- Keep end-user app workflows in `src/autoshop_crm/help_content/` and surface them via `/help`.
- Update `docs/index.md` when adding or moving docs.
- If workflow changes are non-technical, update Help content first and avoid duplicating in `/docs`.

## Code Changes
- Keep route/business/model boundaries consistent with `docs/developer-guide/architecture.md`.
- Add tests for new routes/services and permission behavior.
