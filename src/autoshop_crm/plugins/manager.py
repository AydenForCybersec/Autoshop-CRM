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
    # Flask integration
    # ------------------------------------------------------------------

    def init_app(self, app) -> None:
        """Wire plugin manager into a Flask app — call after all core blueprints."""
        from .models import PluginState
        self._app = app
        self.plugins_dir = Path(app.root_path).parent.parent / "plugins"

        manifests = self.discover()
        self._manifests = manifests

        with app.app_context():
            for plugin_id, manifest in manifests.items():
                # Register declared permissions first so can() works for all roles.
                self._register_permissions(manifest)
                state = PluginState.query.filter_by(plugin_id=plugin_id).first()
                instance = self._load_plugin(manifest)
                if instance is None:
                    if state:
                        state.failed = True
                        state.fail_reason = "Failed to load module"
                        from ..extensions import db
                        db.session.commit()
                    continue
                # Register blueprint for ALL discovered plugins at startup,
                # even disabled ones — Flask forbids registration after first request.
                self._register_plugin(app, instance)
                if state and state.enabled:
                    self._instances[plugin_id] = instance

        app.jinja_env.globals["plugin_nav_items"] = self._collect_nav_items()
        app.jinja_env.globals["plugin_dashboard_widgets"] = self._collect_dashboard_widgets()
        app.jinja_env.globals["plugin_settings_panels"] = self._collect_settings_panels()

    def _register_permissions(self, manifest: dict) -> None:
        """Add plugin-declared permissions to the live RBAC module."""
        from ..services import authorization as _auth
        for perm in manifest.get("declares_permissions", []):
            if perm not in _auth.PERMISSIONS:
                _auth.PERMISSIONS = _auth.PERMISSIONS + (perm,)
                _auth.PERMISSION_LABELS.setdefault(perm, perm.replace("_", " ").title())
            for role_key in ("admin", "owner"):
                _auth.ROLE_PERMISSIONS[role_key].add(perm)

    def _register_plugin(self, app, instance: PluginMixin) -> None:
        """Register blueprint for a plugin. Blueprint must set template_folder='templates'."""
        bp = instance.get_blueprint()
        if bp is not None:
            url_prefix = f"/plugins/{instance.plugin_id}"
            if bp.name not in app.blueprints:
                app.register_blueprint(bp, url_prefix=url_prefix)

    def _collect_nav_items(self) -> list[dict]:
        items = []
        for inst in self._instances.values():
            try:
                items.extend(inst.get_nav_items())
            except Exception as exc:
                logger.warning("Plugin %s: get_nav_items error — %s", inst.plugin_id, exc)
        return items

    def _collect_dashboard_widgets(self) -> list[dict]:
        from types import SimpleNamespace
        widgets = []
        for inst in self._instances.values():
            try:
                for w in inst.get_dashboard_widgets():
                    # Convert vars dict to SimpleNamespace so templates can use
                    # vars.key syntax without hitting dict method names (e.g. .items()).
                    if isinstance(w.get("vars"), dict):
                        w = dict(w)
                        w["vars"] = SimpleNamespace(**w["vars"])
                    widgets.append(w)
            except Exception as exc:
                logger.warning("Plugin %s: get_dashboard_widgets error — %s", inst.plugin_id, exc)
        return sorted(widgets, key=lambda w: w.get("order", 99))

    def _collect_settings_panels(self) -> list[dict]:
        panels = []
        for inst in self._instances.values():
            try:
                panel = inst.get_settings_panel()
                if panel is not None:
                    panels.append(panel)
            except Exception as exc:
                logger.warning("Plugin %s: get_settings_panel error — %s", inst.plugin_id, exc)
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
        self._register_permissions(manifest)
        instance = self._load_plugin(manifest)
        if instance is not None:
            instance.on_install()
            if self._app:
                try:
                    self._register_plugin(self._app, instance)
                except Exception as exc:
                    # Flask forbids blueprint registration after the first request.
                    # The plugin is installed; a service reload will activate its routes.
                    logger.warning("Plugin %s: blueprint registration deferred (reload required) — %s", plugin_id, exc)
            self._instances[plugin_id] = instance
            self._refresh_jinja_globals()
        else:
            state.failed = True
            state.fail_reason = "Failed to load module after install"
            db.session.commit()

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
        if state is None:
            state = PluginState(plugin_id=plugin_id, enabled=True, settings={})
            db.session.add(state)
        else:
            state.enabled = True
        db.session.commit()
        manifest = self._manifests.get(plugin_id)
        if manifest and plugin_id not in self._instances:
            instance = self._load_plugin(manifest)
            if instance:
                # Blueprint was registered at startup; just activate the instance.
                # For plugins installed after startup, routes need a service reload.
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


plugin_manager = PluginManager()
