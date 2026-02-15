"""Job/work-order HTTP routes."""

from flask.typing import ResponseReturnValue
from flask import Blueprint, flash, request, redirect, url_for

from ..services.authorization import require_permission
from ..services.jobs import create_job, update_job_status, get_job
from ..services.dates import parse_optional_datetime

jobs_bp = Blueprint("jobs", __name__)


@jobs_bp.route("/create", methods=["POST"])
@require_permission("manage_jobs")
def create() -> ResponseReturnValue:
    """Create a job and redirect back to the parent vehicle page."""
    vehicle_id = request.form.get("vehicle_id", type=int)
    description = request.form.get("description", "").strip()
    cost_raw = request.form.get("cost", "").strip()
    created_at_raw = request.form.get("created_at", "").strip()

    if not vehicle_id:
        flash("Vehicle is required.")
        return redirect(url_for("customers.list_customers"))

    try:
        created_at = parse_optional_datetime(created_at_raw)
    except ValueError as exc:
        flash(str(exc))
        return redirect(url_for("vehicles.vehicle_detail", vehicle_id=vehicle_id))

    try:
        cost = float(cost_raw) if cost_raw else None
    except ValueError:
        flash("Cost must be a valid number.", "error")
        return redirect(url_for("vehicles.vehicle_detail", vehicle_id=vehicle_id))

    job = create_job(
        vehicle_id=vehicle_id,
        description=description,
        cost=cost,
        created_at=created_at,
    )
    return redirect(url_for("vehicles.vehicle_detail", vehicle_id=job.vehicle_id))


@jobs_bp.route("/<int:job_id>/status", methods=["POST"])
@require_permission("manage_jobs")
def update_status(job_id: int) -> ResponseReturnValue:
    """Update a job status and redirect to the parent vehicle page."""
    job = get_job(job_id)
    try:
        update_job_status(job, request.form.get("status", ""))
        flash("Job status updated.", "success")
    except ValueError:
        flash("Invalid job status selected.", "error")
    return redirect(url_for("vehicles.vehicle_detail", vehicle_id=job.vehicle_id))
