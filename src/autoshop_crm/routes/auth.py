"""Authentication HTTP routes."""

from flask.typing import ResponseReturnValue
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required

from ..services.auth import login, logout

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login_view() -> ResponseReturnValue:
    """Render login form and process credential submission."""
    if request.method == "POST":
        if login(request.form["username"], request.form["password"]):
            return redirect(url_for("customers.list_customers"))

        flash("Invalid username or password")

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout_view() -> ResponseReturnValue:
    """Log out the current user and redirect to login."""
    logout()
    return redirect(url_for("auth.login_view"))
