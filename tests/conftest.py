"""Shared pytest fixtures for app and client setup."""

import pytest

from autoshop_crm import create_app
from autoshop_crm.extensions import db
from autoshop_crm.models.settings import BusinessSettings
from autoshop_crm.models.user import User


@pytest.fixture
def app():
    """Build a Flask app configured for isolated in-memory testing."""
    app = create_app()
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        WTF_CSRF_ENABLED=False,
        LOGIN_DISABLED=False,
        AUTH_MAX_ATTEMPTS=50,
        AUTH_WINDOW_SECONDS=300,
        AUTH_LOCKOUT_SECONDS=1,
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
def client(app):
    """Return a test client bound to the pytest app fixture."""
    test_client = app.test_client()
    response = test_client.post(
        "/login",
        data={"username": "admin", "password": "supersecure"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    return test_client
