from flask import Blueprint, render_template
from flask_login import login_required, current_user
from .models import Setting
from .database import db

main_bp = Blueprint("main", __name__, template_folder="templates")

@main_bp.route("/")
def index():
    # if setup incomplete setup blueprint will redirect
    return render_template("index_redirect.html")

@main_bp.route("/dashboard")
@login_required
def dashboard():
    s = Setting.query.first()
    return render_template("dashboard.html", settings=s)
