# Plugin System + Admin Panel Design

**Date:** 2026-04-29
**Status:** Approved

---

## Overview

An OctoPrint-style plugin system for Autoshop CRM. Plugins are Python packages that subclass a `PluginMixin` base class and contribute Flask blueprints, nav items, dashboard widgets, and settings panels. A `PluginManager` discovers, loads, and registers them at app startup. Admins install plugins from a built-in marketplace (official monorepo) or by pasting a GitHub URL.

---

## Architecture

At startup, `PluginManager.init_app(app)` is called in the app factory after all core blueprints are registered. It scans `plugins/*/plugin.json`, loads enabled plugins, registers their blueprints, and injects their contributions into Jinja globals.

```
app starts
  → PluginManager scans plugins/
  → loads enabled plugins (skips failed loads, logs errors)
  → registers Flask blueprints at /plugins/<plugin_id>/
  → adds template folders to Jinja search path
  → collects nav items, dashboard widgets, settings panels into lists
  → exposes lists as Jinja globals
```

All plugin blueprints mount under `/plugins/<plugin_id>/`. Static files are served at `/plugins/<plugin_id>/static/`. Failed plugin loads are logged and skipped — a broken plugin never crashes the app.

---

## Plugin Structure

```
plugins/
  <plugin_id>/
    plugin.json       # metadata and declared permissions
    plugin.py         # PluginMixin subclass
    templates/        # Jinja templates (optional)
    static/           # CSS/JS/assets (optional)
```

### plugin.json

```json
{
  "id": "system_monitor",
  "name": "System Monitor",
  "version": "1.0.0",
  "description": "CPU, RAM, disk, and temperature stats.",
  "author": "Autoshop CRM",
  "permissions": ["manage_plugins"],
  "declares_permissions": ["view_system_monitor"]
}
```

- `permissions` — permissions required to install/manage this plugin
- `declares_permissions` — new permissions this plugin adds to the RBAC system on install

### plugin.py

```python
from autoshop_crm.plugins import PluginMixin

class MyPlugin(PluginMixin):
    def get_blueprint(self):
        """Return a Flask Blueprint or None."""

    def get_nav_items(self):
        """Return list of dicts: [{label, url, permission, icon}]"""

    def get_dashboard_widgets(self):
        """Return list of dicts: [{template, vars, permission, order}]"""

    def get_settings_panel(self):
        """Return dict: {template, vars} or None."""

    def get_template_vars(self):
        """Return dict of vars injected into all templates."""

    def on_install(self):
        """Called once on first install."""

    def on_uninstall(self):
        """Called on removal — clean up any created resources."""
```

All hooks have default no-op implementations. Plugins override only what they use.

---

## Plugin Manager

**Location:** `src/autoshop_crm/plugins/manager.py`

**Responsibilities:**
- Scan `plugins/` at startup, validate manifests, import and instantiate mixin classes
- Track state via `PluginState` DB model (`plugin_id`, `enabled`, `settings` JSON, `installed_at`)
- Register blueprints and template folders for enabled plugins only
- Collect and expose hook contributions as Jinja globals: `plugin_nav_items`, `plugin_dashboard_widgets`, `plugin_settings_panels`
- `install_from_path(path)` — validate manifest, call `on_install()`, create `PluginState`, enable
- `install_from_url(url, plugin_path=None)` — git clone into a temp dir, copy the target subfolder (or root if no `plugin_path`) into `plugins/`, then call `install_from_path()`. Temp clone is deleted after copy.
- `uninstall(plugin_id)` — call `on_uninstall()`, delete `PluginState` row, remove folder
- `enable(plugin_id)` / `disable(plugin_id)` — toggle `PluginState.enabled`, reload contributions

**Error handling:** Any exception during plugin load is caught, logged with the plugin ID, and the plugin is marked as failed. The app continues starting normally.

---

## Permission System

Plugin permissions integrate with the existing RBAC system in `services/authorization.py`.

**New built-in permission:** `manage_plugins` — added to the `PERMISSIONS` tuple and granted to `admin` and `owner` roles by default. Required to access `/plugins` management UI.

**Plugin-declared permissions:** On install, permissions in `declares_permissions` are appended to the live `PERMISSIONS` tuple and `PERMISSION_LABELS` dict. They appear automatically in the user permissions UI. On uninstall, they are removed.

**Role grants on install:** Declared permissions are added to `admin` and `owner` role sets automatically. All other roles require manual grant by an admin via the existing permissions UI.

**Route protection:** Plugin blueprints use `@require_permission()` exactly like core routes — no new auth primitives.

---

## Admin UI

**Route:** `/plugins` — requires `manage_plugins` permission. Three tabs:

### Installed Tab
- Lists all installed plugins: name, version, description, author, status badge
- Enable/disable toggle (takes effect after reload prompt)
- Settings button — opens plugin's settings panel inline
- Uninstall button with confirmation

### Marketplace Tab
- Fetches `marketplace.json` from the official plugins GitHub repo
- Cached for 1 hour in-memory; falls back gracefully if offline
- Plugin cards: name, description, version, Install button
- Already-installed plugins show "Installed" badge

### Install from URL Tab
- Text field for a GitHub repo URL
- App clones it into `plugins/`, validates manifest, runs `on_install()`, enables it
- Progress output streamed inline (same pattern as `/updates`)

### Plugin Settings
- `/settings` gains a "Plugins" section with one tab per installed plugin that declares a settings panel
- Each tab renders the plugin's `get_settings_panel()` template
- Settings saved via `POST /plugins/<id>/settings` — manager stores to `PluginState.settings` JSON

