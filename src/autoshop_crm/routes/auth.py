from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required

from ..services.auth import login, logout

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login_view():
    if request.method == "POST":
        if login(request.form["username"], request.form["password"]):
            return redirect(url_for("customers.list_customers"))

        flash("Invalid username or password")

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout_view():
    logout()
    return redirect(url_for("auth.login_view"))
