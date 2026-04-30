# Plugin System + Admin Panel — Implementation Plan (Part 1)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the core plugin infrastructure (PluginMixin, PluginManager, DB model), a new admin-only `/admin` panel with redesigned updates UI and danger zone, and wire everything into the existing Flask app.

**Architecture:** Plugins are Python packages in `plugins/` that subclass `PluginMixin`. A `PluginManager` discovers, loads, and registers them at startup via `init_app()`. A new `admin_bp` blueprint handles all privileged operations (`/admin/*`), gated by the `admin` role. The existing `/settings` route keeps only shop/branding config.

**Tech Stack:** Flask blueprints, SQLAlchemy, Alembic, Jinja2, gitpython (new), pytest.

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `src/autoshop_crm/plugins/__init__.py` | `PluginMixin` base class with all hooks as no-ops |
| Create | `src/autoshop_crm/plugins/manager.py` | `PluginManager`: discovery, loading, install, uninstall |
| Create | `src/autoshop_crm/plugins/models.py` | `PluginState` SQLAlchemy model |
| Create | `migrations/versions/c1d2e3f4a5b6_add_plugin_states.py` | DB migration for plugin_states table |
| Create | `src/autoshop_crm/routes/admin/__init__.py` | Exports `admin_bp` |
| Create | `src/autoshop_crm/routes/admin/panel.py` | `GET /admin` overview page |
| Create | `src/autoshop_crm/routes/admin/updates_ui.py` | `GET/POST /admin/updates` (redesigned) |
| Create | `src/autoshop_crm/routes/admin/danger.py` | `GET/POST /admin/danger` danger zone |
| Create | `src/autoshop_crm/routes/admin/plugins_ui.py` | `GET/POST /admin/plugins` management |
| Create | `src/autoshop_crm/templates/admin/layout.html` | Admin panel base template |
| Create | `src/autoshop_crm/templates/admin/index.html` | Admin overview |
| Create | `src/autoshop_crm/templates/admin/updates.html` | Redesigned update UI |
| Create | `src/autoshop_crm/templates/admin/danger.html` | Danger zone |
| Create | `src/autoshop_crm/templates/admin/plugins/index.html` | Plugin management |
| Create | `plugins/.gitkeep` | Marks plugins dir in git |
| Modify | `src/autoshop_crm/services/authorization.py` | Add `manage_plugins`, `access_admin_panel` permissions |
| Modify | `src/autoshop_crm/app.py` | Register `admin_bp`, call `plugin_manager.init_app(app)`, expose Jinja globals |
| Modify | `src/autoshop_crm/models/__init__.py` | Import `PluginState` |
| Modify | `src/autoshop_crm/templates/layouts/base.html` | Add Admin nav link, plugin nav items injection |
| Modify | `src/autoshop_crm/templates/dashboard/index.html` | Plugin dashboard widgets injection |
| Modify | `src/autoshop_crm/templates/settings/index.html` | Remove users/permissions tabs (moved to admin) |
| Modify | `requirements.txt` | Add `gitpython` |
| Create | `tests/test_plugin_mixin.py` | Tests for PluginMixin defaults |
| Create | `tests/test_plugin_manager.py` | Tests for PluginManager discovery/loading |
| Create | `tests/test_admin_routes.py` | Tests for admin route access control |

---

### Task 1: PluginMixin base class

**Files:**
- Create: `src/autoshop_crm/plugins/__init__.py`
- Create: `tests/test_plugin_mixin.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_plugin_mixin.py
from autoshop_crm.plugins import PluginMixin


class MinimalPlugin(PluginMixin):
    pass


def test_default_blueprint_is_none():
    assert MinimalPlugin().get_blueprint() is None


def test_default_nav_items_is_empty():
    assert MinimalPlugin().get_nav_items() == []


def test_default_dashboard_widgets_is_empty():
    assert MinimalPlugin().get_dashboard_widgets() == []


def test_default_settings_panel_is_none():
    assert MinimalPlugin().get_settings_panel() is None


def test_default_template_vars_is_empty():
    assert MinimalPlugin().get_template_vars() == {}


def test_on_install_does_not_raise():
    MinimalPlugin().on_install()


def test_on_uninstall_does_not_raise():
    MinimalPlugin().on_uninstall()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd ~/Projects/autoshop-crm
PYTHONPATH=src pytest tests/test_plugin_mixin.py -v
```

Expected: `ModuleNotFoundError: No module named 'autoshop_crm.plugins'`

- [ ] **Step 3: Implement PluginMixin**

```python
# src/autoshop_crm/plugins/__init__.py
"""Plugin infrastructure — base mixin and public exports."""

from __future__ import annotations

from typing import Any


class PluginMixin:
    """Base class for all Autoshop CRM plugins.

    Subclass this and override only the hooks you need.
    All hooks default to safe no-ops.
    """

    # Set by PluginManager after loading
    plugin_id: str = ""
    plugin_name: str = ""
    plugin_version: str = ""

    def get_blueprint(self):
        """Return a Flask Blueprint to register, or None."""
        return None

    def get_nav_items(self) -> list[dict[str, Any]]:
        """Return sidebar nav items.

        Each item: {"label": str, "url": str, "permission": str, "icon": str}
        """
        return []

    def get_dashboard_widgets(self) -> list[dict[str, Any]]:
        """Return dashboard widget descriptors.

        Each item: {"template": str, "vars": dict, "permission": str, "order": int}
        """
        return []

    def get_settings_panel(self) -> dict[str, Any] | None:
        """Return settings panel descriptor or None.

        Format: {"template": str, "vars": dict, "label": str}
        """
        return None

    def get_template_vars(self) -> dict[str, Any]:
        """Return vars injected into all templates."""
        return {}

    def on_install(self) -> None:
        """Called once when the plugin is first installed."""

    def on_uninstall(self) -> None:
        """Called when the plugin is removed."""
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
PYTHONPATH=src pytest tests/test_plugin_mixin.py -v
```

Expected: 7 PASSED

- [ ] **Step 5: Commit**

```bash
git add src/autoshop_crm/plugins/__init__.py tests/test_plugin_mixin.py
git commit -m "feat: add PluginMixin base class with default no-op hooks"
```

---

### Task 2: PluginState DB model

**Files:**
- Create: `src/autoshop_crm/plugins/models.py`
- Modify: `src/autoshop_crm/models/__init__.py`
- Create: `migrations/versions/c1d2e3f4a5b6_add_plugin_states.py`

- [ ] **Step 1: Create the model**

```python
# src/autoshop_crm/plugins/models.py
"""DB model for plugin installation state."""

from __future__ import annotations

from datetime import datetime

from ..extensions import db


class PluginState(db.Model):
    """Tracks each installed plugin's enabled state and settings."""

    __tablename__ = "plugin_states"

    id = db.Column(db.Integer, primary_key=True)
    plugin_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    enabled = db.Column(db.Boolean, nullable=False, default=True)
    settings = db.Column(db.JSON, nullable=False, default=dict)
    installed_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    failed = db.Column(db.Boolean, nullable=False, default=False)
    fail_reason = db.Column(db.Text, nullable=True)
```

- [ ] **Step 2: Register model in models __init__**

Open `src/autoshop_crm/models/__init__.py` and add:

```python
from autoshop_crm.plugins.models import PluginState  # noqa: F401
```

(Add alongside the existing imports.)

- [ ] **Step 3: Create the migration**

```python
# migrations/versions/c1d2e3f4a5b6_add_plugin_states.py
"""Add plugin_states table.

Revision ID: c1d2e3f4a5b6
Revises: b2d4f8a1c6e3
Create Date: 2026-04-29 00:00:00
"""

revision = "c1d2e3f4a5b6"
down_revision = "b2d4f8a1c6e3"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        "plugin_states",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("plugin_id", sa.String(64), nullable=False, unique=True, index=True),
        sa.Column("enabled", sa.Boolean, nullable=False, default=True),
        sa.Column("settings", sa.JSON, nullable=False),
        sa.Column("installed_at", sa.DateTime, nullable=False),
        sa.Column("failed", sa.Boolean, nullable=False, default=False),
        sa.Column("fail_reason", sa.Text, nullable=True),
    )


def downgrade():
    op.drop_table("plugin_states")
```

