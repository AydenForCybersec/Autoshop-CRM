# app/customers.py
from flask import Blueprint, render_template

customers_bp = Blueprint('customers', __name__, url_prefix='/customers')

@customers_bp.route('/')
def index():
    return "<h1>Customer Management Coming Soon</h1>"
