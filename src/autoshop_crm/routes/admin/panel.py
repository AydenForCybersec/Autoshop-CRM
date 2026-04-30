"""Admin panel overview."""

from __future__ import annotations

from flask import render_template
from flask.typing import ResponseReturnValue

from ...extensions import db
from ...models.user import User
from ...services.authorization import require_permission
from . import admin_bp


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
