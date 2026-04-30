"""Admin updates UI — redesigned with live progress."""

from __future__ import annotations

from pathlib import Path

from flask import current_app, render_template, request
from flask.typing import ResponseReturnValue

from ...services.authorization import require_permission
from ...services.updater import UpdateError, UpdateManager
from . import admin_bp


def _get_update_manager() -> UpdateManager:
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
    remote = (request.headers.get("X-Forwarded-For", request.remote_addr) or "").split(",")[0].strip()
    return remote in {"127.0.0.1", "::1", "localhost"}


@admin_bp.route("/updates", methods=["GET"])
@require_permission("access_admin_panel")
def updates() -> ResponseReturnValue:
    if not current_app.config.get("UPDATE_ENABLED", True):
        return render_template("admin/updates.html", status={"enabled": False})
    if current_app.config.get("UPDATE_LOCAL_ONLY", True) and not _is_local_request():
        return render_template("admin/updates.html", status={"enabled": False, "error": "Remote access blocked."})
    manager = _get_update_manager()
    status = manager.status(fetch=False)
    return render_template("admin/updates.html", status=status)


@admin_bp.route("/updates/check", methods=["POST"])
@require_permission("access_admin_panel")
def updates_check() -> ResponseReturnValue:
    """Return JSON status after fetching remote."""
    manager = _get_update_manager()
    try:
        status = manager.status(fetch=True)
        return {"ok": True, "has_update": status["has_update"],
                "current": status.get("current_short_commit"),
                "latest": status.get("latest_short_commit"),
                "behind_by": status.get("behind_by", 0)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@admin_bp.route("/updates/apply", methods=["POST"])
@require_permission("access_admin_panel")
def updates_apply() -> ResponseReturnValue:
    """Apply update and return JSON result."""
    if current_app.config.get("UPDATE_LOCAL_ONLY", True) and not _is_local_request():
        return {"ok": False, "error": "Blocked: remote access not allowed for updates."}
    confirm = request.form.get("confirm_text", "").strip()
    if confirm != current_app.config["UPDATE_CONFIRM_PHRASE"]:
        return {"ok": False, "error": "Incorrect confirmation phrase."}
    manager = _get_update_manager()
    try:
        result = manager.apply_update()
        return {"ok": True, "updated": result["updated"],
                "from_commit": result.get("from_commit", "")[:8],
                "to_commit": result.get("to_commit", "")[:8],
                "message": result.get("message", "")}
    except UpdateError as exc:
        return {"ok": False, "error": str(exc)}


@admin_bp.route("/updates/rollback", methods=["POST"])
@require_permission("access_admin_panel")
def updates_rollback() -> ResponseReturnValue:
    """Rollback and return JSON result."""
    if current_app.config.get("UPDATE_LOCAL_ONLY", True) and not _is_local_request():
        return {"ok": False, "error": "Blocked."}
    confirm = request.form.get("confirm_text", "").strip()
    if confirm != current_app.config["UPDATE_CONFIRM_PHRASE"]:
        return {"ok": False, "error": "Incorrect confirmation phrase."}
    steps = int(request.form.get("steps", "1"))
    manager = _get_update_manager()
    try:
        result = manager.rollback(steps=steps)
        return {"ok": True, "from_commit": result.get("from_commit", "")[:8],
                "to_commit": result.get("to_commit", "")[:8]}
    except UpdateError as exc:
        return {"ok": False, "error": str(exc)}
