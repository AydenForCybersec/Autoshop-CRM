"""User model and authentication helpers."""

from __future__ import annotations

from typing import Optional

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from ..extensions import db, login_manager


class User(UserMixin, db.Model):
    """Application login identity."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

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
