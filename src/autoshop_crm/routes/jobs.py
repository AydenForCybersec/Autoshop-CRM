"""Job/work-order HTTP routes."""

from datetime import datetime

from flask.typing import ResponseReturnValue
from flask import Blueprint, flash, request, redirect, url_for

from ..services.authorization import require_permission
from ..services.jobs import (
    create_job,
    create_job_expense,
    create_job_part,
    get_job,
    update_job_cost,
    update_job_status,
)
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


@jobs_bp.route("/<int:job_id>/parts", methods=["POST"])
@require_permission("manage_jobs")
def add_part(job_id: int) -> ResponseReturnValue:
    """Add a part to a job, including optional warranty metadata."""
    job = get_job(job_id)
    part_name = request.form.get("part_name", "").strip()
    supplier = request.form.get("supplier", "").strip()
    notes = request.form.get("notes", "").strip()
    purchased_on_raw = request.form.get("purchased_on", "").strip()
    warranty_years_raw = request.form.get("warranty_years", "").strip()

    if not part_name:
        flash("Part name is required.", "error")
        return redirect(url_for("vehicles.vehicle_detail", vehicle_id=job.vehicle_id))

    purchased_on = None
    if purchased_on_raw:
        try:
            purchased_on = datetime.strptime(purchased_on_raw, "%Y-%m-%d").date()
        except ValueError:
            flash("Purchased date must be a valid date.", "error")
            return redirect(url_for("vehicles.vehicle_detail", vehicle_id=job.vehicle_id))

    try:
        warranty_years = int(warranty_years_raw) if warranty_years_raw else None
    except ValueError:
        flash("Warranty years must be a whole number.", "error")
        return redirect(url_for("vehicles.vehicle_detail", vehicle_id=job.vehicle_id))

    if warranty_years is not None and warranty_years < 0:
        flash("Warranty years cannot be negative.", "error")
        return redirect(url_for("vehicles.vehicle_detail", vehicle_id=job.vehicle_id))

    try:
        create_job_part(
            job=job,
            part_name=part_name,
            supplier=supplier or None,
            warranty_years=warranty_years,
            purchased_on=purchased_on,
            notes=notes or None,
        )
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("vehicles.vehicle_detail", vehicle_id=job.vehicle_id))

    flash("Part added to job.", "success")
    return redirect(url_for("vehicles.vehicle_detail", vehicle_id=job.vehicle_id))


@jobs_bp.route("/<int:job_id>/expenses", methods=["POST"])
@require_permission("manage_jobs")
def add_expense(job_id: int) -> ResponseReturnValue:
    """Add an expense line item to a job."""
    job = get_job(job_id)
    description = request.form.get("description", "").strip()
    amount_raw = request.form.get("amount", "").strip()
    vendor = request.form.get("vendor", "").strip()
    notes = request.form.get("notes", "").strip()
    incurred_on_raw = request.form.get("incurred_on", "").strip()

    if not description:
        flash("Expense description is required.", "error")
        return redirect(url_for("vehicles.vehicle_detail", vehicle_id=job.vehicle_id))

    try:
        amount = float(amount_raw)
    except ValueError:
        flash("Expense amount must be a valid number.", "error")
        return redirect(url_for("vehicles.vehicle_detail", vehicle_id=job.vehicle_id))

    if amount < 0:
        flash("Expense amount cannot be negative.", "error")
        return redirect(url_for("vehicles.vehicle_detail", vehicle_id=job.vehicle_id))

    incurred_on = None
    if incurred_on_raw:
        try:
            incurred_on = datetime.strptime(incurred_on_raw, "%Y-%m-%d").date()
        except ValueError:
            flash("Expense date must be a valid date.", "error")
            return redirect(url_for("vehicles.vehicle_detail", vehicle_id=job.vehicle_id))

    try:
        create_job_expense(
            job=job,
            description=description,
            amount=amount,
            vendor=vendor or None,
            incurred_on=incurred_on,
            notes=notes or None,
        )
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("vehicles.vehicle_detail", vehicle_id=job.vehicle_id))

    flash("Expense added to job.", "success")
    return redirect(url_for("vehicles.vehicle_detail", vehicle_id=job.vehicle_id))


@jobs_bp.route("/<int:job_id>/cost", methods=["POST"])
@require_permission("manage_jobs")
def edit_cost(job_id: int) -> ResponseReturnValue:
    """Edit the total cost recorded for a job."""
    job = get_job(job_id)
    cost_raw = request.form.get("cost", "").strip()

    if not cost_raw:
        try:
            update_job_cost(job, None)
        except ValueError as exc:
            flash(str(exc), "error")
            return redirect(url_for("vehicles.vehicle_detail", vehicle_id=job.vehicle_id))
        flash("Job total cost cleared.", "success")
        return redirect(url_for("vehicles.vehicle_detail", vehicle_id=job.vehicle_id))

    try:
        cost = float(cost_raw)
    except ValueError:
        flash("Cost must be a valid number.", "error")
        return redirect(url_for("vehicles.vehicle_detail", vehicle_id=job.vehicle_id))

    try:
        update_job_cost(job, cost)
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("vehicles.vehicle_detail", vehicle_id=job.vehicle_id))

    flash("Job total cost updated.", "success")
    return redirect(url_for("vehicles.vehicle_detail", vehicle_id=job.vehicle_id))
