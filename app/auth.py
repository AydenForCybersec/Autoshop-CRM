from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from .models import User
from .database import db

auth_bp = Blueprint("auth", __name__, template_folder="templates")

login_manager = LoginManager()
login_manager.login_view = "auth.login"

def init_login(app):
    login_manager.init_app(app)
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    return login_manager

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        pw = request.form.get("password")
        u = User.query.filter_by(email=email).first()
        if u and u.check_password(pw):
            login_user(u)
            flash("Logged in", "success")
            return redirect(url_for("main.dashboard"))
        flash("Invalid credentials", "danger")
    return render_template("login.html")

@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out", "info")
    return redirect(url_for("auth.login"))
