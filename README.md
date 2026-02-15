# Autoshop CRM

Autoshop CRM is a shop management app for customer records, vehicle history, work orders, and day-to-day service operations.

## Start Here

- Non-technical staff/admin usage: open in-app Help Center at `/help`
- Developers and technical operators: `docs/developer-guide/local-development.md`
- Technical docs map: `docs/index.md`

## Quick Run

```zsh
python scripts/autoshopctl.py setup --mode dev
flask --app run.py run --host=0.0.0.0 --port=5000
```

## In-App Help Center

When the server is running, authenticated users can open:

- `GET /help` for Help home
- `GET /help/<slug>` for help articles

The in-app Help content is curated from repository documentation and is designed for non-technical users.
Repository `/docs` content is reserved for command-line, deployment, and file-modification documentation.

## Testing

```zsh
pytest
```

## License

This project is licensed under the GNU Affero General Public License v3.0 (`AGPL-3.0-only`).
See `LICENSE` for the full text.
Copyright and original authorship are recorded in `COPYRIGHT`.

If you distribute or modify this software, you must preserve copyright and license notices,
and provide source code under AGPLv3 terms.
