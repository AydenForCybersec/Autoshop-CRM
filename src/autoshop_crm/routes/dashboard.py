"""Dashboard and application settings routes."""

from __future__ import annotations

import re

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask.typing import ResponseReturnValue
from sqlalchemy import func, inspect
from sqlalchemy.orm import joinedload

from ..extensions import db
from ..models.customer import Customer
from ..models.job import Job
from ..models.settings import BusinessSettings
from ..models.ui_preference import AppPreference
from ..models.vehicle import Vehicle
from ..services.authorization import (
    can_current_user,
    require_permission,
)
from ..services.branding import save_business_logo

dashboard_bp = Blueprint("dashboard", __name__)

HEX_COLOR_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}$")
STATUS_LABELS = {
    "open": "Open",
    "in_progress": "In Progress",
    "on_hold": "On Hold",
    "completed": "Completed",
}
SETTINGS_TABS = {"business", "theme"}


def _is_valid_hex_color(value: str) -> bool:
    """Return True when value is a 6-digit hex color like #1f7a4f."""
    return bool(HEX_COLOR_PATTERN.fullmatch(value.strip()))


def _ensure_preference_table() -> None:
    """Create preferences table on demand for existing deployments."""
    engine = db.session.get_bind()
    if not inspect(engine).has_table(AppPreference.__tablename__):
        AppPreference.__table__.create(bind=engine)


def _get_or_create_preferences() -> AppPreference:
    """Return singleton app preferences, creating defaults if missing."""
    _ensure_preference_table()
    preferences = AppPreference.query.first()
    if preferences is None:
        preferences = AppPreference()
        db.session.add(preferences)
        db.session.commit()
    return preferences


def _ensure_settings_row() -> BusinessSettings:
    """Return singleton business settings row, creating defaults if missing."""
    settings = BusinessSettings.query.first()
    if settings is None:
        settings = BusinessSettings(shop_name="Autoshop CRM", setup_complete=False, sales_tax_rate=6.225)
        db.session.add(settings)
        db.session.commit()
    return settings


def _active_tab() -> str:
    """Return the currently requested settings tab."""
    tab = request.args.get("tab", "business").strip().lower()
    if tab in SETTINGS_TABS:
        return tab
    return "business"


def _render_settings(
    settings: BusinessSettings,
    preferences: AppPreference,
    *,
    active_tab: str,
    form_values: dict[str, str | int | None] | None = None,
):
    """Render settings page with shared context."""
    return render_template(
        "settings/index.html",
        settings=settings,
        preferences=preferences,
        form_values=form_values or {},
        active_tab=active_tab,
    )


@dashboard_bp.route("/")
@require_permission("view_dashboard")
def index() -> ResponseReturnValue:
    """Render the operational dashboard."""
    prefs = _get_or_create_preferences()
    job_limit = max(3, min(20, prefs.dashboard_jobs_limit or 6))

    status_rows = db.session.query(Job.status, func.count(Job.id)).group_by(Job.status).all()
    status_counts = {status: 0 for status in STATUS_LABELS}
    for status, count in status_rows:
        normalized = (status or "open").strip().lower()
        if normalized in status_counts:
            status_counts[normalized] = count

    total_jobs = sum(status_counts.values())
    completed_jobs = status_counts["completed"]
    active_jobs = status_counts["open"] + status_counts["in_progress"] + status_counts["on_hold"]
    completion_rate = round((completed_jobs / total_jobs) * 100, 1) if total_jobs else 0

    totals = {
        "customers": db.session.query(func.count(Customer.id)).scalar() or 0,
        "vehicles": db.session.query(func.count(Vehicle.id)).scalar() or 0,
        "jobs": total_jobs,
        "active_jobs": active_jobs,
    }

    open_pipeline_value = (
        db.session.query(func.sum(Job.cost))
        .filter(Job.status.in_(("open", "in_progress", "on_hold")))
        .scalar()
    ) or 0

    recent_jobs = (
        Job.query.options(joinedload(Job.vehicle).joinedload(Vehicle.customer))
        .order_by(Job.id.desc())
        .limit(job_limit)
        .all()
    )

    return render_template(
        "dashboard/index.html",
        totals=totals,
        status_counts=status_counts,
        status_labels=STATUS_LABELS,
        completion_rate=completion_rate,
        open_pipeline_value=open_pipeline_value,
        recent_jobs=recent_jobs,
    )


