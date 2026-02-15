"""Tests for production runtime configuration safeguards."""

import pytest

from autoshop_crm import create_app


def test_production_requires_non_placeholder_secret(monkeypatch):
    """Production boot should fail when SECRET_KEY is placeholder text."""
    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "change-me-in-production")

    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app()


def test_production_secure_defaults(monkeypatch):
    """Production config should enable secure defaults when SECRET_KEY is valid."""
    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "a-very-strong-secret")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")

    app = create_app()

    assert app.config["SESSION_COOKIE_SECURE"] is True
    assert app.config["REMEMBER_COOKIE_SECURE"] is True
    assert app.config["TEMPLATES_AUTO_RELOAD"] is False
