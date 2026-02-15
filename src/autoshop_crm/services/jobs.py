"""Job service functions for work-order lifecycle operations."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from ..extensions import db
from ..models.job import JOB_STATUSES, Job
from .time import utc_now_naive


def get_job(job_id: int) -> Job:
    """Fetch one job by id or raise 404."""
    return Job.query.get_or_404(job_id)


def get_jobs_for_vehicle(vehicle_id: int) -> list[Job]:
    """Return all jobs associated with a vehicle id."""
    return (
        Job.query.filter_by(vehicle_id=vehicle_id)
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
