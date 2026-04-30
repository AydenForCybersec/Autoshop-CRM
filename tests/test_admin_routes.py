import pytest
from autoshop_crm import create_app
from autoshop_crm.extensions import db as _db
from autoshop_crm.models.user import User


@pytest.fixture
def app():
    app = create_app()
    app.config.update({
        "TESTING": True,
        "LOGIN_DISABLED": False,
        "WTF_CSRF_ENABLED": False,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    })
    with app.app_context():
        _db.create_all()
        yield app
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def admin_user(app):
    with app.app_context():
        u = User(username="admin", role="admin")
        u.set_password("password")
        _db.session.add(u)
        _db.session.commit()
        return u


def _login(client, username, password):
    return client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=True,
    )


def test_admin_panel_requires_login(client):
    resp = client.get("/admin", follow_redirects=False)
    assert resp.status_code in (302, 401)


def test_admin_panel_accessible_to_admin(client, admin_user):
    _login(client, "admin", "password")
    resp = client.get("/admin")
    assert resp.status_code == 200


def test_admin_updates_accessible_to_admin(client, admin_user):
    _login(client, "admin", "password")
    resp = client.get("/admin/updates")
    assert resp.status_code == 200


def test_admin_danger_accessible_to_admin(client, admin_user):
    _login(client, "admin", "password")
    resp = client.get("/admin/danger")
    assert resp.status_code == 200
