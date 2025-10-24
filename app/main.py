from flask import Blueprint, render_template
from flask_login import login_required, current_user
from sqlalchemy import text
from app.database import db
import subprocess

# Define the blueprint (matches __init__.py import)
main_bp = Blueprint("main", __name__)

@main_bp.route("/dashboard")
@login_required
def dashboard():
    """Main dashboard showing key stats and system info."""
    # Try to get Raspberry Pi CPU temperature (safe fallback if not available)
    try:
        temp_output = subprocess.check_output(["vcgencmd", "measure_temp"]).decode("utf-8")
        temperature = temp_output.replace("temp=", "").strip()
    except Exception:
        temperature = "N/A"

    # Get basic stats from the database
    try:
        customers = db.session.execute(text("SELECT COUNT(*) FROM customers")).scalar() or 0
        vehicles = db.session.execute(text("SELECT COUNT(*) FROM vehicles")).scalar() or 0
        orders = db.session.execute(text("SELECT COUNT(*) FROM orders")).scalar() or 0
        total_revenue = db.session.execute(text("SELECT COALESCE(SUM(total), 0) FROM orders")).scalar() or 0.0
    except Exception:
        customers = vehicles = orders = 0
        total_revenue = 0.0

    # Render the dashboard with stats
    return render_template(
        "dashboard.html",
        current_user=current_user,
        customers=customers,
        vehicles=vehicles,
        orders=orders,
        total_revenue=total_revenue,
        temperature=temperature,
    )
