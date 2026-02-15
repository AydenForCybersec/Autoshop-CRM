"""Shared Flask extension instances."""

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager

# Database ORM/session manager.
db = SQLAlchemy()
# Alembic/Flask migration bridge.
migrate = Migrate()
# Authentication/session manager.
login_manager = LoginManager()

login_manager.login_view = "auth.login_view"
