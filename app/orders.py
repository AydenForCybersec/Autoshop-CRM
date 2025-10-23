# app/orders.py
from flask import Blueprint, render_template

orders_bp = Blueprint('orders', __name__, url_prefix='/orders')

@orders_bp.route('/')
def index():
    return "<h1>Orders Management Coming Soon</h1>"
