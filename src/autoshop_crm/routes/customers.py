"""Customer-facing HTTP routes."""

from flask.typing import ResponseReturnValue
from flask import Blueprint, flash, render_template, request, redirect, url_for

from ..services.authorization import require_permission
from ..services.customers import (
    find_customer_duplicates,
    get_customers_paginated,
    get_customer,
    create_customer,
    update_customer,
    merge_customer_data,
)
from ..services.dates import parse_optional_datetime

customers_bp = Blueprint("customers", __name__)


@customers_bp.route("/")
@require_permission("view_customers")
def list_customers() -> ResponseReturnValue:
    """Render a paginated list of customers."""
    page = request.args.get("page", 1, type=int)
    search = request.args.get("q", "").strip()
    pagination = get_customers_paginated(page, search=search)

    return render_template(
        "customers/list.html",
        customers=pagination.items,
        pagination=pagination,
        search_query=search,
    )

@customers_bp.route("/<int:customer_id>")
@require_permission("view_customers")
def customer_detail(customer_id: int) -> ResponseReturnValue:
    """Render detail page for a single customer."""
    customer = get_customer(customer_id)
    return render_template("customers/detail.html", customer=customer)


@customers_bp.route("/create", methods=["POST"])
@require_permission("manage_customers")
def create() -> ResponseReturnValue:
    """Create a customer from submitted form values."""
    name = request.form["name"].strip()
    email = request.form.get("email", "").strip() or None
    phone = request.form.get("phone", "").strip() or None
    address = request.form.get("address", "").strip() or None
    created_at_raw = request.form.get("created_at", "").strip()
    duplicate_action = request.form.get("duplicate_action", "").strip()
    selected_customer_id = request.form.get("selected_customer_id", type=int)

    try:
        created_at = parse_optional_datetime(created_at_raw)
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("customers.list_customers"))

    duplicates = find_customer_duplicates(name=name, email=email, phone=phone)
    if duplicates and not duplicate_action:
        return render_template(
            "customers/confirm_duplicate.html",
            pending={"name": name, "email": email or "", "phone": phone or "", "address": address or "", "created_at": created_at_raw},
            duplicates=duplicates,
        )

    if duplicate_action in {"use_existing", "merge_existing"}:
        if not selected_customer_id:
            flash("Please select a customer to continue.")
            return redirect(url_for("customers.list_customers"))

        existing_customer = get_customer(selected_customer_id)
        if duplicate_action == "merge_existing":
            merge_customer_data(existing_customer, name=name, email=email, phone=phone, created_at=created_at)
            flash("Customer data merged into existing record.", "success")
        else:
            flash("Used existing customer record.", "info")
        return redirect(url_for("customers.customer_detail", customer_id=existing_customer.id))

    if duplicate_action == "add_new" and email:
        matching_email = next(
            (customer for customer in duplicates if customer.email and customer.email.lower() == email.lower()),
            None,
        )
        if matching_email:
            flash("Email already exists on another customer. New customer created without email.", "warning")
            email = None

    create_customer(name, email, phone, address=address, created_at=created_at)
    flash("Customer created.", "success")
    return redirect(url_for("customers.list_customers"))


@customers_bp.route("/<int:customer_id>/update", methods=["POST"])
@require_permission("manage_customers")
def update(customer_id: int) -> ResponseReturnValue:
    """Update a customer's profile fields."""
    customer = get_customer(customer_id)
    name = request.form.get("name", "").strip()
    if not name:
        flash("Name cannot be blank.")
        return redirect(url_for("customers.customer_detail", customer_id=customer_id))

    email = request.form.get("email", "").strip() or None
    phone = request.form.get("phone", "").strip() or None
    address = request.form.get("address", "").strip() or None
    update_customer(customer, name=name, email=email, phone=phone, address=address)
    flash("Customer updated.")
    return redirect(url_for("customers.customer_detail", customer_id=customer_id))
