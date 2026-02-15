"""Security and error-page behavior tests."""

from __future__ import annotations

import re

import pytest

from autoshop_crm import create_app
from autoshop_crm.extensions import db
from autoshop_crm.models.settings import BusinessSettings
from autoshop_crm.models.user import User


def _extract_csrf_token(html: bytes) -> str:
    match = re.search(rb'name="csrf_token"\s+value="([^"]+)"', html)
    if not match:
        raise AssertionError("csrf token field missing")
    return match.group(1).decode("utf-8")


@pytest.fixture
def secure_app():
    """Build app with CSRF enabled for negative POST checks."""
    app = create_app()
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        WTF_CSRF_ENABLED=True,
        LOGIN_DISABLED=False,
    )

    with app.app_context():
        db.create_all()
        admin = User(username="admin", role="admin")
        admin.set_password("supersecure")
        db.session.add(admin)
        db.session.add(BusinessSettings(shop_name="Northside Auto", setup_complete=True))
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def secure_client(secure_app):
    """Return authenticated client with CSRF active."""
    client = secure_app.test_client()
    login_get = client.get("/login")
    token = _extract_csrf_token(login_get.data)
    login_response = client.post(
        "/login",
        data={"username": "admin", "password": "supersecure", "csrf_token": token},
        follow_redirects=False,
    )
    assert login_response.status_code == 302
    return client


def test_customer_create_rejects_missing_csrf(secure_client):
    """Mutating endpoints should reject missing CSRF token."""
    response = secure_client.post(
        "/customers/create",
        data={"name": "No Token", "email": "notoken@example.com"},
        follow_redirects=False,
    )
    assert response.status_code == 400


def test_404_page_uses_branded_template(client):
    """Unknown URLs should render themed 404 view."""
    response = client.get("/does-not-exist")
    assert response.status_code == 404
    assert b"That page is not in the service lane." in response.data
