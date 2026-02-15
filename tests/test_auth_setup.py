"""Tests for first-run setup and login gate behavior."""

from io import BytesIO

import pytest

from autoshop_crm import create_app
from autoshop_crm.extensions import db
from autoshop_crm.models.settings import BusinessSettings
from autoshop_crm.models.user import User


@pytest.fixture
def setup_app():
    """Create a test app with auth enforcement enabled."""
    app = create_app()
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        WTF_CSRF_ENABLED=False,
        LOGIN_DISABLED=False,
    )

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def setup_client(setup_app):
    """Return a test client for setup-flow tests."""
    return setup_app.test_client()


def test_first_run_redirects_to_setup(setup_client):
    """Unauthenticated users should be forced to setup before first admin exists."""
    response = setup_client.get("/customers/", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/setup-admin")


def test_setup_creates_admin_and_business_then_requires_login(setup_client, setup_app):
    """Setup should create admin/settings, then require login for protected pages."""
    response = setup_client.post(
        "/setup-admin",
        data={
            "business_name": "Northside Auto",
            "username": "owner",
            "password": "supersecure",
            "confirm_password": "supersecure",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")

    with setup_app.app_context():
        user = User.query.filter_by(username="owner").first()
        assert user is not None
        assert user.role == "admin"
        settings = BusinessSettings.query.first()
        assert settings is not None
        assert settings.shop_name == "Northside Auto"
        assert settings.setup_complete is True

    locked_response = setup_client.get("/customers/", follow_redirects=False)
    assert locked_response.status_code == 302
    assert locked_response.headers["Location"].startswith("/login")

    login_response = setup_client.post(
        "/login",
        data={"username": "owner", "password": "supersecure"},
        follow_redirects=False,
    )
    assert login_response.status_code == 302
    assert login_response.headers["Location"].endswith("/")


def test_setup_rejects_invalid_logo_extension(setup_client, setup_app):
    """Setup should reject non-image logo uploads and avoid creating admin data."""
    response = setup_client.post(
        "/setup-admin",
        data={
            "business_name": "Northside Auto",
            "username": "owner",
            "password": "supersecure",
            "confirm_password": "supersecure",
            "business_logo": (BytesIO(b"not an image"), "logo.txt"),
        },
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert b"Logo must be one of:" in response.data

    with setup_app.app_context():
        assert User.query.count() == 0
        assert BusinessSettings.query.count() == 0


def test_login_honors_safe_next_redirect(setup_client):
    """Login should return users to a safe local next URL when provided."""
    setup_client.post(
        "/setup-admin",
        data={
            "business_name": "Northside Auto",
            "username": "owner",
            "password": "supersecure",
            "confirm_password": "supersecure",
        },
        follow_redirects=False,
    )

    response = setup_client.post(
        "/login?next=/customers/",
        data={"username": "owner", "password": "supersecure", "next": "/customers/"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/customers/")


def test_login_ignores_unsafe_next_redirect(setup_client):
    """External next URLs should be ignored in favor of dashboard redirect."""
    setup_client.post(
        "/setup-admin",
        data={
            "business_name": "Northside Auto",
            "username": "owner",
            "password": "supersecure",
            "confirm_password": "supersecure",
        },
        follow_redirects=False,
    )

    response = setup_client.post(
        "/login?next=https://evil.example",
        data={"username": "owner", "password": "supersecure", "next": "https://evil.example"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")