@dashboard_bp.route("/settings", methods=["GET", "POST"])
@require_permission("manage_settings")
def settings() -> ResponseReturnValue:
    """Render and update business and UI settings."""
    settings = _ensure_settings_row()
    preferences = _get_or_create_preferences()
    active_tab = _active_tab()

    if request.method == "POST":
        action = request.form.get("action", "").strip().lower()
        requested_tab = request.form.get("active_tab", active_tab).strip().lower()
        if requested_tab in SETTINGS_TABS:
            active_tab = requested_tab

        if action == "update_business":
            existing_shop_name = settings.shop_name
            shop_name_input = request.form.get("shop_name", existing_shop_name).strip()
            shop_phone = request.form.get("shop_phone", "").strip() or None
            shop_email = request.form.get("shop_email", "").strip() or None
            shop_address = request.form.get("shop_address", "").strip() or None

            form_values = {
                "shop_name": shop_name_input or existing_shop_name,
                "shop_phone": shop_phone or "",
                "shop_email": shop_email or "",
                "shop_address": shop_address or "",
            }

            try:
                uploaded_logo = save_business_logo(request.files.get("business_logo"), current_app.static_folder)
            except ValueError as exc:
                flash(str(exc))
                return _render_settings(
                    settings,
                    preferences,
                    active_tab=active_tab,
                    form_values=form_values,
                )

            settings.shop_name = shop_name_input or existing_shop_name
            settings.shop_phone = shop_phone
            settings.shop_email = shop_email
            settings.shop_address = shop_address
            if uploaded_logo:
                settings.shop_logo = uploaded_logo

            for rate_field in ("sales_tax_rate", "card_fee_rate"):
                raw = request.form.get(rate_field, "").strip()
                setattr(settings, rate_field, float(raw) if raw else None)

            db.session.commit()
            flash("Business profile updated.")
            return redirect(url_for("dashboard.settings", tab="business"))

        if action == "update_theme":
            if not can_current_user("manage_theme"):
                flash("You do not have permission to modify theme settings.")
                return redirect(url_for("dashboard.settings", tab="theme"))

            color_fields = (
                "primary_color",
                "accent_color",
                "background_color",
                "surface_color",
                "text_color",
                "muted_color",
                "line_color",
                "success_color",
                "warning_color",
                "danger_color",
            )
            form_values: dict[str, str | int | None] = {}
            for field in color_fields:
                current_value = getattr(preferences, field)
                form_values[field] = request.form.get(field, current_value).strip() or current_value

            jobs_limit_raw = request.form.get("dashboard_jobs_limit", str(preferences.dashboard_jobs_limit)).strip()
            radius_raw = request.form.get("radius_px", str(preferences.radius_px)).strip()
            form_values["dashboard_jobs_limit"] = jobs_limit_raw
            form_values["radius_px"] = radius_raw

            if not all(_is_valid_hex_color(str(form_values[field])) for field in color_fields):
                flash("Theme colors must be valid hex values like #1f7a4f.")
                return _render_settings(
                    settings,
                    preferences,
                    active_tab=active_tab,
                    form_values=form_values,
                )

            try:
                jobs_limit = int(jobs_limit_raw)
            except ValueError:
                flash("Dashboard jobs limit must be a number between 3 and 20.")
                return _render_settings(
                    settings,
                    preferences,
                    active_tab=active_tab,
                    form_values=form_values,
                )

            if jobs_limit < 3 or jobs_limit > 20:
                flash("Dashboard jobs limit must be between 3 and 20.")
                return _render_settings(
                    settings,
                    preferences,
                    active_tab=active_tab,
                    form_values=form_values,
                )

            try:
                radius = int(radius_raw)
            except ValueError:
                flash("Corner radius must be a number between 6 and 28.")
                return _render_settings(
                    settings,
                    preferences,
                    active_tab=active_tab,
                    form_values=form_values,
                )

            if radius < 6 or radius > 28:
                flash("Corner radius must be between 6 and 28.")
                return _render_settings(
                    settings,
                    preferences,
                    active_tab=active_tab,
                    form_values=form_values,
                )

            for field in color_fields:
                setattr(preferences, field, str(form_values[field]))
            preferences.dashboard_jobs_limit = jobs_limit
            preferences.radius_px = radius

            db.session.commit()
            flash("Theme and dashboard preferences updated.")
            return redirect(url_for("dashboard.settings", tab="theme"))

        flash("Unknown settings action.")

    return _render_settings(settings, preferences, active_tab=active_tab)
