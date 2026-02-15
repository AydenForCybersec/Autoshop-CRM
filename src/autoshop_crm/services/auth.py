"""Authentication service helpers wrapping Flask-Login operations."""

from flask_login import login_user, logout_user
from ..models.user import User


def login(username: str, password: str) -> bool:
    """Authenticate a user and establish a login session."""
    user = User.query.filter_by(username=username).first()
    if user and user.is_active and user.check_password(password):
        login_user(user)
        return True
    return False


def logout() -> None:
    """End the current user session."""
    logout_user()