### Nav Integration
- Plugin nav items rendered in sidebar under a "Plugins" divider
- Only shown to users with the required permission declared by the item

---

## Plugins GitHub Repo

**Repo:** `AydenForCybersec/autoshop-crm-plugins`

**Structure:**
```
autoshop-crm-plugins/
  marketplace.json       # index of all available plugins
  plugins/
    system_monitor/
    log_viewer/
    db_backup/
    shop_announcements/
    job_timer/
```

**marketplace.json format:**
```json
[
  {
    "id": "system_monitor",
    "name": "System Monitor",
    "version": "1.0.0",
    "description": "CPU, RAM, disk, and temperature stats.",
    "author": "Autoshop CRM",
    "repo_url": "https://github.com/AydenForCybersec/autoshop-crm-plugins",
    "plugin_path": "plugins/system_monitor"
  }
]
```

Expanding to individual repos later requires only updating `marketplace.json` entries to point to external repo URLs — the install flow is unchanged.

---

## Bundled Plugins

### system_monitor
- Dashboard widget: live CPU %, RAM %, disk %, Pi temperature gauges
- Full page: `/plugins/system_monitor` with sparkline history (last 60 readings, polled every 10s via JSON endpoint)
- Declares permission: `view_system_monitor`

### log_viewer
- Full page: `/plugins/log_viewer` — tails gunicorn log / journalctl output
- Live tail via JS polling, log level filter (INFO/WARNING/ERROR), download button
- Declares permission: `view_logs`

### db_backup
- Full page: `/plugins/db_backup` — manual download of SQLite DB, upload to restore
- Auto-backup: keeps last 5 copies in `backups/`, timestamp-named
- Dashboard widget: last backup time + manual backup button
- Declares permission: `manage_backups`

### shop_announcements
- Owners/admins post short announcements with optional expiry date
- Renders as a banner on the dashboard for all staff
- Per-user dismiss stored in session/cookie
- Declares permission: `manage_announcements`

### job_timer
- Start/stop timer on any open job
- Logs time entries; can auto-populate a labor line item from recorded time
- Timer visible on job detail page
- Declares permission: `use_job_timer`

---

## File Layout (new files)

```
src/autoshop_crm/plugins/
  __init__.py            # PluginMixin base class
  manager.py             # PluginManager
  models.py              # PluginState DB model

src/autoshop_crm/routes/plugins.py          # /plugins management UI routes
src/autoshop_crm/templates/plugins/
  index.html             # plugin management page (installed/marketplace/url tabs)
  _nav_items.html        # sidebar injection partial
  _dashboard_widgets.html # dashboard injection partial

plugins/                 # all installed plugins live here (gitignored except bundled)
  system_monitor/
  log_viewer/
  db_backup/
  shop_announcements/
  job_timer/
```

---

## Admin Panel

A new `/admin` section, gated by the `admin` role (not just a permission — role check directly). Consolidates all dangerous/privileged operations away from the general settings page.

### Navigation
- Admin-only sidebar section (or top-level nav item labeled "Admin") visible only to users with `role == "admin"`
- Existing `/settings` retains branding, theme, and shop info (accessible to owners too)
- `/updates` and user management move under `/admin`

### Admin Panel Sections

**Overview** (`/admin`) — summary cards: active users, installed plugins, last update check, last backup, any failed plugin loads.

**Users & Permissions** (`/admin/users`) — moved from wherever it currently lives. Create/edit/deactivate users, assign roles, set per-user permission overrides.

**Plugins** (`/admin/plugins`) — full plugin management UI (marketplace, install from URL, enable/disable, uninstall, per-plugin settings).

**Updates** (`/admin/updates`) — redesigned update UI:
- Clear current version badge and "Check for updates" button
- If update available: changelog rendered as markdown, version diff highlighted
- Progress shown as a live step-by-step log (polling), not a raw terminal dump
- Steps labeled: "Pulling code", "Running migrations", "Restarting service" with pass/fail indicators
- After restart, auto-reconnect polling — page shows "Reconnecting..." then reloads when app is back up

**Danger Zone** (`/admin/danger`) — destructive operations grouped in a clearly styled red-bordered section:
- **Clear all data** — drops and recreates all tables (requires typing `DELETE EVERYTHING` to confirm)
- **Reset to defaults** — wipes settings/branding back to factory defaults
- **Uninstall all plugins** — removes all plugins at once
- **Export database** — download raw SQLite file (also available in db_backup plugin but surfaced here too)
- Each action requires an explicit typed confirmation phrase, shown inline with a red warning banner explaining consequences

### Existing `/settings` After Move
Retains: shop name, logo, branding colors, invoice rates, labor rates. Accessible to owners and admins. All dangerous ops removed.

### New Permission
`access_admin_panel` — added to `PERMISSIONS`, granted only to `admin` role. Used as the gate for all `/admin/*` routes in addition to the role check (defense in depth).

---

## Integration Points in Existing Code

| File | Change |
|------|--------|
| `app.py` | Add `plugin_manager.init_app(app)`, register `admin_bp` |
| `services/authorization.py` | Add `manage_plugins`, `access_admin_panel` to `PERMISSIONS` and role sets |
| `templates/layouts/base.html` | Loop `plugin_nav_items` in sidebar; add admin nav section |
| `templates/dashboard/index.html` | Loop `plugin_dashboard_widgets` |
| `templates/settings/index.html` | Remove dangerous ops; loop `plugin_settings_panels` |
| `routes/updates.py` | Move to `routes/admin/updates.py`, redesign UI |
| `requirements.txt` | Add `psutil` (system monitor), `gitpython` (install from URL) |
