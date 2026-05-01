"""Application update management routes."""

from __future__ import annotations

from pathlib import Path

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask.typing import ResponseReturnValue

from ..services.authorization import require_permission
from ..services.updater import UpdateError, UpdateManager

updates_bp = Blueprint("updates", __name__)


def get_update_manager() -> UpdateManager:
    """Build update manager from runtime config."""
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
    """Allow sensitive update actions only from local/private network by default."""
    import ipaddress
    raw = (request.headers.get("X-Forwarded-For", request.remote_addr) or "").split(",")[0].strip()
    if raw in {"127.0.0.1", "::1", "localhost"}:
        return True
    try:
        addr = ipaddress.ip_address(raw)
        return addr.is_private or addr.is_loopback
    except ValueError:
        return False


@updates_bp.route("/updates", methods=["GET", "POST"])
@require_permission("manage_updates")
def index() -> ResponseReturnValue:
    """Render and execute update operations."""
    if not current_app.config.get("UPDATE_ENABLED", True):
        flash("Update manager is disabled by configuration.", "warning")
        return render_template("updates/index.html", status={"enabled": False})
    if current_app.config.get("UPDATE_LOCAL_ONLY", True) and not _is_local_request():
        abort(403)

    manager = get_update_manager()

    if request.method == "POST":
        action = request.form.get("action", "").strip().lower()
        try:
            if action == "check":
                status = manager.status(fetch=True)
                if status["error"]:
                    flash(f"Update check failed: {status['error']}", "error")
                elif status["has_update"]:
                    flash("Update available from remote branch.", "info")
                else:
                    flash("No updates available.", "info")
                return redirect(url_for("updates.index"))

            if action == "apply":
                if request.form.get("confirm_text", "").strip() != current_app.config["UPDATE_CONFIRM_PHRASE"]:
                    flash("Type the confirmation phrase before applying updates.", "warning")
                    return redirect(url_for("updates.index"))
                result = manager.apply_update()
                if result["updated"]:
                    flash(
                        "Update applied successfully "
                        f"({result['from_commit'][:8]} -> {result['to_commit'][:8]}).",
                        "success",
                    )
                else:
                    flash(result["message"], "info")
                return redirect(url_for("updates.index"))

            if action == "rollback_1":
                if request.form.get("confirm_text", "").strip() != current_app.config["UPDATE_CONFIRM_PHRASE"]:
                    flash("Type the confirmation phrase before rollback.", "warning")
                    return redirect(url_for("updates.index"))
                result = manager.rollback(steps=1)
                flash(
                    "Rollback complete "
                    f"({result['from_commit'][:8]} -> {result['to_commit'][:8]}).",
                    "warning",
                )
                return redirect(url_for("updates.index"))

            if action == "rollback_2":
                if request.form.get("confirm_text", "").strip() != current_app.config["UPDATE_CONFIRM_PHRASE"]:
                    flash("Type the confirmation phrase before rollback.", "warning")
                    return redirect(url_for("updates.index"))
                result = manager.rollback(steps=2)
                flash(
                    "Rollback by two updates complete "
                    f"({result['from_commit'][:8]} -> {result['to_commit'][:8]}).",
                    "warning",
                )
                return redirect(url_for("updates.index"))

            flash("Unknown update action.", "error")
            return redirect(url_for("updates.index"))
        except UpdateError as exc:
            flash(str(exc), "error")
            return redirect(url_for("updates.index"))

    status = manager.status(fetch=False)
    return render_template("updates/index.html", status=status)
