"""Admin updates UI — stub, full implementation in Task 7."""

from flask import render_template
from ...services.authorization import require_permission
from . import admin_bp


@admin_bp.route("/updates")
@require_permission("access_admin_panel")
def updates():
    return render_template("admin/updates.html")
