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
        pass


plugin_manager = PluginManager()
