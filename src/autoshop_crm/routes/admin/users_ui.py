"""Admin user management — create, edit, reset password, delete, permissions."""

from __future__ import annotations

from flask import flash, redirect, render_template, request, url_for
from flask.typing import ResponseReturnValue
from flask_login import current_user

from ...extensions import db
from ...models.job import JobLabor
from ...models.user import User
from ...services.authorization import (
    PERMISSION_LABELS,
    PERMISSIONS,
    ROLE_LABELS,
    normalize_role,
    require_permission,
    resolve_role_permissions,
)
from . import admin_bp


def _active_admin_count(exclude_id: int | None = None) -> int:
    q = User.query.filter_by(role="admin", is_active=True)
    if exclude_id is not None:
        q = q.filter(User.id != exclude_id)
    return q.count()


@admin_bp.route("/users", methods=["GET"])
@require_permission("access_admin_panel")
def users() -> ResponseReturnValue:
    all_users = User.query.order_by(User.username).all()
    return render_template(
        "admin/users.html",
        users=all_users,
        roles=ROLE_LABELS,
        permissions=PERMISSIONS,
        permission_labels=PERMISSION_LABELS,
    )


@admin_bp.route("/users/create", methods=["POST"])
@require_permission("access_admin_panel")
def user_create() -> ResponseReturnValue:
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    role = normalize_role(request.form.get("role"))

    if not username:
        flash("Username is required.", "error")
        return redirect(url_for("admin.users"))
    if len(password) < 8:
        flash("Password must be at least 8 characters.", "error")
        return redirect(url_for("admin.users"))
    if User.query.filter_by(username=username).first() is not None:
        flash(f"Username '{username}' is already taken.", "error")
        return redirect(url_for("admin.users"))

    labor_rate_raw = request.form.get("labor_rate", "").strip()
    labor_rate = None
    if labor_rate_raw:
        try:
            labor_rate = float(labor_rate_raw)
        except ValueError:
            flash("Labor rate must be a valid number.", "error")
            return redirect(url_for("admin.users"))

    user = User(username=username, role=role, labor_rate=labor_rate)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    flash(f"User '{username}' created.")
    return redirect(url_for("admin.users"))


@admin_bp.route("/users/<int:user_id>/edit", methods=["POST"])
@require_permission("access_admin_panel")
def user_edit(user_id: int) -> ResponseReturnValue:
    user = User.query.get_or_404(user_id)
    role = normalize_role(request.form.get("role"))
    is_active = bool(request.form.get("is_active"))

    if user.id == current_user.id and (role != "admin" or not is_active):
        flash("You cannot demote or deactivate your own account.", "error")
        return redirect(url_for("admin.users"))

    new_username = request.form.get("username", "").strip()
    if not new_username:
        flash("Username cannot be blank.", "error")
        return redirect(url_for("admin.users"))
    if new_username != user.username and User.query.filter_by(username=new_username).first() is not None:
        flash(f"Username '{new_username}' is already taken.", "error")
        return redirect(url_for("admin.users"))

    user.username = new_username
    user.role = role
    user.is_active = is_active
    if role == "admin":
        user.permission_overrides = {}

    labor_rate_raw = request.form.get("labor_rate", "").strip()
    if labor_rate_raw:
        try:
            user.labor_rate = float(labor_rate_raw)
        except ValueError:
            flash("Labor rate must be a valid number.", "error")
            return redirect(url_for("admin.users"))
    else:
        user.labor_rate = None

    db.session.commit()
    flash(f"Updated user '{user.username}'.")
    return redirect(url_for("admin.users"))


@admin_bp.route("/users/<int:user_id>/reset-password", methods=["POST"])
@require_permission("access_admin_panel")
def user_reset_password(user_id: int) -> ResponseReturnValue:
    user = User.query.get_or_404(user_id)
    password = request.form.get("password", "")
    if len(password) < 8:
        flash("Password must be at least 8 characters.", "error")
        return redirect(url_for("admin.users"))
    user.set_password(password)
    db.session.commit()
    flash(f"Password updated for '{user.username}'.")
    return redirect(url_for("admin.users"))


@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
@require_permission("access_admin_panel")
def user_delete(user_id: int) -> ResponseReturnValue:
    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        flash("You cannot delete your own account.", "error")
        return redirect(url_for("admin.users"))

    JobLabor.query.filter_by(user_id=user.id).update({"user_id": None})
    username = user.username
    db.session.delete(user)
    db.session.commit()
    flash(f"User '{username}' has been deleted.")
    return redirect(url_for("admin.users"))


@admin_bp.route("/users/<int:user_id>/permissions", methods=["POST"])
@require_permission("access_admin_panel")
def user_permissions(user_id: int) -> ResponseReturnValue:
    user = User.query.get_or_404(user_id)
    if user.role == "admin":
        flash("Admin permissions are always full-access.", "error")
        return redirect(url_for("admin.users"))

    selected = set(request.form.getlist("permissions"))
    base_permissions = resolve_role_permissions(user.role_key)
    overrides: dict[str, bool] = {}
    for permission in PERMISSIONS:
        selected_enabled = permission in selected
        base_enabled = permission in base_permissions
        if selected_enabled != base_enabled:
            overrides[permission] = selected_enabled

    user.permission_overrides = overrides
    db.session.commit()
    flash(f"Permissions updated for '{user.username}'.")
    return redirect(url_for("admin.users"))
