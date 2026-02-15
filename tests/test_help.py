"""Tests for in-app help routes and content registry integrity."""

import pytest

from autoshop_crm import create_app
from autoshop_crm.extensions import db
from autoshop_crm.models.settings import BusinessSettings
from autoshop_crm.models.user import User
from autoshop_crm.services.help import HELP_ARTICLE_REGISTRY, get_help_article, get_help_index


@pytest.fixture
def help_app():
    """Create a test app with auth enabled and one admin user."""
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
        db.session.add(admin)
        db.session.add(BusinessSettings(shop_name="Northside Auto", setup_complete=True))
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def help_client(help_app):
    """Return a test client for help route checks."""
    return help_app.test_client()


def _login(client):
    """Authenticate as seeded admin user."""
    response = client.post(
        "/login",
        data={"username": "admin", "password": "supersecure"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")


def test_help_requires_authentication(help_client):
    """Anonymous users should be redirected to login for help center."""
    response = help_client.get("/help", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_help_home_and_article_render_for_authenticated_user(help_client):
    """Logged-in users can browse help index and article pages."""
    _login(help_client)

    index_response = help_client.get("/help")
    assert index_response.status_code == 200
    assert b"Help Center" in index_response.data

    article_response = help_client.get("/help/getting-started")
    assert article_response.status_code == 200
    assert b"Getting Started" in article_response.data


def test_help_invalid_slug_returns_404(help_client):
    """Unknown help article slugs should return not found."""
    _login(help_client)
    response = help_client.get("/help/not-a-real-article")
    assert response.status_code == 404


def test_help_redirects_to_setup_when_no_users_exist():
    """Before first admin exists, protected help should redirect to setup."""
    app = create_app()
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        WTF_CSRF_ENABLED=False,
        LOGIN_DISABLED=False,
    )

    with app.app_context():
        db.create_all()
        client = app.test_client()
        response = client.get("/help", follow_redirects=False)
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/setup-admin")
        quick_start_response = client.get("/help/quick-start", follow_redirects=False)
        assert quick_start_response.status_code == 200
        assert b"Getting Started" in quick_start_response.data
        db.session.remove()
        db.drop_all()


def test_help_registry_integrity_and_markdown_rendering():
    """Registry entries should be complete and render safe article HTML."""
    assert len(HELP_ARTICLE_REGISTRY) == len(set(HELP_ARTICLE_REGISTRY.keys()))

    index_entries = get_help_index()
    assert index_entries

    for entry in index_entries:
        assert entry.slug
        assert entry.title
        assert entry.summary
        assert entry.audience

        article = get_help_article(entry.slug)
        assert article is not None
        assert "<h1>" in article.content_html

    daily = get_help_article("daily-workflows")
    assert daily is not None
    assert "<ol>" in daily.content_html
    assert "<li>" in daily.content_html
