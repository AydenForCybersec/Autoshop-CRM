"""Tests for role-based authorization and user management."""

import pytest

from autoshop_crm import create_app
from autoshop_crm.extensions import db
from autoshop_crm.models.settings import BusinessSettings
from autoshop_crm.models.user import User


@pytest.fixture
def rbac_app():
    """Create a test app with auth enabled for RBAC checks."""
    app = create_app()
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        WTF_CSRF_ENABLED=False,
        LOGIN_DISABLED=False,
    )

    with app.app_context():
        db.create_all()
        admin = User(username="admin", role="admin")
        admin.set_password("supersecure")
        mechanic = User(username="mech", role="mechanic")
        mechanic.set_password("supersecure")
        db.session.add_all(
            [
                admin,
                mechanic,
                BusinessSettings(shop_name="Northside Auto", setup_complete=True),
            ]
        )
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def rbac_client(rbac_app):
    """Return test client for RBAC suite."""
    return rbac_app.test_client()


def _login(client, username: str, password: str = "supersecure") -> None:
    """Authenticate a test user."""
    response = client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")


def test_mechanic_cannot_access_accounting(rbac_client):
    """Mechanic role should not be allowed to load accounting reports."""
    _login(rbac_client, "mech")

    response = rbac_client.get("/accounting/", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")


def test_admin_can_create_user_and_set_permission_overrides(rbac_client, rbac_app):
    """Admin should be able to create users and apply granular permission overrides."""
    _login(rbac_client, "admin")

    create_response = rbac_client.post(
        "/settings?tab=users",
        data={
            "action": "create_user",
            "active_tab": "users",
            "new_username": "bookkeeper",
            "new_role": "accountant",
            "new_password": "supersecure",
        },
        follow_redirects=False,
    )
    assert create_response.status_code == 302
    assert create_response.headers["Location"].endswith("/settings?tab=users")

    with rbac_app.app_context():
        user = User.query.filter_by(username="bookkeeper").first()
        assert user is not None
        assert user.role == "accountant"

    perm_response = rbac_client.post(
        "/settings?tab=permissions",
        data={
            "action": "update_permissions",
            "active_tab": "permissions",
            "user_id": str(user.id),
            "permissions": ["view_dashboard", "view_accounting", "export_accounting", "view_customers"],
        },
        follow_redirects=False,
    )
    assert perm_response.status_code == 302
    assert perm_response.headers["Location"].endswith("/settings?tab=permissions")

    with rbac_app.app_context():
        updated = User.query.get(user.id)
        assert updated is not None
        assert updated.can("view_accounting") is True
        assert updated.can("view_customers") is True


def test_inactive_users_cannot_log_in(rbac_client, rbac_app):
    """Disabled accounts should be prevented from authenticating."""
    with rbac_app.app_context():
        user = User.query.filter_by(username="mech").first()
        assert user is not None
        user.is_active = False
        db.session.commit()

    response = rbac_client.post(
        "/login",
        data={"username": "mech", "password": "supersecure"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"This account is disabled" in response.data
