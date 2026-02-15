"""Tests for customer service helpers."""

from autoshop_crm.services.customers import create_customer, get_all_customers


def test_create_customer(app):
    """Creating a customer should return a persisted model with an id."""
    customer = create_customer(
        name="John Doe",
        email="john@example.com",
        phone="555-1234",
    )

    assert customer.id is not None
    assert customer.name == "John Doe"


def test_get_all_customers(app):
    """Listing customers should return all seeded records."""
    create_customer("Alice")
    create_customer("Bob")

    customers = get_all_customers()
    assert len(customers) == 2
