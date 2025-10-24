from flask import Blueprint, render_template, redirect, url_for, jsonify
import subprocess
import psutil

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    return redirect(url_for('main.dashboard'))

@main_bp.route('/dashboard')
def dashboard():
    """Main dashboard with live system metrics"""
    try:
        temp_output = subprocess.check_output(["vcgencmd", "measure_temp"]).decode("utf-8")
        pi_temp = float(temp_output.replace("temp=", "").replace("'C\n", ""))
    except Exception:
        pi_temp = None

    cpu_usage = psutil.cpu_percent()
    mem_usage = psutil.virtual_memory().percent

    settings = {
        "shop_name": "Autoshop CRM",
        "version": "1.0.0",
    }

    return render_template(
        "dashboard.html",
        settings=settings,
        pi_temp=pi_temp,
        cpu_usage=cpu_usage,
        mem_usage=mem_usage,
    )

@main_bp.route('/api/system_stats')
def system_stats():
    """Return JSON system info for live dashboard updates."""
    try:
        temp_output = subprocess.check_output(["vcgencmd", "measure_temp"]).decode("utf-8")
        pi_temp = float(temp_output.replace("temp=", "").replace("'C\n", ""))
    except Exception:
        pi_temp = None

    return jsonify({
        "pi_temp": pi_temp,
        "cpu": psutil.cpu_percent(),
        "mem": psutil.virtual_memory().percent
    })
