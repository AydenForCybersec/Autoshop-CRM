"""Accounting and reporting routes."""

from __future__ import annotations

from datetime import datetime, timedelta
import csv
import io

from flask import Blueprint, Response, flash, redirect, render_template, request, url_for
from flask.typing import ResponseReturnValue
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from ..models.job import Job
from ..models.settings import BusinessSettings
from ..models.vehicle import Vehicle
from ..services.authorization import require_permission
from ..services.dates import parse_optional_datetime

accounting_bp = Blueprint("accounting", __name__)


def _date_window() -> tuple[datetime | None, datetime | None, str, str]:
    """Parse optional start/end date query params."""
    start_raw = request.args.get("start_date", "").strip()
    end_raw = request.args.get("end_date", "").strip()

    try:
        start_dt = parse_optional_datetime(start_raw) if start_raw else None
        end_dt = parse_optional_datetime(end_raw) if end_raw else None
    except ValueError as exc:
        raise ValueError(str(exc)) from exc
    if end_dt:
        end_dt = end_dt + timedelta(days=1)
    return start_dt, end_dt, start_raw, end_raw


def _jobs_query(start_dt: datetime | None, end_dt: datetime | None):
    """Build a filtered jobs query."""
    query = Job.query.options(
        joinedload(Job.vehicle).joinedload(Vehicle.customer),
        joinedload(Job.parts),
    )
    if start_dt:
        query = query.filter(Job.created_at >= start_dt)
    if end_dt:
        query = query.filter(Job.created_at < end_dt)
    return query


def _job_price_breakdown(job: Job, tax_percentage: float) -> dict[str, float]:
    """Return accounting-friendly part/labor/subtotal/tax/total values for one job."""
    parts_total = float(sum((part.part_price or 0.0) for part in job.parts))
    labor_total = float(sum((part.labor_cost or 0.0) for part in job.parts))
    has_line_items = bool(job.parts)
    subtotal = float(parts_total + labor_total)

    if has_line_items:
        tax_amount = subtotal * (tax_percentage / 100.0)
        total = subtotal + tax_amount
    else:
        # Preserve legacy rows that only store a total cost without part/labor lines.
        tax_amount = 0.0
        total = float(job.cost or 0.0)
        subtotal = total

    return {
        "parts_total": parts_total,
        "labor_total": labor_total,
        "subtotal": subtotal,
        "tax_amount": tax_amount,
        "total": total,
    }


@accounting_bp.route("/")
@require_permission("view_accounting")
def index() -> ResponseReturnValue:
    """Render accounting summary and transaction list."""
    try:
        start_dt, end_dt, start_raw, end_raw = _date_window()
    except ValueError as exc:
        flash(str(exc))
        return redirect(url_for("accounting.index"))
    settings = BusinessSettings.query.first()
    tax_percentage = float(settings.tax_percentage if settings and settings.tax_percentage is not None else 0.0)

    jobs_query = _jobs_query(start_dt, end_dt)
    jobs = jobs_query.order_by(Job.created_at.desc(), Job.id.desc()).limit(200).all()
    job_rows = [{"job": job, **_job_price_breakdown(job, tax_percentage)} for job in jobs]

    totals_query = _jobs_query(start_dt, end_dt)
    total_revenue = totals_query.with_entities(func.sum(Job.cost)).filter(Job.status == "completed").scalar() or 0.0

    open_pipeline = (
        _jobs_query(start_dt, end_dt)
        .with_entities(func.sum(Job.cost))
        .filter(Job.status.in_(("open", "in_progress", "on_hold")))
        .scalar()
    ) or 0.0

    avg_ticket = (
        _jobs_query(start_dt, end_dt)
        .with_entities(func.avg(Job.cost))
        .filter(Job.cost.isnot(None))
        .scalar()
    ) or 0.0
    completed_jobs = _jobs_query(start_dt, end_dt).filter(Job.status == "completed").all()
    completed_parts_revenue = float(sum((_job_price_breakdown(job, tax_percentage)["parts_total"] for job in completed_jobs)))
    completed_labor_revenue = float(sum((_job_price_breakdown(job, tax_percentage)["labor_total"] for job in completed_jobs)))

    return render_template(
        "accounting/index.html",
        job_rows=job_rows,
        total_revenue=total_revenue,
        open_pipeline=open_pipeline,
        avg_ticket=avg_ticket,
        completed_parts_revenue=completed_parts_revenue,
        completed_labor_revenue=completed_labor_revenue,
        start_date=start_raw,
        end_date=end_raw,
    )


@accounting_bp.route("/jobs.csv")
@require_permission("export_accounting")
def jobs_csv() -> ResponseReturnValue:
    """Export a CSV ledger of jobs with date filters applied."""
    try:
        start_dt, end_dt, _, _ = _date_window()
    except ValueError as exc:
        return Response(str(exc), status=400, mimetype="text/plain")
    settings = BusinessSettings.query.first()
    tax_percentage = float(settings.tax_percentage if settings and settings.tax_percentage is not None else 0.0)
    jobs = _jobs_query(start_dt, end_dt).order_by(Job.created_at.asc(), Job.id.asc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "job_id",
            "job_date",
            "status",
            "cost",
            "parts_total",
            "labor_total",
            "subtotal",
            "tax_amount",
            "total_with_tax",
            "description",
            "vehicle_id",
            "customer_id",
            "vehicle_make",
            "vehicle_model",
            "vehicle_year",
        ]
    )
    for job in jobs:
        breakdown = _job_price_breakdown(job, tax_percentage)
        writer.writerow(
            [
                job.id,
                job.created_at.isoformat() if job.created_at else "",
                job.status,
                job.cost if job.cost is not None else "",
                breakdown["parts_total"],
                breakdown["labor_total"],
                breakdown["subtotal"],
                breakdown["tax_amount"],
                breakdown["total"],
                job.description,
                job.vehicle_id,
                job.vehicle.customer_id if job.vehicle else "",
                job.vehicle.make if job.vehicle else "",
                job.vehicle.model if job.vehicle else "",
                job.vehicle.year if job.vehicle else "",
            ]
        )

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": 'attachment; filename="job-ledger.csv"'},
    )
