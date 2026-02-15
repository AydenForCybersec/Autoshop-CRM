"""Tests for update management routes."""

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
    )

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def updates_client(updates_app):
    """Return test client for update route suite."""
    return updates_app.test_client()


class FakeUpdateManager:
    """Simple controllable double for update route tests."""

    def __init__(self):
        self.rollback_steps = None

    def status(self, *, fetch=False):
        return {
            "enabled": True,
            "repo_path": "/tmp/repo",
            "remote": "origin",
            "branch": "main",
            "is_git_repo": True,
            "current_commit": "1111111111111111",
            "current_short_commit": "11111111",
            "latest_commit": "2222222222222222",
            "latest_short_commit": "22222222",
            "dirty": False,
            "ahead_by": 0,
            "behind_by": 1 if fetch else 0,
            "has_update": bool(fetch),
            "rollback_points": [
                {"commit": "1111111111111111", "short_commit": "11111111", "timestamp_utc": "2026-02-15T00:00:00+00:00"}
            ],
            "error": None,
        }

    def apply_update(self):
        return {"updated": True, "from_commit": "1111111111111111", "to_commit": "2222222222222222"}

    def rollback(self, *, steps=1):
        self.rollback_steps = steps
        return {
            "rolled_back": True,
            "from_commit": "2222222222222222",
            "to_commit": "1111111111111111",
            "steps": steps,
        }


def test_updates_page_renders_status(updates_client, monkeypatch):
    """Updates page should render status content from manager."""
    manager = FakeUpdateManager()
    monkeypatch.setattr("autoshop_crm.routes.updates.get_update_manager", lambda: manager)

    response = updates_client.get("/updates")

    assert response.status_code == 200
    assert b"Application Updates" in response.data
    assert b"11111111" in response.data


def test_updates_apply_action_redirects_with_success_flash(updates_client, monkeypatch):
    """Apply action should execute manager update and flash success."""
    manager = FakeUpdateManager()
    monkeypatch.setattr("autoshop_crm.routes.updates.get_update_manager", lambda: manager)

    response = updates_client.post("/updates", data={"action": "apply"}, follow_redirects=True)

    assert response.status_code == 200
    assert b"Update applied successfully" in response.data


def test_updates_rollback_two_calls_manager(updates_client, monkeypatch):
    """Rollback by two should pass steps=2 into manager."""
    manager = FakeUpdateManager()
    monkeypatch.setattr("autoshop_crm.routes.updates.get_update_manager", lambda: manager)

    response = updates_client.post("/updates", data={"action": "rollback_2"}, follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/updates")
    assert manager.rollback_steps == 2


@pytest.fixture
def updates_rbac_app():
    """Create app with auth enabled for permission checks."""
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
    """Return client for update RBAC checks."""
    return updates_rbac_app.test_client()


def _login(client, username: str, password: str = "supersecure") -> None:
    response = client.post("/login", data={"username": username, "password": password}, follow_redirects=False)
    assert response.status_code == 302


def test_mechanic_cannot_access_updates(updates_rbac_client):
    """Mechanic users should be blocked from update manager route."""
    _login(updates_rbac_client, "mech")

    response = updates_rbac_client.get("/updates", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")
