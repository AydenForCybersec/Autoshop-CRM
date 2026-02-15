from flask_login import login_user, logout_user
from ..models.user import User


def login(username, password):
    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        login_user(user)
        return True
    return False


def logout():
    logout_user()
