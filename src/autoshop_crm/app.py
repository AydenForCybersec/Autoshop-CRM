"""Flask application factory and blueprint wiring."""

from sqlalchemy import inspect
from flask import Flask, current_app, redirect, render_template, request, url_for
from flask_login import current_user, logout_user

from .config import get_config
from .extensions import csrf, db, migrate, login_manager
from .models.settings import BusinessSettings
from .models.ui_preference import AppPreference
from .models.user import User
from .services.authorization import ROLE_LABELS, can_current_user

from .cli import register_commands

# Blueprints
from .routes.customers import customers_bp
from .routes.vehicles import vehicles_bp
from .routes.jobs import jobs_bp
from .routes.auth import auth_bp
from .routes.dashboard import dashboard_bp
from .routes.accounting import accounting_bp
from .routes.updates import updates_bp
from .routes.help import help_bp


def create_app() -> Flask:
    """Create, configure, and return the Flask application instance."""
    app = Flask(__name__)

    # Load config
    app.config.from_object(get_config())

    # Init extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Register CLI commands
    register_commands(app)

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(updates_bp)
    app.register_blueprint(accounting_bp, url_prefix="/accounting")
    app.register_blueprint(help_bp)
    app.register_blueprint(customers_bp, url_prefix="/customers")
    app.register_blueprint(vehicles_bp, url_prefix="/vehicles")
    app.register_blueprint(jobs_bp, url_prefix="/jobs")

    @app.context_processor
    def inject_branding() -> dict[str, object]:
        """Expose shop branding fields to all templates."""
        default_name = "Autoshop CRM"
        app_name = default_name
        app_logo_url = None
        app_favicon_url = None
        theme_vars = {}

        if inspect(db.session.get_bind()).has_table("settings"):
            settings = BusinessSettings.query.first()
            if settings and settings.shop_name:
                app_name = settings.shop_name.strip() or default_name
            if settings and settings.shop_logo:
                app_logo_url = url_for("static", filename=settings.shop_logo)
                app_favicon_url = app_logo_url

        if inspect(db.session.get_bind()).has_table("app_preferences"):
            preferences = AppPreference.query.first()
            if preferences:
                theme_vars = {
                    "--brand": preferences.primary_color,
                    "--brand-strong": preferences.primary_color,
                    "--highlight": preferences.accent_color,
                    "--bg": preferences.background_color,
                    "--surface": preferences.surface_color,
                    "--text": preferences.text_color,
                    "--muted": preferences.muted_color,
                    "--line": preferences.line_color,
                    "--success": preferences.success_color,
                    "--warning": preferences.warning_color,
                    "--danger": preferences.danger_color,
                    "--radius": f"{preferences.radius_px}px",
                    "--radius-sm": f"{max(6, preferences.radius_px - 6)}px",
                }

        initials = "".join(part[0] for part in app_name.split() if part).upper()[:2] or "AC"
        return {
            "app_name": app_name,
            "app_logo_url": app_logo_url,
            "app_favicon_url": app_favicon_url,
            "app_initials": initials,
            "theme_vars": theme_vars,
            "can": can_current_user,
            "role_labels": ROLE_LABELS,
        }

    @app.before_request
    def enforce_auth_and_bootstrap_admin():
        """Protect non-auth routes and force first-run admin setup."""
        if current_app.config.get("LOGIN_DISABLED"):
            return None

        endpoint = request.endpoint or ""
        if endpoint.startswith("static"):
            return None
        if endpoint == "help.quick_start":
            return None

        has_user = User.query.first() is not None

        if not has_user and endpoint != "auth.setup_admin":
            return redirect(url_for("auth.setup_admin"))

        if has_user and not current_user.is_authenticated and endpoint != "auth.login_view":
            return redirect(url_for("auth.login_view", next=request.full_path))

        if current_user.is_authenticated and not current_user.is_active:
            logout_user()
            return redirect(url_for("auth.login_view"))

        return None

    @app.errorhandler(404)
    def not_found(_error):
        """Render a branded 404 page."""
        return render_template("errors/404.html"), 404

    return app
