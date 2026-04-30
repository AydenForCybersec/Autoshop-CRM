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


def test_user_management_actions_removed_from_settings(rbac_client, rbac_app):
    """User/permission management actions are no longer handled at /settings (moved to /admin)."""
    _login(rbac_client, "admin")

    # create_user is no longer handled — settings page renders with "Unknown settings action"
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
    assert create_response.status_code == 200

    with rbac_app.app_context():
        user = User.query.filter_by(username="bookkeeper").first()
        assert user is None

    # update_permissions is no longer handled — settings page renders with "Unknown settings action"
    with rbac_app.app_context():
        existing = User.query.filter_by(username="mech").first()
        user_id = existing.id

    perm_response = rbac_client.post(
        "/settings?tab=permissions",
        data={
            "action": "update_permissions",
            "active_tab": "permissions",
            "user_id": str(user_id),
            "permissions": ["view_dashboard"],
        },
        follow_redirects=False,
    )
    assert perm_response.status_code == 200

    with rbac_app.app_context():
        mech = User.query.filter_by(username="mech").first()
        assert mech.permission_overrides == {} or mech.permission_overrides is None


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