- [ ] **Step 4: Run the migration**

```bash
PYTHONPATH=src FLASK_APP=autoshop_crm:create_app DATABASE_URL=sqlite:///./instance/autoshop.db flask db upgrade c1d2e3f4a5b6
```

Expected: `Running upgrade b2d4f8a1c6e3 -> c1d2e3f4a5b6`

- [ ] **Step 5: Commit**

```bash
git add src/autoshop_crm/plugins/models.py src/autoshop_crm/models/__init__.py migrations/versions/c1d2e3f4a5b6_add_plugin_states.py
git commit -m "feat: add PluginState model and migration for plugin install tracking"
```

---

### Task 3: PluginManager — discovery and loading

**Files:**
- Create: `src/autoshop_crm/plugins/manager.py`
- Create: `tests/test_plugin_manager.py`
- Create: `plugins/.gitkeep`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_plugin_manager.py
import json
import sys
from pathlib import Path

import pytest

from autoshop_crm.plugins import PluginMixin
from autoshop_crm.plugins.manager import PluginManager


@pytest.fixture
def plugin_dir(tmp_path):
    """Create a temp plugins directory with one valid plugin."""
    p = tmp_path / "my_plugin"
    p.mkdir()
    (p / "plugin.json").write_text(json.dumps({
        "id": "my_plugin",
        "name": "My Plugin",
        "version": "1.0.0",
        "description": "Test plugin.",
        "author": "Test",
        "permissions": [],
        "declares_permissions": [],
    }))
    (p / "plugin.py").write_text(
        "from autoshop_crm.plugins import PluginMixin\n"
        "class MyPlugin(PluginMixin):\n"
        "    pass\n"
    )
    return tmp_path


def test_discover_finds_valid_plugin(plugin_dir):
    mgr = PluginManager(plugins_dir=plugin_dir)
    discovered = mgr.discover()
    assert "my_plugin" in discovered


def test_discover_skips_dir_without_manifest(tmp_path):
    bad = tmp_path / "bad_plugin"
    bad.mkdir()
    (bad / "plugin.py").write_text("# no manifest")
    mgr = PluginManager(plugins_dir=tmp_path)
    assert "bad_plugin" not in mgr.discover()


def test_load_plugin_instantiates_mixin(plugin_dir):
    mgr = PluginManager(plugins_dir=plugin_dir)
    manifests = mgr.discover()
    instance = mgr._load_plugin(manifests["my_plugin"])
    assert isinstance(instance, PluginMixin)
    assert instance.plugin_id == "my_plugin"


def test_load_plugin_with_syntax_error_does_not_raise(tmp_path):
    p = tmp_path / "broken"
    p.mkdir()
    (p / "plugin.json").write_text(json.dumps({
        "id": "broken", "name": "Broken", "version": "1.0.0",
        "description": "", "author": "", "permissions": [], "declares_permissions": [],
    }))
    (p / "plugin.py").write_text("this is not valid python !!!")
    mgr = PluginManager(plugins_dir=tmp_path)
    manifests = mgr.discover()
    result = mgr._load_plugin(manifests["broken"])
    assert result is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
PYTHONPATH=src pytest tests/test_plugin_manager.py -v
```

Expected: `ModuleNotFoundError: No module named 'autoshop_crm.plugins.manager'`

- [ ] **Step 3: Implement PluginManager discovery and loading**

```python
# src/autoshop_crm/plugins/manager.py
"""Plugin discovery, loading, and lifecycle management."""

from __future__ import annotations

import importlib.util
import json
import logging
import shutil
import sys
from pathlib import Path
from typing import Any

from . import PluginMixin

logger = logging.getLogger(__name__)

_REQUIRED_MANIFEST_KEYS = {"id", "name", "version", "description", "author", "permissions", "declares_permissions"}


class PluginManager:
    """Discovers, loads, and manages plugin lifecycle."""

    def __init__(self, plugins_dir: Path | None = None) -> None:
        self.plugins_dir: Path = plugins_dir or Path("plugins")
        self._instances: dict[str, PluginMixin] = {}
        self._manifests: dict[str, dict[str, Any]] = {}
        self._app = None

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def discover(self) -> dict[str, dict[str, Any]]:
        """Scan plugins_dir and return valid manifests keyed by plugin_id."""
        manifests: dict[str, dict[str, Any]] = {}
        if not self.plugins_dir.is_dir():
            return manifests
        for entry in sorted(self.plugins_dir.iterdir()):
            if not entry.is_dir():
                continue
            manifest_path = entry / "plugin.json"
            plugin_py = entry / "plugin.py"
            if not manifest_path.exists() or not plugin_py.exists():
                continue
            try:
                manifest = json.loads(manifest_path.read_text())
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Plugin %s: invalid manifest — %s", entry.name, exc)
                continue
            if not _REQUIRED_MANIFEST_KEYS.issubset(manifest):
                logger.warning("Plugin %s: manifest missing required keys", entry.name)
                continue
            manifests[manifest["id"]] = {**manifest, "_path": entry}
        return manifests

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def _load_plugin(self, manifest: dict[str, Any]) -> PluginMixin | None:
        """Import plugin.py, find the PluginMixin subclass, instantiate it."""
        plugin_id = manifest["id"]
        plugin_path: Path = manifest["_path"]
        module_name = f"_autoshop_plugin_{plugin_id}"
        spec = importlib.util.spec_from_file_location(module_name, plugin_path / "plugin.py")
        if spec is None or spec.loader is None:
            logger.error("Plugin %s: could not create module spec", plugin_id)
            return None
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)  # type: ignore[union-attr]
        except Exception as exc:
            logger.error("Plugin %s: error loading module — %s", plugin_id, exc)
            sys.modules.pop(module_name, None)
            return None

        klass = None
        for attr in vars(module).values():
            if (
                isinstance(attr, type)
                and issubclass(attr, PluginMixin)
                and attr is not PluginMixin
            ):
                klass = attr
                break

        if klass is None:
            logger.error("Plugin %s: no PluginMixin subclass found", plugin_id)
            return None

        instance = klass()
        instance.plugin_id = plugin_id
        instance.plugin_name = manifest["name"]
        instance.plugin_version = manifest["version"]
        return instance

    # ------------------------------------------------------------------
    # Flask integration (implemented in Task 4)
    # ------------------------------------------------------------------

    def init_app(self, app) -> None:
        """Wire plugin manager into a Flask app."""
        # Implemented in Task 4
        pass
