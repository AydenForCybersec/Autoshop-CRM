"""User model and authentication helpers."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from ..extensions import db, login_manager


class User(UserMixin, db.Model):
    """Application login identity."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    # Keep app-facing attribute as `username` while remaining compatible with
    # existing databases that created this column as `name`.
    username = db.Column("name", db.String(120), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(30))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password: str) -> None:
        """Hash and store a plaintext password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Return ``True`` if the provided password matches stored hash."""
        return check_password_hash(self.password_hash, password)


@login_manager.user_loader
def load_user(user_id: str) -> Optional[User]:
    """Resolve a Flask-Login user id into a ``User`` instance."""
    return User.query.get(int(user_id))
