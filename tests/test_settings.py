"""Tests for settings updates and branding context data."""

from io import BytesIO
from pathlib import Path

import pytest
from flask import render_template_string

from autoshop_crm import create_app
from autoshop_crm.extensions import db
from autoshop_crm.models.settings import BusinessSettings
from autoshop_crm.models.ui_preference import AppPreference


@pytest.fixture
def settings_app(tmp_path):
    """Create an isolated app instance for settings route tests."""
    app = create_app()
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        WTF_CSRF_ENABLED=False,
        LOGIN_DISABLED=True,
    )
    app.static_folder = str(tmp_path / "static")
    Path(app.static_folder).mkdir(parents=True, exist_ok=True)

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def settings_client(settings_app):
    """Return a test client for settings tests."""
    return settings_app.test_client()


def test_settings_update_persists_business_and_preferences(settings_client, settings_app):
    """Posting valid business and theme settings should persist all configured fields."""
    business_response = settings_client.post(
        "/settings",
        data={
            "action": "update_business",
            "active_tab": "business",
            "shop_name": "Northside Auto",
            "shop_phone": "(555) 123-4567",
            "shop_email": "service@northside.test",
            "shop_address": "123 Main St",
        },
        follow_redirects=False,
    )
    assert business_response.status_code == 302
    assert business_response.headers["Location"].endswith("/settings?tab=business")

    theme_response = settings_client.post(
        "/settings",
        data={
            "action": "update_theme",
            "active_tab": "theme",
            "primary_color": "#102030",
            "accent_color": "#405060",
            "background_color": "#708090",
            "surface_color": "#a0b0c0",
            "text_color": "#010203",
            "muted_color": "#112233",
            "line_color": "#223344",
            "success_color": "#334455",
            "warning_color": "#445566",
            "danger_color": "#556677",
            "dashboard_jobs_limit": "8",
            "radius_px": "18",
        },
        follow_redirects=False,
    )
    assert theme_response.status_code == 302
    assert theme_response.headers["Location"].endswith("/settings?tab=theme")

    with settings_app.app_context():
        settings = BusinessSettings.query.first()
        prefs = AppPreference.query.first()
        assert settings is not None
        assert prefs is not None
        assert settings.shop_name == "Northside Auto"
        assert settings.shop_phone == "(555) 123-4567"
        assert settings.shop_email == "service@northside.test"
        assert settings.shop_address == "123 Main St"
        assert prefs.primary_color == "#102030"
        assert prefs.accent_color == "#405060"
        assert prefs.background_color == "#708090"
        assert prefs.surface_color == "#a0b0c0"
        assert prefs.text_color == "#010203"
        assert prefs.muted_color == "#112233"
        assert prefs.line_color == "#223344"
        assert prefs.success_color == "#334455"
        assert prefs.warning_color == "#445566"
        assert prefs.danger_color == "#556677"
        assert prefs.dashboard_jobs_limit == 8
        assert prefs.radius_px == 18


def test_settings_rejects_invalid_hex_color(settings_client, settings_app):
    """Invalid color fields should fail validation and avoid persisting preference changes."""
    response = settings_client.post(
        "/settings",
        data={
            "action": "update_theme",
            "active_tab": "theme",
            "primary_color": "not-a-color",
            "accent_color": "#405060",
            "background_color": "#708090",
            "surface_color": "#a0b0c0",
            "text_color": "#010203",
            "muted_color": "#112233",
            "line_color": "#223344",
            "success_color": "#334455",
            "warning_color": "#445566",
            "danger_color": "#556677",
            "dashboard_jobs_limit": "6",
            "radius_px": "16",
        },
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert b"Theme colors must be valid hex values like #1f7a4f." in response.data
    assert b'value="not-a-color"' in response.data

    with settings_app.app_context():
        prefs = AppPreference.query.first()
        assert prefs is not None
        assert prefs.primary_color == "#1f7a4f"


@pytest.mark.parametrize(
    ("jobs_limit", "expected_message"),
    [
        ("abc", b"Dashboard jobs limit must be a number between 3 and 20."),
        ("2", b"Dashboard jobs limit must be between 3 and 20."),
        ("21", b"Dashboard jobs limit must be between 3 and 20."),
    ],
)
def test_settings_rejects_invalid_jobs_limit(
    settings_client, settings_app, jobs_limit, expected_message
):
    """Non-numeric and out-of-range jobs limits should be rejected."""
    response = settings_client.post(
        "/settings",
        data={
            "action": "update_theme",
            "active_tab": "theme",
            "primary_color": "#102030",
            "accent_color": "#405060",
            "background_color": "#708090",
            "surface_color": "#a0b0c0",
            "text_color": "#010203",
            "muted_color": "#112233",
            "line_color": "#223344",
            "success_color": "#334455",
            "warning_color": "#445566",
            "danger_color": "#556677",
            "dashboard_jobs_limit": jobs_limit,
            "radius_px": "16",
        },
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert expected_message in response.data
    assert f'value="{jobs_limit}"'.encode() in response.data

    with settings_app.app_context():
        prefs = AppPreference.query.first()
        assert prefs is not None
        assert prefs.dashboard_jobs_limit == 6


def test_settings_logo_upload_updates_shop_logo(settings_client, settings_app):
    """Valid logo upload should store a static-relative logo path."""
    response = settings_client.post(
        "/settings",
        data={
            "action": "update_business",
            "active_tab": "business",
            "shop_name": "Northside Auto",
            "shop_phone": "",
            "shop_email": "",
            "shop_address": "",
            "business_logo": (BytesIO(b"fake image bytes"), "brand.png"),
        },
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/settings?tab=business")

    with settings_app.app_context():
        settings = BusinessSettings.query.first()
        assert settings is not None
        assert settings.shop_logo is not None
        assert settings.shop_logo.startswith("uploads/logos/brand-")
        assert settings.shop_logo.endswith(".png")
        assert Path(settings_app.static_folder, settings.shop_logo).exists()


def test_branding_context_uses_shop_name_and_initials_fallback(settings_app):
    """Branding context should include app name and initials when no logo is configured."""
    with settings_app.app_context():
        db.session.add(BusinessSettings(shop_name="Northside Auto", setup_complete=True))
        db.session.commit()

    with settings_app.test_request_context("/"):
        rendered = render_template_string("{{ app_name }}|{{ app_initials }}|{{ app_logo_url or '' }}")

    assert rendered == "Northside Auto|NA|"


def test_branding_context_exposes_theme_vars(settings_app):
    """Theme color preferences should be exposed through template context vars."""
    with settings_app.app_context():
        db.session.add(BusinessSettings(shop_name="Northside Auto", setup_complete=True))
        db.session.add(
            AppPreference(
                primary_color="#010203",
                accent_color="#111213",
                background_color="#212223",
                surface_color="#313233",
                dashboard_jobs_limit=6,
            )
        )
        db.session.commit()

    with settings_app.test_request_context("/"):
        rendered = render_template_string(
            "{{ theme_vars['--brand'] }}|{{ theme_vars['--highlight'] }}|"
            "{{ theme_vars['--bg'] }}|{{ theme_vars['--surface'] }}"
        )

    assert rendered == "#010203|#111213|#212223|#313233"
