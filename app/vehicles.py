# app/vehicles.py
from flask import Blueprint, render_template

vehicles_bp = Blueprint('vehicles', __name__, url_prefix='/vehicles')

@vehicles_bp.route('/')
def index():
    return "<h1>Vehicle Management Coming Soon</h1>"
