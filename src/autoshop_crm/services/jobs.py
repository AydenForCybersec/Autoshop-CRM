"""Job service functions for work-order lifecycle operations."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy.orm import joinedload

from ..extensions import db
from ..models.job import JOB_STATUSES, Job, JobExpense, JobLabor, JobPart
from .time import utc_now_naive


def get_job(job_id: int) -> Job:
    """Fetch one job by id or raise 404."""
    return Job.query.get_or_404(job_id)


def get_jobs_for_vehicle(vehicle_id: int) -> list[Job]:
    """Return all jobs associated with a vehicle id."""
    return (
        Job.query.filter_by(vehicle_id=vehicle_id)
        .options(joinedload(Job.parts), joinedload(Job.expenses), joinedload(Job.labor))
        .order_by(Job.created_at.desc(), Job.id.desc())
        .all()
    )


def create_job(
    vehicle_id: int,
    description: str,
    cost: Optional[float] = None,
    created_at: Optional[datetime] = None,
) -> Job:
    """Create and persist a job/work-order."""
    job = Job(
        vehicle_id=vehicle_id,
        description=description.strip(),
        cost=cost,
        created_at=created_at or utc_now_naive(),
    )
    db.session.add(job)
    db.session.commit()
    return job


def update_job_status(job: Job, status: str) -> Job:
    """Update a job status and persist the change."""
    normalized = (status or "").strip().lower()
    if normalized not in JOB_STATUSES:
        raise ValueError("Invalid job status.")
    job.status = normalized
    db.session.commit()
    return job


def update_job_cost(job: Job, cost: float | None) -> Job:
    """Update editable total cost for a repair."""
    if cost is not None and cost < 0:
        raise ValueError("Cost cannot be negative.")
    job.cost = cost
    db.session.commit()
    return job


def _safe_add_years(base_date: date, years: int) -> date:
    """Return a date shifted by years, preserving month/day when possible."""
    try:
        return base_date.replace(year=base_date.year + years)
    except ValueError:
        # Handles leap-day warranties that expire on non-leap years.
        return base_date.replace(month=2, day=28, year=base_date.year + years)


def create_job_part(
    *,
    job: Job,
    part_name: str,
    unit_price: float | None = None,
    supplier: str | None = None,
    warranty_years: int | None = None,
    purchased_on: date | None = None,
    notes: str | None = None,
) -> JobPart:
    """Create a part line item for a job and persist it."""
    normalized_supplier = supplier.strip() if supplier and supplier.strip() else None
    normalized_notes = notes.strip() if notes and notes.strip() else None
    effective_purchased_on = purchased_on or (job.created_at.date() if job.created_at else utc_now_naive().date())
    expires_on = None
    if warranty_years and warranty_years > 0:
        expires_on = _safe_add_years(effective_purchased_on, warranty_years)

    part = JobPart(
        job_id=job.id,
        part_name=part_name.strip(),
        unit_price=float(unit_price) if unit_price is not None else None,
        supplier=normalized_supplier,
        warranty_years=warranty_years,
        purchased_on=effective_purchased_on,
        warranty_expires_on=expires_on,
        notes=normalized_notes,
    )
    db.session.add(part)
    db.session.flush()
    db.session.expire(job)
    job.cost = round(job.parts_total + job.labor_total, 2)
    db.session.commit()
    return part


def get_active_warranty_parts_for_vehicle(
    *,
    vehicle_id: int,
    as_of: date | None = None,
) -> list[JobPart]:
    """Return parts for a vehicle whose warranty is still active."""
    reference = as_of or utc_now_naive().date()
    return (
        JobPart.query.join(Job, JobPart.job_id == Job.id)
        .options(joinedload(JobPart.job))
        .filter(Job.vehicle_id == vehicle_id)
        .filter(JobPart.warranty_expires_on.isnot(None))
        .filter(JobPart.warranty_expires_on >= reference)
        .order_by(JobPart.warranty_expires_on.asc(), JobPart.purchased_on.desc(), JobPart.id.desc())
        .all()
    )


def create_job_labor(
    *,
    job: Job,
    user_id: int | None,
    hours: float,
    rate_at_time: float,
    notes: str | None = None,
) -> JobLabor:
    """Create a labor entry for a job and persist it."""
    entry = JobLabor(
        job_id=job.id,
        user_id=user_id,
        hours=hours,
        rate_at_time=rate_at_time,
        notes=notes.strip() if notes and notes.strip() else None,
        created_at=utc_now_naive(),
    )
    db.session.add(entry)
    db.session.flush()
    db.session.expire(job)
    job.cost = round(job.parts_total + job.labor_total, 2)
    db.session.commit()
    return entry


def create_job_expense(
    *,
    job: Job,
    description: str,
    amount: float,
    vendor: str | None = None,
    incurred_on: date | None = None,
    notes: str | None = None,
) -> JobExpense:
    """Create an expense line item for a job and persist it."""
    effective_date = incurred_on or (job.created_at.date() if job.created_at else utc_now_naive().date())
    normalized_vendor = vendor.strip() if vendor and vendor.strip() else None
    normalized_notes = notes.strip() if notes and notes.strip() else None

    expense = JobExpense(
        job_id=job.id,
        description=description.strip(),
        amount=float(amount),
        vendor=normalized_vendor,
        incurred_on=effective_date,
        notes=normalized_notes,
    )
    db.session.add(expense)
    db.session.commit()
    return expense