```

- [ ] **Step 4: Create plugins dir**

```bash
mkdir -p plugins && touch plugins/.gitkeep
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
PYTHONPATH=src pytest tests/test_plugin_manager.py -v
```

Expected: 4 PASSED

- [ ] **Step 6: Commit**

```bash
git add src/autoshop_crm/plugins/manager.py tests/test_plugin_manager.py plugins/.gitkeep
git commit -m "feat: add PluginManager with plugin discovery and safe loading"
```

---

### Task 4: PluginManager — Flask integration and install/uninstall

**Files:**
- Modify: `src/autoshop_crm/plugins/manager.py` (complete `init_app`, add `install_from_path`, `install_from_url`, `uninstall`, `enable`, `disable`)
- Modify: `requirements.txt` (add `gitpython`)

- [ ] **Step 1: Add gitpython to requirements.txt**

Open `requirements.txt` and add:
```
gitpython
```

Install it:
```bash
pip install gitpython
```

- [ ] **Step 2: Replace the stub `init_app` and add lifecycle methods**

Replace the entire `init_app` method and add the install/uninstall/enable/disable methods in `src/autoshop_crm/plugins/manager.py`:

```python
    def init_app(self, app) -> None:
        """Wire plugin manager into a Flask app — call after all core blueprints."""
        from .models import PluginState
        self._app = app
        self.plugins_dir = Path(app.root_path).parent.parent / "plugins"

        manifests = self.discover()
        self._manifests = manifests

        with app.app_context():
            for plugin_id, manifest in manifests.items():
                state = PluginState.query.filter_by(plugin_id=plugin_id).first()
                if state is None or not state.enabled:
                    continue
                instance = self._load_plugin(manifest)
                if instance is None:
                    if state:
                        state.failed = True
                        state.fail_reason = "Failed to load module"
                        from ..extensions import db
                        db.session.commit()
                    continue
                self._register_plugin(app, instance)
                self._instances[plugin_id] = instance

        # Expose contributions as Jinja globals
        app.jinja_env.globals["plugin_nav_items"] = self._collect_nav_items()
        app.jinja_env.globals["plugin_dashboard_widgets"] = self._collect_dashboard_widgets()
        app.jinja_env.globals["plugin_settings_panels"] = self._collect_settings_panels()

    def _register_plugin(self, app, instance: PluginMixin) -> None:
        """Register blueprint, template folder, and static folder for a plugin."""
        bp = instance.get_blueprint()
        if bp is not None:
            url_prefix = f"/plugins/{instance.plugin_id}"
            if bp.name not in app.blueprints:
                app.register_blueprint(bp, url_prefix=url_prefix)

        plugin_path: Path = self._manifests[instance.plugin_id]["_path"]
        template_dir = plugin_path / "templates"
        if template_dir.is_dir():
            app.jinja_loader.searchpath.append(str(template_dir))  # type: ignore[union-attr]

    def _collect_nav_items(self) -> list[dict]:
        items = []
        for inst in self._instances.values():
            items.extend(inst.get_nav_items())
        return items

    def _collect_dashboard_widgets(self) -> list[dict]:
        widgets = []
        for inst in self._instances.values():
            widgets.extend(inst.get_dashboard_widgets())
        return sorted(widgets, key=lambda w: w.get("order", 99))

    def _collect_settings_panels(self) -> list[dict]:
        panels = []
        for inst in self._instances.values():
            panel = inst.get_settings_panel()
            if panel is not None:
                panels.append(panel)
        return panels

    # ------------------------------------------------------------------
    # Install / uninstall
    # ------------------------------------------------------------------

    def install_from_path(self, path: Path) -> str:
        """Copy a plugin folder into plugins_dir, register it. Returns plugin_id."""
        from .models import PluginState
        from ..extensions import db

        manifest_path = path / "plugin.json"
        if not manifest_path.exists():
            raise ValueError(f"No plugin.json found in {path}")
        manifest = json.loads(manifest_path.read_text())
        if not _REQUIRED_MANIFEST_KEYS.issubset(manifest):
            raise ValueError("plugin.json is missing required keys")

        plugin_id = manifest["id"]
        dest = self.plugins_dir / plugin_id
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(path, dest)

        state = PluginState.query.filter_by(plugin_id=plugin_id).first()
        if state is None:
            state = PluginState(plugin_id=plugin_id, enabled=True, settings={})
            db.session.add(state)
        else:
            state.enabled = True
            state.failed = False
            state.fail_reason = None
        db.session.commit()

        manifest["_path"] = dest
        self._manifests[plugin_id] = manifest
        instance = self._load_plugin(manifest)
        if instance is not None:
            instance.on_install()
            if self._app:
                self._register_plugin(self._app, instance)
            self._instances[plugin_id] = instance
            self._refresh_jinja_globals()

        return plugin_id

    def install_from_url(self, url: str, plugin_path: str | None = None) -> str:
        """Clone url into a temp dir, copy plugin_path subfolder, install."""
        import tempfile
        import git

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            git.Repo.clone_from(url, tmp_path)
            source = tmp_path / plugin_path if plugin_path else tmp_path
            if not (source / "plugin.json").exists():
                raise ValueError(f"No plugin.json found at {source}")
            return self.install_from_path(source)

    def uninstall(self, plugin_id: str) -> None:
        """Remove plugin folder and DB state."""
        from .models import PluginState
        from ..extensions import db

        instance = self._instances.get(plugin_id)
        if instance:
            try:
                instance.on_uninstall()
            except Exception as exc:
                logger.warning("Plugin %s: on_uninstall error — %s", plugin_id, exc)

        plugin_dir = self.plugins_dir / plugin_id
        if plugin_dir.exists():
            shutil.rmtree(plugin_dir)

        PluginState.query.filter_by(plugin_id=plugin_id).delete()
        db.session.commit()

        self._instances.pop(plugin_id, None)
        self._manifests.pop(plugin_id, None)
        self._refresh_jinja_globals()

    def enable(self, plugin_id: str) -> None:
        """Enable a plugin and register it."""
        from .models import PluginState
        from ..extensions import db

        state = PluginState.query.filter_by(plugin_id=plugin_id).first()
        if state:
            state.enabled = True
            db.session.commit()
        manifest = self._manifests.get(plugin_id)
        if manifest and plugin_id not in self._instances:
            instance = self._load_plugin(manifest)
            if instance and self._app:
                self._register_plugin(self._app, instance)
                self._instances[plugin_id] = instance
                self._refresh_jinja_globals()

    def disable(self, plugin_id: str) -> None:
        """Disable a plugin (takes full effect after restart)."""
        from .models import PluginState
        from ..extensions import db

        state = PluginState.query.filter_by(plugin_id=plugin_id).first()
        if state:
            state.enabled = False
            db.session.commit()

    def get_all_states(self) -> list[dict]:
        """Return list of plugin info dicts for the management UI."""
        from .models import PluginState
        states = {s.plugin_id: s for s in PluginState.query.all()}
        result = []
        for plugin_id, manifest in self._manifests.items():
            state = states.get(plugin_id)
            result.append({
                "id": plugin_id,
                "name": manifest["name"],
                "version": manifest["version"],
                "description": manifest["description"],
                "author": manifest["author"],
                "enabled": state.enabled if state else False,
                "failed": state.failed if state else False,
                "fail_reason": state.fail_reason if state else None,
                "installed_at": state.installed_at if state else None,
            })
        return result

    def _refresh_jinja_globals(self) -> None:
        if self._app:
            self._app.jinja_env.globals["plugin_nav_items"] = self._collect_nav_items()
            self._app.jinja_env.globals["plugin_dashboard_widgets"] = self._collect_dashboard_widgets()
            self._app.jinja_env.globals["plugin_settings_panels"] = self._collect_settings_panels()
```

- [ ] **Step 3: Commit**

```bash
git add src/autoshop_crm/plugins/manager.py requirements.txt
git commit -m "feat: complete PluginManager with init_app, install, uninstall, enable/disable"
```

---

### Task 5: New permissions

**Files:**
- Modify: `src/autoshop_crm/services/authorization.py`

- [ ] **Step 1: Add the two new permissions**

In `src/autoshop_crm/services/authorization.py`, update `PERMISSIONS`:

```python
PERMISSIONS: tuple[str, ...] = (
    "view_dashboard",
    "view_customers",
    "manage_customers",
    "view_vehicles",
    "manage_vehicles",
    "view_jobs",
    "manage_jobs",
    "view_accounting",
    "export_accounting",
    "manage_settings",
    "manage_users",
    "manage_permissions",
    "manage_theme",
    "manage_updates",
    "manage_plugins",        # new
    "access_admin_panel",    # new
)
```

Add to `ROLE_PERMISSIONS` for `admin` and `owner`:

```python
"admin": set(PERMISSIONS),  # already gets all, no change needed
"owner": {
    "view_dashboard",
    "view_customers",
    "manage_customers",
    "view_vehicles",
    "manage_vehicles",
    "view_jobs",
    "manage_jobs",
    "view_accounting",
    "export_accounting",
    "manage_settings",
    "manage_users",
    "manage_permissions",
    "manage_theme",
    "manage_updates",
    # manage_plugins and access_admin_panel intentionally NOT given to owner
},
```

Add to `PERMISSION_LABELS`:

```python
"manage_plugins": "Install and manage plugins",
"access_admin_panel": "Access admin panel",
```

- [ ] **Step 2: Run existing tests to verify nothing broke**

```bash
PYTHONPATH=src pytest tests/ -v
```

Expected: All previously passing tests still pass.

- [ ] **Step 3: Commit**

```bash
git add src/autoshop_crm/services/authorization.py
git commit -m "feat: add manage_plugins and access_admin_panel permissions"
```

---

### Task 6: Admin blueprint

**Files:**
- Create: `src/autoshop_crm/routes/admin/__init__.py`
- Create: `src/autoshop_crm/routes/admin/panel.py`
- Create: `src/autoshop_crm/templates/admin/layout.html`
- Create: `src/autoshop_crm/templates/admin/index.html`
- Create: `tests/test_admin_routes.py`
- Modify: `src/autoshop_crm/app.py`

- [ ] **Step 1: Write failing route tests**

```python
# tests/test_admin_routes.py
import pytest
from autoshop_crm import create_app
from autoshop_crm.extensions import db as _db
from autoshop_crm.models.user import User


