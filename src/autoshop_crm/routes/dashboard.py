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
from ..services.branding import save_business_logo

dashboard_bp = Blueprint("dashboard", __name__)

HEX_COLOR_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}$")
STATUS_LABELS = {
    "open": "Open",
    "in_progress": "In Progress",
    "on_hold": "On Hold",
    "completed": "Completed",
}


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


@dashboard_bp.route("/")
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
def settings() -> ResponseReturnValue:
    """Render and update business + UI settings."""
    settings = BusinessSettings.query.first()
    if settings is None:
        settings = BusinessSettings(shop_name="Autoshop CRM", setup_complete=False)
        db.session.add(settings)
        db.session.commit()

    preferences = _get_or_create_preferences()
    form_values: dict[str, str | int | None] = {}

    if request.method == "POST":
        existing_shop_name = settings.shop_name
        shop_name_input = request.form.get("shop_name", existing_shop_name).strip()
        shop_phone = request.form.get("shop_phone", "").strip() or None
        shop_email = request.form.get("shop_email", "").strip() or None
        shop_address = request.form.get("shop_address", "").strip() or None

        primary_color = request.form.get("primary_color", preferences.primary_color).strip() or preferences.primary_color
        accent_color = request.form.get("accent_color", preferences.accent_color).strip() or preferences.accent_color
        background_color = (
            request.form.get("background_color", preferences.background_color).strip() or preferences.background_color
        )
        surface_color = request.form.get("surface_color", preferences.surface_color).strip() or preferences.surface_color
        jobs_limit_raw = request.form.get("dashboard_jobs_limit", str(preferences.dashboard_jobs_limit)).strip()

        form_values = {
            "shop_name": shop_name_input or existing_shop_name,
            "shop_phone": shop_phone or "",
            "shop_email": shop_email or "",
            "shop_address": shop_address or "",
            "primary_color": primary_color,
            "accent_color": accent_color,
            "background_color": background_color,
            "surface_color": surface_color,
            "dashboard_jobs_limit": jobs_limit_raw,
        }

        if not all(
            _is_valid_hex_color(value)
            for value in (primary_color, accent_color, background_color, surface_color)
        ):
            flash("Theme colors must be valid hex values like #1f7a4f.")
            return render_template(
                "settings/index.html", settings=settings, preferences=preferences, form_values=form_values
            )

        try:
            jobs_limit = int(jobs_limit_raw)
        except ValueError:
            flash("Dashboard jobs limit must be a number between 3 and 20.")
            return render_template(
                "settings/index.html", settings=settings, preferences=preferences, form_values=form_values
            )

        if jobs_limit < 3 or jobs_limit > 20:
            flash("Dashboard jobs limit must be between 3 and 20.")
            return render_template(
                "settings/index.html", settings=settings, preferences=preferences, form_values=form_values
            )

        try:
            uploaded_logo = save_business_logo(request.files.get("business_logo"), current_app.static_folder)
        except ValueError as exc:
            flash(str(exc))
            return render_template(
                "settings/index.html", settings=settings, preferences=preferences, form_values=form_values
            )

        settings.shop_name = shop_name_input or existing_shop_name
        settings.shop_phone = shop_phone
        settings.shop_email = shop_email
        settings.shop_address = shop_address
        if uploaded_logo:
            settings.shop_logo = uploaded_logo

        preferences.primary_color = primary_color
        preferences.accent_color = accent_color
        preferences.background_color = background_color
        preferences.surface_color = surface_color
        preferences.dashboard_jobs_limit = jobs_limit

        db.session.commit()
        flash("Settings updated.")
        return redirect(url_for("dashboard.settings"))

    return render_template("settings/index.html", settings=settings, preferences=preferences, form_values=form_values)
