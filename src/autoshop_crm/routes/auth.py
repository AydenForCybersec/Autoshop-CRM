"""Authentication HTTP routes."""

from sqlalchemy import inspect
from flask.typing import ResponseReturnValue
from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..models.settings import BusinessSettings
from ..models.user import User
from ..services.branding import save_business_logo
from ..services.auth import login, logout

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login_view() -> ResponseReturnValue:
    """Render login form and process credential submission."""
    if User.query.first() is None:
        return redirect(url_for("auth.setup_admin"))

    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()
        if user and not user.is_active:
            flash("This account is disabled. Contact an administrator.")
        elif login(username, password):
            return redirect(url_for("dashboard.index"))
        else:
            flash("Invalid username or password")

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout_view() -> ResponseReturnValue:
    """Log out the current user and redirect to login."""
    logout()
    return redirect(url_for("auth.login_view"))


@auth_bp.route("/setup-admin", methods=["GET", "POST"])
def setup_admin() -> ResponseReturnValue:
    """Create the initial admin account on first launch."""
    if User.query.first() is not None:
        if current_user.is_authenticated:
            return redirect(url_for("dashboard.index"))
        return redirect(url_for("auth.login_view"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        business_name = request.form.get("business_name", "").strip()

        if not username:
            flash("Username is required.")
            return render_template(
                "auth/setup_admin.html",
                setup_username=username,
                setup_business_name=business_name,
            )

        if len(password) < 8:
            flash("Password must be at least 8 characters.")
            return render_template(
                "auth/setup_admin.html",
                setup_username=username,
                setup_business_name=business_name,
            )

        if password != confirm_password:
            flash("Passwords do not match.")
            return render_template(
                "auth/setup_admin.html",
                setup_username=username,
                setup_business_name=business_name,
            )

        if User.query.filter_by(username=username).first():
            flash("That username is already taken.")
            return render_template(
                "auth/setup_admin.html",
                setup_username=username,
                setup_business_name=business_name,
            )

        if not business_name:
            flash("Business name is required.")
            return render_template(
                "auth/setup_admin.html",
                setup_username=username,
                setup_business_name=business_name,
            )

        try:
            logo_path = save_business_logo(request.files.get("business_logo"), current_app.static_folder)
        except ValueError as exc:
            flash(str(exc))
            return render_template(
                "auth/setup_admin.html",
                setup_username=username,
                setup_business_name=business_name,
            )

        user = User(username=username, role="admin")
        user.set_password(password)

        engine = db.session.get_bind()
        if not inspect(engine).has_table("settings"):
            BusinessSettings.__table__.create(bind=engine)

        settings = BusinessSettings(
            shop_name=business_name,
            shop_logo=logo_path,
            setup_complete=True,
        )

        db.session.add(user)
        db.session.add(settings)
        db.session.commit()

        flash("Setup complete. Sign in with your new admin account.")
        return redirect(url_for("auth.login_view"))

    return render_template("auth/setup_admin.html")
