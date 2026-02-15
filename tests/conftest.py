"""Shared pytest fixtures for app and client setup."""

import pytest

from autoshop_crm import create_app
from autoshop_crm.extensions import db


@pytest.fixture
def app():
    """Build a Flask app configured for isolated in-memory testing."""
    app = create_app()
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        WTF_CSRF_ENABLED=False,
        LOGIN_DISABLED=True,  # disable auth for most tests
    )

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Return a test client bound to the pytest app fixture."""
    return app.test_client()
