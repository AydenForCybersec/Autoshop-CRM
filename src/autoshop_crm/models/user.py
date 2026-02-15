"""User model and authentication helpers."""

from __future__ import annotations

from typing import Optional

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from ..extensions import db, login_manager
from ..services.authorization import PERMISSIONS, apply_permission_overrides, normalize_role, resolve_role_permissions
from ..services.time import utc_now_naive


class User(UserMixin, db.Model):
    """Application login identity."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    # Keep app-facing attribute as `username` while remaining compatible with
    # existing databases that created this column as `name`.
    username = db.Column("name", db.String(120), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(30), nullable=False, default="owner")
    permission_overrides = db.Column(db.JSON, nullable=False, default=dict)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=utc_now_naive)

    def set_password(self, password: str) -> None:
        """Hash and store a plaintext password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Return ``True`` if the provided password matches stored hash."""
        return check_password_hash(self.password_hash, password)

    @property
    def role_key(self) -> str:
        """Return normalized role key for permission resolution."""
        return normalize_role(self.role)

    @property
    def is_admin(self) -> bool:
        """Return True when user is assigned the admin role."""
        return self.role_key == "admin"

    def get_effective_permissions(self) -> set[str]:
        """Return final permission set including per-user overrides."""
        if self.is_admin:
            return set(PERMISSIONS)
        base = resolve_role_permissions(self.role_key)
        return apply_permission_overrides(base, self.permission_overrides)

    def can(self, permission: str) -> bool:
        """Return True when the user has the requested permission."""
        return permission in self.get_effective_permissions()


@login_manager.user_loader
def load_user(user_id: str) -> Optional[User]:
    """Resolve a Flask-Login user id into a ``User`` instance."""
    return User.query.get(int(user_id))
