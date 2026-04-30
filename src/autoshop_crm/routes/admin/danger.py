"""Admin danger zone — stub, full implementation in Task 8."""

from flask import render_template
from ...services.authorization import require_permission
from . import admin_bp


@admin_bp.route("/danger")
@require_permission("access_admin_panel")
def danger():
    return render_template("admin/danger.html")
