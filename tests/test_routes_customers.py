"""Route smoke tests for customer endpoints."""

from autoshop_crm.services.customers import create_customer


def test_customers_page(client):
    """Customer list route should respond successfully."""
    response = client.get("/customers/")
    assert response.status_code == 200


def test_customers_page_supports_search(client, app):
    """Customer directory should filter rows by text query."""
    with app.app_context():
        create_customer("Jane Doe", "jane@example.com", "(555) 101-2020")
        create_customer("John Smith", "john@example.com", "(555) 303-4040")

    response = client.get("/customers/?q=jane")

    assert response.status_code == 200
    assert b"Jane Doe" in response.data
    assert b"John Smith" not in response.data
