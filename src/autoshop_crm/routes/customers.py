"""Customer-facing HTTP routes."""

from flask.typing import ResponseReturnValue
from flask import Blueprint, render_template, request, redirect, url_for

from ..services.customers import (
    get_customers_paginated,
    get_customer,
    create_customer,
)

customers_bp = Blueprint("customers", __name__)


@customers_bp.route("/")
def list_customers() -> ResponseReturnValue:
    """Render a paginated list of customers."""
    page = request.args.get("page", 1, type=int)
    pagination = get_customers_paginated(page)

    return render_template(
        "customers/list.html",
        customers=pagination.items,
        pagination=pagination,
    )

@customers_bp.route("/<int:customer_id>")
def customer_detail(customer_id: int) -> ResponseReturnValue:
    """Render detail page for a single customer."""
    customer = get_customer(customer_id)
    return render_template("customers/detail.html", customer=customer)


@customers_bp.route("/create", methods=["POST"])
def create() -> ResponseReturnValue:
    """Create a customer from submitted form values."""
    name = request.form["name"]
    email = request.form.get("email")
    phone = request.form.get("phone")

    create_customer(name, email, phone)
    return redirect(url_for("customers.list_customers"))
