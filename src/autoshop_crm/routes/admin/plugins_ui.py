"""Admin plugin management UI — stub, full implementation in Task 9."""

from flask import render_template
from ...services.authorization import require_permission
from . import admin_bp


@admin_bp.route("/plugins")
@require_permission("access_admin_panel")
def plugins():
    return render_template("admin/plugins/index.html")
