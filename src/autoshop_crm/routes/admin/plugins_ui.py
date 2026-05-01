"""Admin plugin management UI."""

from __future__ import annotations

import requests as http_requests
from flask import flash, redirect, render_template, request, url_for
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
        try:
            if state.enabled:
                plugin_manager.disable(plugin_id)
                flash(f"Plugin '{plugin_id}' disabled. Changes take effect after restart.")
            else:
                plugin_manager.enable(plugin_id)
                flash(f"Plugin '{plugin_id}' enabled.")
        except Exception as exc:
            flash(f"Plugin '{plugin_id}': {exc}", "error")
    return redirect(url_for("admin.plugins"))


@admin_bp.route("/plugins/uninstall/<plugin_id>", methods=["POST"])
@require_permission("access_admin_panel")
def plugin_uninstall(plugin_id: str) -> ResponseReturnValue:
    from autoshop_crm.plugins.manager import plugin_manager
    plugin_manager.uninstall(plugin_id)
    flash(f"Plugin '{plugin_id}' uninstalled.")
    return redirect(url_for("admin.plugins"))


@admin_bp.route("/plugins/install-url", methods=["POST"])
@require_permission("access_admin_panel")
def plugin_install_url() -> ResponseReturnValue:
    from autoshop_crm.plugins.manager import plugin_manager
    url = request.form.get("url", "").strip()
    plugin_path = request.form.get("plugin_path", "").strip() or None
    if not url:
        flash("URL is required.")
        return redirect(url_for("admin.plugins"))
    try:
        plugin_id = plugin_manager.install_from_url(url, plugin_path)
        flash(f"Plugin '{plugin_id}' installed successfully.")
    except Exception as exc:
        flash(f"Install failed: {exc}")
    return redirect(url_for("admin.plugins"))


@admin_bp.route("/plugins/install-marketplace/<plugin_id>", methods=["POST"])
@require_permission("access_admin_panel")
def plugin_install_marketplace(plugin_id: str) -> ResponseReturnValue:
    from autoshop_crm.plugins.manager import plugin_manager
    marketplace = _fetch_marketplace()
    entry = next((p for p in marketplace if p["id"] == plugin_id), None)
    if entry is None:
        flash("Plugin not found in marketplace.")
        return redirect(url_for("admin.plugins"))
    try:
        pid = plugin_manager.install_from_url(entry["repo_url"], entry.get("plugin_path"))
        flash(f"Plugin '{pid}' installed.")
    except Exception as exc:
        flash(f"Install failed: {exc}")
    return redirect(url_for("admin.plugins"))
