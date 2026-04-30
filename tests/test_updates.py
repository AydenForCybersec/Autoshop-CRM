"""Tests for admin update management routes."""

import pytest

from autoshop_crm import create_app
from autoshop_crm.extensions import db
from autoshop_crm.models.settings import BusinessSettings
from autoshop_crm.models.user import User


@pytest.fixture
def updates_app():
    """Create a test app for update route behavior."""
    app = create_app()
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        WTF_CSRF_ENABLED=False,
        LOGIN_DISABLED=True,
        UPDATE_ENABLED=True,
        UPDATE_LOCAL_ONLY=False,
        UPDATE_CONFIRM_PHRASE="CONFIRM",
    )

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def updates_client(updates_app):
    return updates_app.test_client()


class FakeUpdateManager:
    """Controllable double for update route tests."""

    def __init__(self):
        self.rollback_steps = None

    def status(self, *, fetch=False):
        return {
            "enabled": True,
            "has_update": bool(fetch),
            "current_short_commit": "11111111",
            "latest_short_commit": "22222222",
            "behind_by": 1 if fetch else 0,
            "rollback_points": [
                {"short_commit": "11111111", "timestamp_utc": "2026-02-15T00:00:00+00:00"}
            ],
        }

    def apply_update(self):
        return {"updated": True, "from_commit": "1111111111111111", "to_commit": "2222222222222222"}

    def rollback(self, *, steps=1):
        self.rollback_steps = steps
        return {"from_commit": "2222222222222222", "to_commit": "1111111111111111"}


def test_updates_page_renders(updates_client, monkeypatch):
    """Admin updates page should render status content."""
    manager = FakeUpdateManager()
    monkeypatch.setattr("autoshop_crm.routes.admin.updates_ui._get_update_manager", lambda: manager)

    response = updates_client.get("/admin/updates")

    assert response.status_code == 200
    assert b"Updates" in response.data
    assert b"11111111" in response.data


def test_updates_check_returns_json(updates_client, monkeypatch):
    """Check endpoint should return JSON status."""
    manager = FakeUpdateManager()
    monkeypatch.setattr("autoshop_crm.routes.admin.updates_ui._get_update_manager", lambda: manager)

    response = updates_client.post("/admin/updates/check")

    assert response.status_code == 200
    data = response.get_json()
    assert data["ok"] is True
    assert "has_update" in data


def test_updates_apply_requires_confirm(updates_client, monkeypatch):
    """Apply should be blocked without correct confirmation phrase."""
    manager = FakeUpdateManager()
    monkeypatch.setattr("autoshop_crm.routes.admin.updates_ui._get_update_manager", lambda: manager)

    response = updates_client.post("/admin/updates/apply", data={"confirm_text": "WRONG"})

    data = response.get_json()
    assert data["ok"] is False
    assert "confirmation" in data["error"].lower()


def test_updates_apply_succeeds_with_correct_phrase(updates_client, monkeypatch):
    """Apply should call manager and return success JSON."""
    manager = FakeUpdateManager()
    monkeypatch.setattr("autoshop_crm.routes.admin.updates_ui._get_update_manager", lambda: manager)

    response = updates_client.post("/admin/updates/apply", data={"confirm_text": "CONFIRM"})

    data = response.get_json()
    assert data["ok"] is True


def test_updates_rollback_passes_steps(updates_client, monkeypatch):
    """Rollback endpoint should pass steps to manager."""
    manager = FakeUpdateManager()
    monkeypatch.setattr("autoshop_crm.routes.admin.updates_ui._get_update_manager", lambda: manager)

    response = updates_client.post("/admin/updates/rollback", data={"confirm_text": "CONFIRM", "steps": "2"})

    data = response.get_json()
    assert data["ok"] is True
    assert manager.rollback_steps == 2


@pytest.fixture
def updates_rbac_app():
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
        db.session.add_all([admin, mechanic, BusinessSettings(shop_name="Northside Auto", setup_complete=True)])
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def updates_rbac_client(updates_rbac_app):
    return updates_rbac_app.test_client()


def _login(client, username: str, password: str = "supersecure") -> None:
    response = client.post("/login", data={"username": username, "password": password}, follow_redirects=False)
    assert response.status_code == 302


def test_mechanic_cannot_access_admin_updates(updates_rbac_client):
    """Mechanic users should be blocked from admin updates route."""
    _login(updates_rbac_client, "mech")

    response = updates_rbac_client.get("/admin/updates", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")
