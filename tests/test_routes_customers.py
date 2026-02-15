def test_customers_page(client):
    response = client.get("/customers/")
    assert response.status_code == 200
