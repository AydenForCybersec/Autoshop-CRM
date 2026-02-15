"""Customer service functions for querying and mutating customer data."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import func, or_

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


def find_customer_duplicates(name: str, email: Optional[str], phone: Optional[str]) -> list[Customer]:
    """Return likely duplicates for a customer profile."""
    normalized_name = name.strip()
    normalized_email = email.strip().lower() if email and email.strip() else None
    normalized_phone = Customer._normalize_phone(phone)

    clauses = [func.lower(Customer.name) == normalized_name.lower()]
    if normalized_email:
        clauses.append(func.lower(Customer.email) == normalized_email)
    if normalized_phone:
        clauses.append(Customer.phone == normalized_phone)

    return (
        Customer.query.filter(or_(*clauses))
        .order_by(Customer.name.asc(), Customer.id.asc())
        .all()
    )


def create_customer(
    name: str,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    created_at: Optional[datetime] = None,
) -> Customer:
    """Create and persist a customer record."""
    normalized_email = email.strip().lower() if email and email.strip() else None
    customer = Customer(name=name.strip(), email=normalized_email, phone=phone, created_at=created_at or datetime.utcnow())
    db.session.add(customer)
    db.session.commit()
    return customer


def merge_customer_data(
    existing_customer: Customer,
    name: str,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    created_at: Optional[datetime] = None,
) -> Customer:
    """Merge new customer form data into an existing record."""
    cleaned_name = name.strip()
    normalized_email = email.strip().lower() if email and email.strip() else None
    normalized_phone = Customer._normalize_phone(phone)

    if cleaned_name and existing_customer.name.lower() == "unknown customer":
        existing_customer.name = cleaned_name
    if normalized_email and not existing_customer.email:
        existing_customer.email = normalized_email
    if normalized_phone and not existing_customer.phone:
        existing_customer.phone = normalized_phone

    if created_at:
        if existing_customer.created_at is None or created_at < existing_customer.created_at:
            existing_customer.created_at = created_at

    db.session.commit()
    return existing_customer


def get_customer(customer_id: int) -> Customer:
    """Fetch one customer by id or raise 404."""
    return Customer.query.get_or_404(customer_id)
