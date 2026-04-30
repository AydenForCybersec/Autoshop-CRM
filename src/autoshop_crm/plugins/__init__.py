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
