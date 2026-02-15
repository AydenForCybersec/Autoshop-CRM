"""Customer service functions for querying and mutating customer data."""

from __future__ import annotations

from typing import Optional

from ..extensions import db
from ..models.customer import Customer


def get_all_customers() -> list[Customer]:
    """Return all customers sorted alphabetically by name."""
    return Customer.query.order_by(Customer.name).all()


def get_customers_paginated(page: int, per_page: int = 10):
    """Return a pagination object for customer listing pages."""
    return Customer.query.order_by(Customer.name).paginate(
        page=page,
        per_page=per_page,
        error_out=False,
    )


def create_customer(name: str, email: Optional[str] = None, phone: Optional[str] = None) -> Customer:
    """Create and persist a customer record."""
    customer = Customer(name=name, email=email, phone=phone)
    db.session.add(customer)
    db.session.commit()
    return customer


def get_customer(customer_id: int) -> Customer:
    """Fetch one customer by id or raise 404."""
    return Customer.query.get_or_404(customer_id)
