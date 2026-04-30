"""Admin danger zone — destructive operations with typed confirmation."""

from __future__ import annotations

from flask import flash, redirect, render_template, request, url_for
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
                flash("Incorrect confirmation phrase.")
                return redirect(url_for("admin.danger"))
            db.drop_all()
            db.create_all()
            from alembic.config import Config
            from alembic import command as alembic_command
            from flask import current_app
            import os
            alembic_cfg = Config(os.path.join(current_app.root_path, "..", "..", "migrations", "alembic.ini"))
            alembic_cfg.set_main_option("script_location", os.path.join(current_app.root_path, "..", "..", "migrations"))
            alembic_command.stamp(alembic_cfg, "head")
            flash("All data cleared. Database reset to empty.")
            return redirect(url_for("auth.login_view"))

        if action == "reset_defaults":
            if confirm != _RESET_PHRASE:
                flash("Incorrect confirmation phrase.")
                return redirect(url_for("admin.danger"))
            BusinessSettings.query.delete()
            AppPreference.query.delete()
            db.session.commit()
            flash("Settings and theme reset to defaults.")
            return redirect(url_for("dashboard.settings"))

        flash("Unknown action.")
        return redirect(url_for("admin.danger"))

    return render_template(
        "admin/danger.html",
        confirm_phrase=_CONFIRM_PHRASE,
        reset_phrase=_RESET_PHRASE,
    )
