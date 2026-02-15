"""Route smoke tests for customer endpoints."""

def test_customers_page(client):
    """Customer list route should respond successfully."""
    response = client.get("/customers/")
    assert response.status_code == 200
