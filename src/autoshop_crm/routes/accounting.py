"""Accounting and reporting routes."""

from __future__ import annotations

from datetime import datetime, timedelta
import csv
import io

from flask import Blueprint, Response, flash, redirect, render_template, request, url_for
from flask.typing import ResponseReturnValue
from sqlalchemy import func

from datetime import date

from sqlalchemy.orm import joinedload

from ..extensions import db
from ..models.job import Job
from ..models.vehicle import Vehicle
from ..models.settings import BusinessSettings
from ..services.authorization import require_permission
from ..services.dates import parse_optional_datetime


class _JobRow:
    """Thin wrapper that precomputes per-job totals for the accounting template."""

    __slots__ = ("job", "parts_total", "labor_total", "subtotal", "tax_amount", "total")

    def __init__(self, job: Job, tax_rate: float) -> None:
        self.job = job
        self.parts_total = job.parts_total
        self.labor_total = job.labor_total
        self.subtotal = round(self.parts_total + self.labor_total, 2)
        self.tax_amount = round(self.subtotal * tax_rate / 100, 2)
        self.total = round(self.subtotal + self.tax_amount, 2)

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
    query = Job.query.join(Vehicle, Vehicle.id == Job.vehicle_id)
    if start_dt:
        query = query.filter(Job.created_at >= start_dt)
    if end_dt:
        query = query.filter(Job.created_at < end_dt)
    return query


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
    tax_rate = (settings.sales_tax_rate or 0.0) if settings else 0.0

    recent_jobs = (
        _jobs_query(start_dt, end_dt)
        .options(joinedload(Job.parts), joinedload(Job.labor))
        .order_by(Job.created_at.desc(), Job.id.desc())
        .limit(5)
        .all()
    )
    job_rows = [_JobRow(j, tax_rate) for j in recent_jobs]

    completed_query = _jobs_query(start_dt, end_dt).filter(Job.status == "completed")
    total_revenue = completed_query.with_entities(func.sum(Job.cost)).scalar() or 0.0

    completed_jobs = (
        completed_query
        .options(joinedload(Job.parts), joinedload(Job.labor))
        .all()
    )
    completed_parts_revenue = round(sum(j.parts_total for j in completed_jobs), 2)
    completed_labor_revenue = round(sum(j.labor_total for j in completed_jobs), 2)

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

    return render_template(
        "accounting/index.html",
        job_rows=job_rows,
        total_revenue=total_revenue,
        completed_parts_revenue=completed_parts_revenue,
        completed_labor_revenue=completed_labor_revenue,
        open_pipeline=open_pipeline,
        avg_ticket=avg_ticket,
        start_date=start_raw,
        end_date=end_raw,
    )


@accounting_bp.route("/invoice-report")
@require_permission("view_accounting")
def invoice_report() -> ResponseReturnValue:
    """Render a printable invoice report for a date range."""
    try:
        start_dt, end_dt, start_raw, end_raw = _date_window()
    except ValueError as exc:
        flash(str(exc))
        return redirect(url_for("accounting.index"))

    from ..models.job import JobLabor
    jobs = (
        _jobs_query(start_dt, end_dt)
        .options(joinedload(Job.parts), joinedload(Job.labor))
        .order_by(Job.created_at.asc(), Job.id.asc())
        .all()
    )
    settings = BusinessSettings.query.first()

    tax_rate = (settings.sales_tax_rate or 0.0) if settings else 0.0

    total_parts = sum(j.parts_total for j in jobs)
    total_labor = sum(j.labor_total for j in jobs)
    total_tax = round((total_parts + total_labor) * tax_rate / 100, 2)
    total_due = sum(j.cost for j in jobs if j.cost is not None)

    return render_template(
        "accounting/invoice_report.html",
        jobs=jobs,
        settings=settings,
        tax_rate=tax_rate,
        start_date=start_raw,
        end_date=end_raw,
        total_parts=total_parts,
        total_labor=total_labor,
        total_tax=total_tax,
        total_due=total_due,
        print_date=date.today().strftime("%A, %B %-d, %Y"),
    )


@accounting_bp.route("/jobs.csv")
@require_permission("export_accounting")
def jobs_csv() -> ResponseReturnValue:
    """Export a CSV ledger of jobs with date filters applied."""
    try:
        start_dt, end_dt, _, _ = _date_window()
    except ValueError as exc:
        return Response(str(exc), status=400, mimetype="text/plain")
    jobs = _jobs_query(start_dt, end_dt).order_by(Job.created_at.asc(), Job.id.asc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "job_id",
            "job_date",
            "status",
            "cost",
            "description",
            "vehicle_id",
            "customer_id",
            "vehicle_make",
            "vehicle_model",
            "vehicle_year",
        ]
    )
    for job in jobs:
        writer.writerow(
            [
                job.id,
                job.created_at.isoformat() if job.created_at else "",
                job.status,
                job.cost if job.cost is not None else "",
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
