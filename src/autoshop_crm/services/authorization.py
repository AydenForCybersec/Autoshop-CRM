"""Role and permission helpers for route-level authorization."""

from __future__ import annotations

from functools import wraps
from typing import Callable, Iterable

from flask import current_app, flash, redirect, request, url_for
from flask.typing import ResponseReturnValue
from flask_login import current_user

PermissionFunc = Callable[..., ResponseReturnValue]

PERMISSIONS: tuple[str, ...] = (
    "view_dashboard",
    "view_customers",
    "manage_customers",
    "view_vehicles",
    "manage_vehicles",
    "view_jobs",
    "manage_jobs",
    "view_accounting",
    "export_accounting",
    "manage_settings",
    "manage_users",
    "manage_permissions",
    "manage_theme",
    "manage_updates",
    "manage_plugins",
    "access_admin_panel",
)

ROLE_PERMISSIONS: dict[str, set[str]] = {
    "admin": set(PERMISSIONS),
    "owner": {
        "view_dashboard",
        "view_customers",
        "manage_customers",
        "view_vehicles",
        "manage_vehicles",
        "view_jobs",
        "manage_jobs",
        "view_accounting",
        "export_accounting",
        "manage_settings",
        "manage_users",
        "manage_permissions",
        "manage_theme",
        "manage_updates",
    },
    "mechanic": {
        "view_dashboard",
        "view_customers",
        "view_vehicles",
        "view_jobs",
        "manage_jobs",
    },
    "accountant": {
        "view_dashboard",
        "view_accounting",
        "export_accounting",
    },
    "service_writer": {
        "view_dashboard",
        "view_customers",
        "manage_customers",
        "view_vehicles",
        "manage_vehicles",
        "view_jobs",
        "manage_jobs",
    },
    "custom": set(),
}

ROLE_LABELS: dict[str, str] = {
    "admin": "Admin",
    "owner": "Owner",
    "mechanic": "Mechanic",
    "accountant": "Accountant",
    "service_writer": "Service Writer",
    "custom": "Custom",
}

PERMISSION_LABELS: dict[str, str] = {
    "view_dashboard": "View dashboard",
    "view_customers": "View customers",
    "manage_customers": "Create/edit customers",
    "view_vehicles": "View vehicles",
    "manage_vehicles": "Create/edit vehicles",
    "view_jobs": "View work orders",
    "manage_jobs": "Create/edit work orders",
    "view_accounting": "View accounting reports",
    "export_accounting": "Export accounting CSV",
    "manage_settings": "Manage settings",
    "manage_users": "Create/manage users",
    "manage_permissions": "Set user permissions",
    "manage_theme": "Customize theme",
    "manage_updates": "Manage app updates",
    "manage_plugins": "Install and manage plugins",
    "access_admin_panel": "Access admin panel",
}


def normalize_role(role: str | None) -> str:
    """Normalize any role input to a supported key."""
    role_key = (role or "").strip().lower()
    if role_key in ROLE_PERMISSIONS:
        return role_key
    return "owner"


def resolve_role_permissions(role: str | None) -> set[str]:
    """Return default permission set for a role."""
    role_key = normalize_role(role)
    return set(ROLE_PERMISSIONS.get(role_key, set()))


def apply_permission_overrides(
    base_permissions: Iterable[str], overrides: dict[str, bool] | None
) -> set[str]:
    """Apply per-user permission grants/denials to a base permission set."""
    merged = set(base_permissions)
    for key, allowed in (overrides or {}).items():
        if key not in PERMISSIONS:
            continue
        if bool(allowed):
            merged.add(key)
        else:
            merged.discard(key)
    return merged


def can_current_user(permission: str) -> bool:
    """Return True when current user can access a permission-gated feature."""
    if current_app.config.get("LOGIN_DISABLED"):
        return True
    if not current_user.is_authenticated:
        return False
    return bool(getattr(current_user, "can", lambda _: False)(permission))


def require_permission(permission: str) -> Callable[[PermissionFunc], PermissionFunc]:
    """Route decorator enforcing a specific permission."""

    def decorator(func: PermissionFunc) -> PermissionFunc:
        @wraps(func)
        def wrapped(*args, **kwargs):
            if can_current_user(permission):
                return func(*args, **kwargs)

            if current_app.config.get("LOGIN_DISABLED"):
                return func(*args, **kwargs)

            if not current_user.is_authenticated:
                return redirect(url_for("auth.login_view", next=request.full_path))

            flash("You do not have permission to access that section.", "warning")
            return redirect(url_for("dashboard.index"))

        return wrapped

    return decorator
