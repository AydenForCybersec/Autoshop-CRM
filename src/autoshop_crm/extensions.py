"""Shared Flask extension instances."""

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

# Database ORM/session manager.
db = SQLAlchemy()
# Alembic/Flask migration bridge.
migrate = Migrate()
# Authentication/session manager.
login_manager = LoginManager()
# CSRF middleware for all mutating form requests.
csrf = CSRFProtect()

login_manager.login_view = "auth.login_view"