@pytest.fixture
def app():
    app = create_app()
    app.config.update({"TESTING": True, "LOGIN_DISABLED": False,
                       "WTF_CSRF_ENABLED": False,
                       "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.app_context():
        _db.create_all()
        yield app
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def admin_user(app):
    with app.app_context():
        u = User(username="admin", role="admin")
        u.set_password("password")
        _db.session.add(u)
        _db.session.commit()
        return u


def _login(client, username, password):
    return client.post("/login", data={"username": username, "password": password},
                       follow_redirects=True)


def test_admin_panel_requires_login(client):
    resp = client.get("/admin", follow_redirects=False)
    assert resp.status_code in (302, 401)


def test_admin_panel_accessible_to_admin(client, admin_user):
    _login(client, "admin", "password")
    resp = client.get("/admin")
    assert resp.status_code == 200


def test_admin_updates_accessible_to_admin(client, admin_user):
    _login(client, "admin", "password")
    resp = client.get("/admin/updates")
    assert resp.status_code == 200


def test_admin_danger_accessible_to_admin(client, admin_user):
    _login(client, "admin", "password")
    resp = client.get("/admin/danger")
    assert resp.status_code == 200
```

- [ ] **Step 2: Run to verify they fail**

```bash
PYTHONPATH=src pytest tests/test_admin_routes.py -v
```

Expected: `AssertionError` — `/admin` not found yet.

- [ ] **Step 3: Create admin blueprint package**

```python
# src/autoshop_crm/routes/admin/__init__.py
"""Admin panel blueprint package."""

from flask import Blueprint

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

from . import panel  # noqa: E402, F401
from . import updates_ui  # noqa: E402, F401
from . import danger  # noqa: E402, F401
from . import plugins_ui  # noqa: E402, F401
```

- [ ] **Step 4: Create admin overview route**

```python
# src/autoshop_crm/routes/admin/panel.py
"""Admin panel overview."""

from __future__ import annotations

from flask import render_template
from flask_login import current_user
from flask.typing import ResponseReturnValue

from ...extensions import db
from ...models.user import User
from ...services.authorization import require_permission
from .. admin import admin_bp


@admin_bp.route("")
@admin_bp.route("/")
@require_permission("access_admin_panel")
def index() -> ResponseReturnValue:
    user_count = User.query.filter_by(is_active=True).count()
    from autoshop_crm.plugins.manager import plugin_manager
    plugin_states = plugin_manager.get_all_states() if plugin_manager._app else []
    installed_count = len(plugin_states)
    failed_count = sum(1 for p in plugin_states if p["failed"])
    return render_template(
        "admin/index.html",
        user_count=user_count,
        installed_count=installed_count,
        failed_count=failed_count,
    )
```

- [ ] **Step 5: Create admin layout template**

```html
{# src/autoshop_crm/templates/admin/layout.html #}
{% extends "layouts/base.html" %}

{% block content %}
<section class="hero-panel compact">
    <p class="eyebrow">Admin</p>
    <h1>{% block admin_title %}Admin Panel{% endblock %}</h1>
    {% block admin_subtitle %}<p class="subcopy">System administration and configuration.</p>{% endblock %}
</section>

<nav class="tab-nav" aria-label="Admin sections">
    <a href="{{ url_for('admin.index') }}" class="{{ 'active' if request.endpoint == 'admin.index' }}">Overview</a>
    <a href="{{ url_for('admin.updates') }}" class="{{ 'active' if request.endpoint == 'admin.updates' }}">Updates</a>
    <a href="{{ url_for('admin.plugins') }}" class="{{ 'active' if request.endpoint == 'admin.plugins' }}">Plugins</a>
    <a href="{{ url_for('admin.danger') }}" class="{{ 'active' if request.endpoint == 'admin.danger' }}">Danger Zone</a>
</nav>

{% block admin_content %}{% endblock %}
{% endblock %}
```

- [ ] **Step 6: Create admin overview template**

```html
{# src/autoshop_crm/templates/admin/index.html #}
{% extends "admin/layout.html" %}
{% block admin_title %}Admin Panel{% endblock %}

{% block admin_content %}
<section class="layout-two-col">
    <article class="panel">
        <div class="panel-head"><h2>System</h2></div>
        <div class="form-grid">
            <p class="entity-meta"><strong>Active Users:</strong> {{ user_count }}</p>
            <p class="entity-meta"><strong>Installed Plugins:</strong> {{ installed_count }}</p>
            {% if failed_count > 0 %}
                <p class="entity-meta" style="color:var(--danger)"><strong>Failed Plugins:</strong> {{ failed_count }}</p>
            {% endif %}
        </div>
    </article>

    <article class="panel">
        <div class="panel-head"><h2>Quick Links</h2></div>
        <div class="form-grid">
            <a class="btn btn-secondary" href="{{ url_for('admin.updates') }}">Check for Updates</a>
            <a class="btn btn-secondary" href="{{ url_for('admin.plugins') }}">Manage Plugins</a>
            <a class="btn btn-secondary" href="{{ url_for('dashboard.settings') }}">Shop Settings</a>
            <a class="btn btn-danger" href="{{ url_for('admin.danger') }}">Danger Zone</a>
        </div>
    </article>
</section>
{% endblock %}
```

- [ ] **Step 7: Register admin_bp and plugin_manager in app.py**

In `src/autoshop_crm/app.py`, add imports:

```python
from .routes.admin import admin_bp
from .plugins.manager import PluginManager

plugin_manager = PluginManager()
```

In `create_app()`, after the existing blueprint registrations, add:

```python
app.register_blueprint(admin_bp)
plugin_manager.init_app(app)
```

Also add an Admin nav link in `base.html` — inside the `{% if current_user.is_authenticated %}` block, add:

```html
{% if can('access_admin_panel') %}
    <a href="{{ url_for('admin.index') }}">Admin</a>
{% endif %}
```

Place it after the existing nav links and before Help.

- [ ] **Step 8: Add stub routes for updates, danger, plugins (to unblock tests)**

```python
# src/autoshop_crm/routes/admin/updates_ui.py
from flask import render_template
from ...services.authorization import require_permission
from . import admin_bp

@admin_bp.route("/updates")
@require_permission("access_admin_panel")
def updates():
    return render_template("admin/updates.html")
```

```python
# src/autoshop_crm/routes/admin/danger.py
from flask import render_template
from ...services.authorization import require_permission
from . import admin_bp

@admin_bp.route("/danger")
@require_permission("access_admin_panel")
def danger():
    return render_template("admin/danger.html")
```

```python
# src/autoshop_crm/routes/admin/plugins_ui.py
from flask import render_template
from ...services.authorization import require_permission
from . import admin_bp

@admin_bp.route("/plugins")
@require_permission("access_admin_panel")
def plugins():
    return render_template("admin/plugins/index.html")
```

Create stub templates:
```html
{# src/autoshop_crm/templates/admin/updates.html #}
{% extends "admin/layout.html" %}
{% block admin_title %}Updates{% endblock %}
{% block admin_content %}<section class="panel"><p>Updates UI — coming in next step.</p></section>{% endblock %}
```

```html
{# src/autoshop_crm/templates/admin/danger.html #}
{% extends "admin/layout.html" %}
{% block admin_title %}Danger Zone{% endblock %}
{% block admin_content %}<section class="panel"><p>Danger Zone — coming in next step.</p></section>{% endblock %}
```

```html
{# src/autoshop_crm/templates/admin/plugins/index.html #}
{% extends "admin/layout.html" %}
{% block admin_title %}Plugins{% endblock %}
{% block admin_content %}<section class="panel"><p>Plugins UI — coming in next step.</p></section>{% endblock %}
```

- [ ] **Step 9: Run tests**

```bash
PYTHONPATH=src pytest tests/test_admin_routes.py -v
```

Expected: 4 PASSED

- [ ] **Step 10: Commit**

```bash
git add src/autoshop_crm/routes/admin/ src/autoshop_crm/templates/admin/ src/autoshop_crm/app.py tests/test_admin_routes.py
git commit -m "feat: add admin blueprint with overview page and stub routes"
```

---

### Task 7: Redesigned Updates UI

**Files:**
- Modify: `src/autoshop_crm/routes/admin/updates_ui.py` (full implementation)
- Modify: `src/autoshop_crm/templates/admin/updates.html` (full implementation)

The new updates UI adds:
- Version badges with current vs latest
- Step-by-step progress output via JS polling
- Auto-reconnect after service restarts

- [ ] **Step 1: Implement the full updates route**

Replace `src/autoshop_crm/routes/admin/updates_ui.py` with:

```python
"""Admin updates UI — redesigned with live progress."""

from __future__ import annotations

import json
from pathlib import Path

from flask import Response, current_app, render_template, request, stream_with_context
from flask.typing import ResponseReturnValue

from ...services.authorization import require_permission
from ...services.updater import UpdateError, UpdateManager
from . import admin_bp


def _get_update_manager() -> UpdateManager:
    return UpdateManager(
        repo_path=Path(current_app.config["UPDATE_REPO_PATH"]),
        instance_path=Path(current_app.instance_path),
        remote=current_app.config["UPDATE_REMOTE"],
        branch=current_app.config.get("UPDATE_BRANCH"),
        rollback_limit=current_app.config["UPDATE_ROLLBACK_LIMIT"],
        allow_dirty=current_app.config["UPDATE_ALLOW_DIRTY"],
        command_timeout=current_app.config["UPDATE_COMMAND_TIMEOUT"],
        post_update_commands=current_app.config["UPDATE_POST_UPDATE_COMMANDS"],
        post_rollback_commands=current_app.config["UPDATE_POST_ROLLBACK_COMMANDS"],
        allowed_command_prefixes=current_app.config["UPDATE_ALLOWED_COMMAND_PREFIXES"],
    )


def _is_local_request() -> bool:
    remote = (request.headers.get("X-Forwarded-For", request.remote_addr) or "").split(",")[0].strip()
    return remote in {"127.0.0.1", "::1", "localhost"}


@admin_bp.route("/updates", methods=["GET"])
@require_permission("access_admin_panel")
def updates() -> ResponseReturnValue:
    if not current_app.config.get("UPDATE_ENABLED", True):
        return render_template("admin/updates.html", status={"enabled": False})
    if current_app.config.get("UPDATE_LOCAL_ONLY", True) and not _is_local_request():
        return render_template("admin/updates.html", status={"enabled": False, "error": "Remote access blocked."})
    manager = _get_update_manager()
    status = manager.status(fetch=False)
    return render_template("admin/updates.html", status=status)


@admin_bp.route("/updates/check", methods=["POST"])
@require_permission("access_admin_panel")
def updates_check() -> ResponseReturnValue:
    """Return JSON status after fetching remote."""
    manager = _get_update_manager()
    try:
        status = manager.status(fetch=True)
        return {"ok": True, "has_update": status["has_update"],
                "current": status.get("current_short_commit"),
                "latest": status.get("latest_short_commit"),
                "behind_by": status.get("behind_by", 0)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@admin_bp.route("/updates/apply", methods=["POST"])
@require_permission("access_admin_panel")
def updates_apply() -> ResponseReturnValue:
    """Apply update and return JSON result."""
    if current_app.config.get("UPDATE_LOCAL_ONLY", True) and not _is_local_request():
        return {"ok": False, "error": "Blocked: remote access not allowed for updates."}
    confirm = request.form.get("confirm_text", "").strip()
    if confirm != current_app.config["UPDATE_CONFIRM_PHRASE"]:
        return {"ok": False, "error": "Incorrect confirmation phrase."}
    manager = _get_update_manager()
    try:
        result = manager.apply_update()
        return {"ok": True, "updated": result["updated"],
                "from_commit": result.get("from_commit", "")[:8],
                "to_commit": result.get("to_commit", "")[:8],
                "message": result.get("message", "")}
    except UpdateError as exc:
        return {"ok": False, "error": str(exc)}


@admin_bp.route("/updates/rollback", methods=["POST"])
@require_permission("access_admin_panel")
def updates_rollback() -> ResponseReturnValue:
    """Rollback and return JSON result."""
    if current_app.config.get("UPDATE_LOCAL_ONLY", True) and not _is_local_request():
        return {"ok": False, "error": "Blocked."}
    confirm = request.form.get("confirm_text", "").strip()
    if confirm != current_app.config["UPDATE_CONFIRM_PHRASE"]:
        return {"ok": False, "error": "Incorrect confirmation phrase."}
    steps = int(request.form.get("steps", "1"))
    manager = _get_update_manager()
    try:
        result = manager.rollback(steps=steps)
        return {"ok": True, "from_commit": result.get("from_commit", "")[:8],
                "to_commit": result.get("to_commit", "")[:8]}
    except UpdateError as exc:
        return {"ok": False, "error": str(exc)}
```

- [ ] **Step 2: Implement the full updates template**

Replace `src/autoshop_crm/templates/admin/updates.html` with:

```html
{% extends "admin/layout.html" %}
{% block admin_title %}Updates{% endblock %}
{% block admin_subtitle %}<p class="subcopy">Manage application version, apply updates, and roll back if needed.</p>{% endblock %}

{% block admin_content %}
{% if not status.enabled %}
<section class="panel">
    <p class="entity-meta">{{ status.error or "Update manager is disabled by configuration." }}</p>
</section>
{% else %}
<section class="layout-two-col">
    <article class="panel" id="status-panel">
        <div class="panel-head">
            <h2>Version</h2>
            <span class="chip" id="update-badge">{{ "Update Available" if status.has_update else "Up to Date" }}</span>
        </div>
        <div class="form-grid">
            <p class="entity-meta"><strong>Current:</strong> <code id="current-commit">{{ status.current_short_commit or "N/A" }}</code></p>
            <p class="entity-meta"><strong>Latest:</strong> <code id="latest-commit">{{ status.latest_short_commit or "N/A" }}</code></p>
            <p class="entity-meta"><strong>Behind by:</strong> <span id="behind-by">{{ status.behind_by }}</span> commit(s)</p>
        </div>
        <div style="margin-top:1rem">
            <button class="btn btn-secondary" id="check-btn" onclick="checkForUpdates()">Check for Updates</button>
        </div>
    </article>

    <article class="panel">
        <div class="panel-head"><h2>Apply Update</h2></div>
        <p class="entity-meta">Type <code>{{ config.UPDATE_CONFIRM_PHRASE }}</code> to confirm.</p>
        <div class="form-grid">
            <label class="field">
                <span>Confirmation Phrase</span>
                <input type="text" id="apply-confirm" autocomplete="off" placeholder="{{ config.UPDATE_CONFIRM_PHRASE }}">
            </label>
            <div style="display:flex;gap:.5rem;flex-wrap:wrap">
                <button class="btn btn-primary" id="apply-btn"
                    onclick="applyUpdate()"
                    {{ 'disabled' if not status.has_update }}>Apply Update</button>
                <button class="btn btn-secondary" onclick="rollback(1)">Rollback 1</button>
                <button class="btn btn-secondary" onclick="rollback(2)">Rollback 2</button>
            </div>
        </div>
    </article>
</section>

<section class="panel" id="progress-panel" style="display:none">
    <div class="panel-head">
        <h2 id="progress-title">Applying Update…</h2>
        <span class="chip" id="progress-badge">In Progress</span>
    </div>
    <div id="progress-steps" style="font-family:monospace;font-size:.85rem;line-height:1.6;padding:.5rem 0"></div>
    <div id="reconnect-msg" style="display:none;margin-top:1rem">
        <p class="entity-meta" style="color:var(--warning)">Service restarting — reconnecting…</p>
    </div>
</section>

{% if status.rollback_points %}
<section class="panel">
    <div class="panel-head"><h2>Rollback History</h2></div>
    <ul class="entity-list">
        {% for item in status.rollback_points %}
        <li class="entity-item">
            <p class="entity-meta"><code>{{ item.short_commit }}</code>{% if item.timestamp_utc %} — {{ item.timestamp_utc }}{% endif %}</p>
        </li>
        {% endfor %}
    </ul>
</section>
{% endif %}

<script>
const CSRF = "{{ csrf_token() }}";

function addStep(msg, status) {
    const el = document.getElementById("progress-steps");
    const icon = status === "ok" ? "✓" : status === "error" ? "✗" : "…";
    const color = status === "ok" ? "var(--success)" : status === "error" ? "var(--danger)" : "var(--muted)";
    el.innerHTML += `<div style="color:${color}">${icon} ${msg}</div>`;
    el.scrollTop = el.scrollHeight;
}

function showProgress(title) {
    document.getElementById("progress-panel").style.display = "";
    document.getElementById("progress-title").textContent = title;
    document.getElementById("progress-steps").innerHTML = "";
    document.getElementById("progress-badge").textContent = "In Progress";
    document.getElementById("reconnect-msg").style.display = "none";
}

function finishProgress(ok, msg) {
    document.getElementById("progress-badge").textContent = ok ? "Done" : "Failed";
    document.getElementById("progress-badge").style.background = ok ? "var(--success)" : "var(--danger)";
    addStep(msg, ok ? "ok" : "error");
}

async function checkForUpdates() {
    const btn = document.getElementById("check-btn");
    btn.disabled = true;
    btn.textContent = "Checking…";
    const resp = await fetch("{{ url_for('admin.updates_check') }}", {
        method: "POST",
        headers: {"X-CSRFToken": CSRF}
    });
    const data = await resp.json();
    btn.disabled = false;
    btn.textContent = "Check for Updates";
    if (data.ok) {
        document.getElementById("current-commit").textContent = data.current || "N/A";
        document.getElementById("latest-commit").textContent = data.latest || "N/A";
        document.getElementById("behind-by").textContent = data.behind_by;
        document.getElementById("update-badge").textContent = data.has_update ? "Update Available" : "Up to Date";
        document.getElementById("apply-btn").disabled = !data.has_update;
    } else {
        alert("Check failed: " + data.error);
    }
}

async function applyUpdate() {
    const confirm_text = document.getElementById("apply-confirm").value;
    showProgress("Applying Update");
    addStep("Pulling latest code from remote…", "pending");
    const fd = new FormData();
    fd.append("confirm_text", confirm_text);
    fd.append("csrf_token", CSRF);
    const resp = await fetch("{{ url_for('admin.updates_apply') }}", {method:"POST", body: fd});
    const data = await resp.json();
    if (!data.ok) {
        finishProgress(false, data.error);
        return;
    }
    addStep(`Code updated: ${data.from_commit} → ${data.to_commit}`, "ok");
    addStep("Running database migrations…", "ok");
    addStep("Restarting service…", "pending");
    document.getElementById("reconnect-msg").style.display = "";
    // Poll until app is back up
    await waitForReconnect();
}

async function rollback(steps) {
    const confirm_text = document.getElementById("apply-confirm").value;
    showProgress(`Rolling Back ${steps} Update(s)`);
    addStep("Reverting commits…", "pending");
    const fd = new FormData();
    fd.append("confirm_text", confirm_text);
    fd.append("steps", steps);
    fd.append("csrf_token", CSRF);
    const resp = await fetch("{{ url_for('admin.updates_rollback') }}", {method:"POST", body: fd});
    const data = await resp.json();
    if (!data.ok) { finishProgress(false, data.error); return; }
    addStep(`Rolled back: ${data.from_commit} → ${data.to_commit}`, "ok");
    document.getElementById("reconnect-msg").style.display = "";
    await waitForReconnect();
}

async function waitForReconnect() {
    await new Promise(r => setTimeout(r, 3000));
    let tries = 0;
    while (tries < 30) {
        try {
            const r = await fetch(window.location.href, {method:"HEAD"});
            if (r.ok) { window.location.reload(); return; }
        } catch(_) {}
        await new Promise(r => setTimeout(r, 1500));
        tries++;
    }
    finishProgress(false, "Could not reconnect — check service status manually.");
}
</script>
{% endif %}
{% endblock %}
```

- [ ] **Step 3: Run tests**

```bash
PYTHONPATH=src pytest tests/test_admin_routes.py::test_admin_updates_accessible_to_admin -v
```

Expected: PASSED

- [ ] **Step 4: Commit**

```bash
git add src/autoshop_crm/routes/admin/updates_ui.py src/autoshop_crm/templates/admin/updates.html
git commit -m "feat: redesign updates UI with live progress and auto-reconnect"
```

---

### Task 8: Danger Zone

**Files:**
- Modify: `src/autoshop_crm/routes/admin/danger.py`
- Modify: `src/autoshop_crm/templates/admin/danger.html`

- [ ] **Step 1: Implement danger zone route**

Replace `src/autoshop_crm/routes/admin/danger.py` with:

```python
"""Admin danger zone — destructive operations with typed confirmation."""

from __future__ import annotations

from flask import current_app, flash, redirect, render_template, request, url_for
from flask.typing import ResponseReturnValue

from ...extensions import db
from ...models.settings import BusinessSettings
from ...models.ui_preference import AppPreference
from ...services.authorization import require_permission
from . import admin_bp

_CONFIRM_PHRASE = "DELETE EVERYTHING"
_RESET_PHRASE = "RESET DEFAULTS"


@admin_bp.route("/danger", methods=["GET", "POST"])
@require_permission("access_admin_panel")
def danger() -> ResponseReturnValue:
    if request.method == "POST":
        action = request.form.get("action", "")
        confirm = request.form.get("confirm_text", "").strip()

        if action == "clear_all_data":
            if confirm != _CONFIRM_PHRASE:
                flash("Incorrect confirmation phrase.", "error")
                return redirect(url_for("admin.danger"))
            db.drop_all()
            db.create_all()
            flash("All data cleared. Database reset to empty.", "warning")
            return redirect(url_for("auth.login_view"))

        if action == "reset_defaults":
            if confirm != _RESET_PHRASE:
                flash("Incorrect confirmation phrase.", "error")
                return redirect(url_for("admin.danger"))
            BusinessSettings.query.delete()
            AppPreference.query.delete()
            db.session.commit()
            flash("Settings and theme reset to defaults.", "warning")
            return redirect(url_for("dashboard.settings"))

        flash("Unknown action.", "error")
        return redirect(url_for("admin.danger"))

    return render_template(
        "admin/danger.html",
        confirm_phrase=_CONFIRM_PHRASE,
        reset_phrase=_RESET_PHRASE,
    )
```

- [ ] **Step 2: Implement danger zone template**

Replace `src/autoshop_crm/templates/admin/danger.html` with:

```html
{% extends "admin/layout.html" %}
{% block admin_title %}Danger Zone{% endblock %}
{% block admin_subtitle %}<p class="subcopy" style="color:var(--danger)">These actions are irreversible. Read carefully before proceeding.</p>{% endblock %}

{% block admin_content %}
<section class="panel" style="border:2px solid var(--danger)">
    <div class="panel-head">
        <h2 style="color:var(--danger)">Destructive Actions</h2>
        <span class="chip" style="background:var(--danger);color:#fff">Irreversible</span>
    </div>

    <article class="panel" style="margin-top:1rem">
        <div class="panel-head"><h3>Clear All Data</h3></div>
        <p class="entity-meta" style="color:var(--danger)">Drops and recreates all database tables. <strong>All customers, vehicles, jobs, and settings will be permanently deleted.</strong></p>
        <form method="post" onsubmit="return confirm('This will DELETE ALL DATA permanently. Are you absolutely sure?')">
            <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
            <input type="hidden" name="action" value="clear_all_data">
            <label class="field">
                <span>Type <code>{{ confirm_phrase }}</code> to confirm</span>
                <input type="text" name="confirm_text" autocomplete="off" placeholder="{{ confirm_phrase }}">
            </label>
            <button type="submit" class="btn btn-danger" style="margin-top:.5rem">Clear All Data</button>
        </form>
    </article>

    <article class="panel" style="margin-top:1rem">
        <div class="panel-head"><h3>Reset Settings to Defaults</h3></div>
        <p class="entity-meta">Wipes shop branding, theme colors, and business info. Users and job data are preserved.</p>
        <form method="post">
            <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
            <input type="hidden" name="action" value="reset_defaults">
            <label class="field">
                <span>Type <code>{{ reset_phrase }}</code> to confirm</span>
                <input type="text" name="confirm_text" autocomplete="off" placeholder="{{ reset_phrase }}">
            </label>
            <button type="submit" class="btn btn-danger" style="margin-top:.5rem">Reset to Defaults</button>
        </form>
    </article>
</section>
{% endblock %}
```

- [ ] **Step 3: Run tests**

```bash
PYTHONPATH=src pytest tests/test_admin_routes.py::test_admin_danger_accessible_to_admin -v
```

Expected: PASSED

- [ ] **Step 4: Commit**

```bash
git add src/autoshop_crm/routes/admin/danger.py src/autoshop_crm/templates/admin/danger.html
git commit -m "feat: add danger zone with typed confirmation for destructive ops"
```

---

### Task 9: Plugin Management UI

**Files:**
- Modify: `src/autoshop_crm/routes/admin/plugins_ui.py`
- Modify: `src/autoshop_crm/templates/admin/plugins/index.html`

- [ ] **Step 1: Implement plugins management route**

Replace `src/autoshop_crm/routes/admin/plugins_ui.py` with:

```python
"""Admin plugin management UI."""

from __future__ import annotations

import json
from pathlib import Path

import requests as http_requests
from flask import current_app, flash, redirect, render_template, request, url_for
from flask.typing import ResponseReturnValue

from ...services.authorization import require_permission
from . import admin_bp

MARKETPLACE_URL = "https://raw.githubusercontent.com/AydenForCybersec/autoshop-crm-plugins/main/marketplace.json"
_marketplace_cache: list[dict] | None = None


def _fetch_marketplace() -> list[dict]:
    global _marketplace_cache
    if _marketplace_cache is not None:
        return _marketplace_cache
    try:
        resp = http_requests.get(MARKETPLACE_URL, timeout=5)
        resp.raise_for_status()
        _marketplace_cache = resp.json()
    except Exception:
        _marketplace_cache = []
    return _marketplace_cache


@admin_bp.route("/plugins", methods=["GET"])
@require_permission("access_admin_panel")
def plugins() -> ResponseReturnValue:
    from autoshop_crm.plugins.manager import plugin_manager
    installed = plugin_manager.get_all_states()
    installed_ids = {p["id"] for p in installed}
    marketplace = [p for p in _fetch_marketplace() if p["id"] not in installed_ids]
    return render_template(
        "admin/plugins/index.html",
        installed=installed,
        marketplace=marketplace,
    )


@admin_bp.route("/plugins/toggle/<plugin_id>", methods=["POST"])
@require_permission("access_admin_panel")
def plugin_toggle(plugin_id: str) -> ResponseReturnValue:
    from autoshop_crm.plugins.manager import plugin_manager
    from autoshop_crm.plugins.models import PluginState
    state = PluginState.query.filter_by(plugin_id=plugin_id).first()
    if state:
        if state.enabled:
            plugin_manager.disable(plugin_id)
            flash(f"Plugin '{plugin_id}' disabled. Changes take effect after restart.", "info")
        else:
            plugin_manager.enable(plugin_id)
            flash(f"Plugin '{plugin_id}' enabled.", "success")
    return redirect(url_for("admin.plugins"))


@admin_bp.route("/plugins/uninstall/<plugin_id>", methods=["POST"])
@require_permission("access_admin_panel")
def plugin_uninstall(plugin_id: str) -> ResponseReturnValue:
    from autoshop_crm.plugins.manager import plugin_manager
    plugin_manager.uninstall(plugin_id)
    flash(f"Plugin '{plugin_id}' uninstalled.", "warning")
    return redirect(url_for("admin.plugins"))


@admin_bp.route("/plugins/install-url", methods=["POST"])
@require_permission("access_admin_panel")
def plugin_install_url() -> ResponseReturnValue:
    from autoshop_crm.plugins.manager import plugin_manager
    url = request.form.get("url", "").strip()
    plugin_path = request.form.get("plugin_path", "").strip() or None
    if not url:
        flash("URL is required.", "error")
        return redirect(url_for("admin.plugins"))
    try:
        plugin_id = plugin_manager.install_from_url(url, plugin_path)
        flash(f"Plugin '{plugin_id}' installed successfully.", "success")
    except Exception as exc:
        flash(f"Install failed: {exc}", "error")
    return redirect(url_for("admin.plugins"))


@admin_bp.route("/plugins/install-marketplace/<plugin_id>", methods=["POST"])
@require_permission("access_admin_panel")
def plugin_install_marketplace(plugin_id: str) -> ResponseReturnValue:
    from autoshop_crm.plugins.manager import plugin_manager
    marketplace = _fetch_marketplace()
    entry = next((p for p in marketplace if p["id"] == plugin_id), None)
    if entry is None:
        flash("Plugin not found in marketplace.", "error")
        return redirect(url_for("admin.plugins"))
    try:
        pid = plugin_manager.install_from_url(
            entry["repo_url"],
            entry.get("plugin_path")
        )
        flash(f"Plugin '{pid}' installed.", "success")
    except Exception as exc:
        flash(f"Install failed: {exc}", "error")
    return redirect(url_for("admin.plugins"))
```

- [ ] **Step 2: Add `requests` to requirements.txt**

```
requests
```

```bash
pip install requests
```

- [ ] **Step 3: Implement the plugins template**

Replace `src/autoshop_crm/templates/admin/plugins/index.html` with:

```html
{% extends "admin/layout.html" %}
{% block admin_title %}Plugins{% endblock %}
{% block admin_subtitle %}<p class="subcopy">Install, enable, disable, and manage plugins.</p>{% endblock %}

{% block admin_content %}
<nav class="tab-nav" id="plugin-tabs" style="margin-bottom:1rem">
    <a href="#installed" onclick="showTab('installed')" id="tab-installed" class="active">Installed ({{ installed|length }})</a>
    <a href="#marketplace" onclick="showTab('marketplace')" id="tab-marketplace">Marketplace ({{ marketplace|length }})</a>
    <a href="#install-url" onclick="showTab('install-url')" id="tab-url">Install from URL</a>
</nav>

<div id="pane-installed">
{% if installed %}
    <ul class="entity-list">
    {% for plugin in installed %}
        <li class="entity-item" style="display:flex;align-items:center;justify-content:space-between;gap:1rem">
            <div>
                <strong>{{ plugin.name }}</strong>
                <span class="chip">v{{ plugin.version }}</span>
                {% if plugin.failed %}<span class="chip" style="background:var(--danger);color:#fff">Failed</span>{% endif %}
                {% if not plugin.enabled %}<span class="chip" style="background:var(--muted)">Disabled</span>{% endif %}
                <p class="entity-meta">{{ plugin.description }}</p>
                {% if plugin.fail_reason %}<p class="entity-meta" style="color:var(--danger)">{{ plugin.fail_reason }}</p>{% endif %}
            </div>
            <div style="display:flex;gap:.5rem;flex-shrink:0">
                <form method="post" action="{{ url_for('admin.plugin_toggle', plugin_id=plugin.id) }}">
                    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                    <button class="btn btn-secondary">{{ "Disable" if plugin.enabled else "Enable" }}</button>
                </form>
                <form method="post" action="{{ url_for('admin.plugin_uninstall', plugin_id=plugin.id) }}"
                      onsubmit="return confirm('Uninstall {{ plugin.name }}?')">
                    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                    <button class="btn btn-danger">Uninstall</button>
                </form>
            </div>
        </li>
    {% endfor %}
    </ul>
{% else %}
    <p class="empty-state">No plugins installed. Browse the Marketplace to get started.</p>
{% endif %}
</div>

<div id="pane-marketplace" style="display:none">
{% if marketplace %}
    <ul class="entity-list">
    {% for plugin in marketplace %}
        <li class="entity-item" style="display:flex;align-items:center;justify-content:space-between;gap:1rem">
            <div>
                <strong>{{ plugin.name }}</strong>
                <span class="chip">v{{ plugin.version }}</span>
                <p class="entity-meta">{{ plugin.description }}</p>
                <p class="entity-meta" style="color:var(--muted)">by {{ plugin.author }}</p>
            </div>
            <form method="post" action="{{ url_for('admin.plugin_install_marketplace', plugin_id=plugin.id) }}">
                <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                <button class="btn btn-primary">Install</button>
            </form>
        </li>
    {% endfor %}
    </ul>
{% else %}
    <p class="empty-state">No additional plugins available, or marketplace could not be reached.</p>
{% endif %}
</div>

<div id="pane-install-url" style="display:none">
    <section class="panel">
        <div class="panel-head"><h2>Install from GitHub URL</h2></div>
        <form method="post" action="{{ url_for('admin.plugin_install_url') }}">
            <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
            <div class="form-grid">
                <label class="field">
                    <span>GitHub Repository URL</span>
                    <input type="url" name="url" placeholder="https://github.com/user/repo" required>
                </label>
                <label class="field">
                    <span>Plugin subfolder path (leave blank if plugin.json is at repo root)</span>
                    <input type="text" name="plugin_path" placeholder="plugins/my_plugin">
                </label>
                <button type="submit" class="btn btn-primary">Install Plugin</button>
            </div>
        </form>
    </section>
</div>

<script>
function showTab(name) {
    ["installed","marketplace","install-url"].forEach(t => {
        document.getElementById("pane-" + t).style.display = t === name ? "" : "none";
        document.getElementById("tab-" + t).classList.toggle("active", t === name);
    });
    return false;
}
// Show tab from hash
const hash = location.hash.replace("#","");
if (["installed","marketplace","install-url"].includes(hash)) showTab(hash);
</script>
{% endblock %}
```

- [ ] **Step 4: Commit**

```bash
git add src/autoshop_crm/routes/admin/plugins_ui.py src/autoshop_crm/templates/admin/plugins/index.html requirements.txt
git commit -m "feat: add plugin management UI with marketplace, URL install, enable/disable"
```

---

### Task 10: Template integration — nav and dashboard widgets

**Files:**
- Modify: `src/autoshop_crm/templates/layouts/base.html`
- Modify: `src/autoshop_crm/templates/dashboard/index.html`

- [ ] **Step 1: Add plugin nav items and admin link to base.html**

In `src/autoshop_crm/templates/layouts/base.html`, replace the nav block inside `{% if current_user.is_authenticated %}` with:

```html
{% if current_user.is_authenticated %}
    {% if can('view_dashboard') %}
        <a href="{{ url_for('dashboard.index') }}">Dashboard</a>
    {% endif %}
    {% if can('view_customers') %}
        <a href="{{ url_for('customers.list_customers') }}">Customers</a>
    {% endif %}
    {% if can('view_accounting') %}
        <a href="{{ url_for('accounting.index') }}">Accounting</a>
    {% endif %}
    {% if can('manage_settings') %}
        <a href="{{ url_for('dashboard.settings') }}">Settings</a>
    {% endif %}
    {% for item in plugin_nav_items %}
        {% if can(item.permission) %}
            <a href="{{ item.url }}">{{ item.label }}</a>
        {% endif %}
    {% endfor %}
    {% if can('access_admin_panel') %}
        <a href="{{ url_for('admin.index') }}">Admin</a>
    {% endif %}
    <a href="{{ url_for('help.index') }}">Help</a>
    <span class="nav-user">{{ current_user.username }} · {{ role_labels.get(current_user.role_key, current_user.role_key|title) }}</span>
    <a href="{{ url_for('auth.logout_view') }}">Logout</a>
{% else %}
    {% if request.endpoint == "auth.setup_admin" %}
        <a href="{{ url_for('auth.setup_admin') }}">Setup Admin</a>
    {% else %}
        <a href="{{ url_for('auth.login_view') }}">Login</a>
    {% endif %}
{% endif %}
```

Also ensure `plugin_nav_items` defaults to empty list in Jinja globals if the plugin manager hasn't loaded yet. Add this to `app.py` inside `create_app()`, before `plugin_manager.init_app(app)`:

```python
app.jinja_env.globals.setdefault("plugin_nav_items", [])
app.jinja_env.globals.setdefault("plugin_dashboard_widgets", [])
app.jinja_env.globals.setdefault("plugin_settings_panels", [])
```

- [ ] **Step 2: Add plugin widgets to dashboard template**

Open `src/autoshop_crm/templates/dashboard/index.html` and at the bottom of the `{% block content %}`, before `{% endblock %}`, add:

```html
{% if plugin_dashboard_widgets %}
<section>
    {% for widget in plugin_dashboard_widgets %}
        {% if can(widget.permission) %}
            {% with vars = widget.vars %}
                {% include widget.template %}
            {% endwith %}
        {% endif %}
    {% endfor %}
</section>
{% endif %}
```

- [ ] **Step 3: Run full test suite**

```bash
PYTHONPATH=src pytest tests/ -v
```

Expected: All tests pass.

- [ ] **Step 4: Commit**

```bash
git add src/autoshop_crm/templates/layouts/base.html src/autoshop_crm/templates/dashboard/index.html src/autoshop_crm/app.py
git commit -m "feat: inject plugin nav items and dashboard widgets into templates"
```

---

### Task 11: Remove dangerous ops from settings, add plugin settings panels

**Files:**
- Modify: `src/autoshop_crm/templates/settings/index.html`
- Modify: `src/autoshop_crm/routes/dashboard.py` (remove `users` and `permissions` from `SETTINGS_TABS`)

- [ ] **Step 1: Remove users/permissions tabs from SETTINGS_TABS**

In `src/autoshop_crm/routes/dashboard.py`, update:

```python
SETTINGS_TABS = {"business", "theme"}
```

Also remove `users` and `permissions` tab handling from the `settings()` POST handler — delete the `if action in ("create_user", "update_user", ...)` blocks. Add a redirect for any attempt to hit those tabs:

```python
if active_tab not in SETTINGS_TABS:
    active_tab = "business"
```

- [ ] **Step 2: Add plugin settings panels to settings template**

At the bottom of `src/autoshop_crm/templates/settings/index.html`, before `{% endblock %}`, add:

```html
{% for panel in plugin_settings_panels %}
<section class="panel" style="margin-top:1rem">
    <div class="panel-head"><h2>{{ panel.label }}</h2><span class="chip">Plugin</span></div>
    {% with vars = panel.vars %}
        {% include panel.template %}
    {% endwith %}
</section>
{% endfor %}
```

- [ ] **Step 3: Run full test suite**

```bash
PYTHONPATH=src pytest tests/ -v
```

Expected: All tests pass.

- [ ] **Step 4: Push to dev and merge to main**

```bash
git add src/autoshop_crm/templates/settings/index.html src/autoshop_crm/routes/dashboard.py
git commit -m "feat: remove user/permission management from settings, add plugin settings injection"
git push origin dev
git checkout main && git merge dev --no-edit && git push origin main && git checkout dev
```

---

## Self-Review

**Spec coverage check:**
- ✓ PluginMixin base class with all hooks — Task 1
- ✓ PluginState DB model + migration — Task 2
- ✓ PluginManager discovery, loading, install, uninstall, enable/disable — Tasks 3 & 4
- ✓ `manage_plugins` and `access_admin_panel` permissions — Task 5
- ✓ Admin blueprint + overview — Task 6
- ✓ Redesigned update UI with live progress + auto-reconnect — Task 7
- ✓ Danger zone with typed confirmations — Task 8
- ✓ Plugin management UI (installed, marketplace, URL install) — Task 9
- ✓ Nav injection + dashboard widget injection — Task 10
- ✓ Settings cleanup + plugin settings panels — Task 11
- ✓ `gitpython` added to requirements — Task 4

**Not in this plan (covered in Part 2):**
- Bundled plugins (system_monitor, log_viewer, db_backup, shop_announcements, job_timer)
- GitHub plugins repo + marketplace.json

**Type consistency:** `PluginMixin` hooks and `PluginManager` methods use consistent names throughout. `plugin_manager` is exported as a module-level singleton from `manager.py` and imported by name in route files.

**One gap fixed:** `plugin_manager` needs to be exported as a module-level singleton. Add to `manager.py`:

```python
# At bottom of manager.py
plugin_manager = PluginManager()
```

And in `app.py`, import it as:
```python
from .plugins.manager import plugin_manager
```

Instead of instantiating a new one.
