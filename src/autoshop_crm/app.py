from flask import Flask

from .config import get_config
from .extensions import db, migrate, login_manager

from .cli import register_commands

# Blueprints
from .routes.customers import customers_bp
from .routes.vehicles import vehicles_bp
from .routes.jobs import jobs_bp
from .routes.auth import auth_bp


def create_app():
    app = Flask(__name__)

    # Load config
    app.config.from_object(get_config())

    # Init extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # Register CLI commands
    register_commands(app)

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(customers_bp, url_prefix="/customers")
    app.register_blueprint(vehicles_bp, url_prefix="/vehicles")
    app.register_blueprint(jobs_bp, url_prefix="/jobs")

    return app
