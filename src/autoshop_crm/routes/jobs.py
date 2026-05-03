"""Job/work-order HTTP routes."""

from datetime import datetime

from flask.typing import ResponseReturnValue
from flask import Blueprint, flash, render_template, request, redirect, url_for
from sqlalchemy.orm import joinedload

from ..services.authorization import require_permission
from ..services.jobs import (
    create_job,
    create_job_expense,
    create_job_labor,
    create_job_part,
    get_job,
    update_job_cost,
    update_job_status,
)
from ..services.dates import parse_optional_datetime
from ..models.settings import BusinessSettings
from ..models.user import User

jobs_bp = Blueprint("jobs", __name__)


@jobs_bp.route("/invoice/multi")
@require_permission("manage_jobs")
def invoice_multi() -> ResponseReturnValue:
    """Render a combined invoice for multiple selected jobs."""
    from ..models.job import Job
    ids_raw = request.args.get("ids", "")
    job_ids = [int(x) for x in ids_raw.split(",") if x.strip().isdigit()]
    if not job_ids:
        flash("No jobs selected for invoice.")
        return redirect(url_for("customers.list_customers"))

    jobs = (
        Job.query
        .options(joinedload(Job.parts), joinedload(Job.labor))
        .filter(Job.id.in_(job_ids))
        .order_by(Job.created_at.asc(), Job.id.asc())
        .all()
    )
    if not jobs:
        flash("No matching jobs found.")
        return redirect(url_for("customers.list_customers"))

    settings = BusinessSettings.query.first()
    parts_total = sum(j.parts_total for j in jobs)
    labor_total = sum(j.labor_total for j in jobs)
    subtotal = parts_total + labor_total
    # Use sum of manual costs where set, otherwise subtotal
    total_due = sum(j.cost if j.cost is not None else (j.parts_total + j.labor_total) for j in jobs)
    all_completed = all(j.status == "completed" for j in jobs)

    return render_template(
        "jobs/invoice_multi.html",
        jobs=jobs,
        settings=settings,
        parts_total=parts_total,
        labor_total=labor_total,
        subtotal=subtotal,
        total_due=total_due,
        all_completed=all_completed,
        sales_tax_rate=settings.sales_tax_rate or 0.0 if settings else 0.0,
        card_fee_rate=settings.card_fee_rate or 0.0 if settings else 0.0,
    )


@jobs_bp.route("/<int:job_id>/invoice")
@require_permission("manage_jobs")
def invoice(job_id: int) -> ResponseReturnValue:
    """Render a print-ready invoice for a job."""
    from ..models.job import Job
    job = (
        Job.query
        .options(
            joinedload(Job.parts),
            joinedload(Job.labor),
        )
        .get_or_404(job_id)
    )
    settings = BusinessSettings.query.first()
    parts_total = round(sum((p.part_price or 0.0) for p in job.parts), 2)
    labor_total = round(sum((p.labor_cost or 0.0) for p in job.parts), 2)
    subtotal = round(parts_total + labor_total, 2)
    total_due = job.cost if job.cost is not None else subtotal
    tax_rate = (settings.tax_percentage or 0.0) if settings else 0.0
    tax_amount = round(subtotal * tax_rate / 100, 2)
    total_with_tax = round(subtotal + tax_amount, 2)
    return render_template(
        "jobs/invoice.html",
        job=job,
        settings=settings,
        parts_total=parts_total,
        labor_total=labor_total,
        subtotal=subtotal,
        total_due=total_due,
        tax_amount=tax_amount,
        total_with_tax=total_with_tax,
        sales_tax_rate=tax_rate,
        card_fee_rate=(settings.card_fee_rate or 0.0) if settings else 0.0,
    )


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
    unit_price_raw = request.form.get("unit_price", "").strip()
    supplier = request.form.get("supplier", "").strip()
    notes = request.form.get("notes", "").strip()
    purchased_on_raw = request.form.get("purchased_on", "").strip()
    warranty_years_raw = request.form.get("warranty_years", "").strip()

    if not part_name:
        flash("Part name is required.", "error")
        return redirect(url_for("vehicles.vehicle_detail", vehicle_id=job.vehicle_id))

    try:
        unit_price = float(unit_price_raw) if unit_price_raw else None
    except ValueError:
        flash("Part price must be a valid number.", "error")
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
            unit_price=unit_price,
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


@jobs_bp.route("/<int:job_id>/labor", methods=["POST"])
@require_permission("manage_jobs")
def add_labor(job_id: int) -> ResponseReturnValue:
    """Add a labor entry to a job."""
    job = get_job(job_id)
    user_id_raw = request.form.get("user_id", "").strip()
    hours_raw = request.form.get("hours", "").strip()
    notes = request.form.get("notes", "").strip()

    try:
        hours = float(hours_raw)
        if hours <= 0:
            raise ValueError
    except ValueError:
        flash("Hours must be a positive number.", "error")
        return redirect(url_for("vehicles.vehicle_detail", vehicle_id=job.vehicle_id))

    mechanic = None
    if user_id_raw:
        mechanic = User.query.get(int(user_id_raw))

    rate = (mechanic.labor_rate or 0.0) if mechanic else 0.0

    try:
        create_job_labor(
            job=job,
            user_id=mechanic.id if mechanic else None,
            hours=hours,
            rate_at_time=rate,
            notes=notes or None,
        )
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("vehicles.vehicle_detail", vehicle_id=job.vehicle_id))

    flash("Labor entry added.", "success")
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


@jobs_bp.route("/<int:job_id>/description", methods=["POST"])
@require_permission("manage_jobs")
def update_description(job_id: int) -> ResponseReturnValue:
    """Update the description text of a job."""
    job = get_job(job_id)
    description = request.form.get("description", "").strip()
    if not description:
        flash("Description cannot be blank.", "error")
        return redirect(url_for("vehicles.vehicle_detail", vehicle_id=job.vehicle_id))
    job.description = description
    from ..extensions import db
    db.session.commit()
    flash("Job description updated.", "success")
    return redirect(url_for("vehicles.vehicle_detail", vehicle_id=job.vehicle_id))


@jobs_bp.route("/parts/<int:part_id>/edit", methods=["POST"])
@require_permission("manage_jobs")
def edit_part(part_id: int) -> ResponseReturnValue:
    """Edit an existing part entry."""
    from ..models.job import JobPart
    from ..extensions import db
    from datetime import date as date_type
    part = JobPart.query.get_or_404(part_id)
    job = get_job(part.job_id)
    if request.form.get("job_id", type=int) != job.id:
        flash("Invalid request.", "error")
        return redirect(url_for("customers.list_customers"))

    part_name = request.form.get("part_name", "").strip()
    if not part_name:
        flash("Part name is required.", "error")
        return redirect(url_for("vehicles.vehicle_detail", vehicle_id=job.vehicle_id))

    unit_price_raw = request.form.get("unit_price", "").strip()
    try:
        unit_price = float(unit_price_raw) if unit_price_raw else None
    except ValueError:
        flash("Price must be a valid number.", "error")
        return redirect(url_for("vehicles.vehicle_detail", vehicle_id=job.vehicle_id))

    purchased_on_raw = request.form.get("purchased_on", "").strip()
    purchased_on = part.purchased_on
    if purchased_on_raw:
        try:
            purchased_on = datetime.strptime(purchased_on_raw, "%Y-%m-%d").date()
        except ValueError:
            flash("Purchased date must be a valid date.", "error")
            return redirect(url_for("vehicles.vehicle_detail", vehicle_id=job.vehicle_id))

    warranty_years_raw = request.form.get("warranty_years", "").strip()
    try:
        warranty_years = int(warranty_years_raw) if warranty_years_raw else None
    except ValueError:
        flash("Warranty years must be a whole number.", "error")
        return redirect(url_for("vehicles.vehicle_detail", vehicle_id=job.vehicle_id))

    part.part_name = part_name
    part.unit_price = unit_price
    part.supplier = request.form.get("supplier", "").strip() or None
    part.notes = request.form.get("notes", "").strip() or None
    part.purchased_on = purchased_on
    part.warranty_years = warranty_years
    if warranty_years and warranty_years > 0 and purchased_on:
        from ..services.jobs import _safe_add_years
        part.warranty_expires_on = _safe_add_years(purchased_on, warranty_years)
    else:
        part.warranty_expires_on = None

    db.session.commit()
    flash("Part updated.", "success")
    return redirect(url_for("vehicles.vehicle_detail", vehicle_id=job.vehicle_id))


@jobs_bp.route("/parts/<int:part_id>/delete", methods=["POST"])
@require_permission("manage_jobs")
def delete_part(part_id: int) -> ResponseReturnValue:
    """Delete a part entry from a job."""
    from ..models.job import JobPart
    from ..extensions import db
    part = JobPart.query.get_or_404(part_id)
    job = get_job(part.job_id)
    if request.form.get("job_id", type=int) != job.id:
        flash("Invalid request.", "error")
        return redirect(url_for("customers.list_customers"))
    vehicle_id = job.vehicle_id
    db.session.delete(part)
    db.session.commit()
    flash("Part removed.", "success")
    return redirect(url_for("vehicles.vehicle_detail", vehicle_id=vehicle_id))


@jobs_bp.route("/labor/<int:labor_id>/edit", methods=["POST"])
@require_permission("manage_jobs")
def edit_labor(labor_id: int) -> ResponseReturnValue:
    """Edit an existing labor entry."""
    from ..models.job import JobLabor
    from ..extensions import db
    entry = JobLabor.query.get_or_404(labor_id)
    job = get_job(entry.job_id)
    if request.form.get("job_id", type=int) != job.id:
        flash("Invalid request.", "error")
        return redirect(url_for("customers.list_customers"))

    hours_raw = request.form.get("hours", "").strip()
    try:
        hours = float(hours_raw)
        if hours <= 0:
            raise ValueError
    except ValueError:
        flash("Hours must be a positive number.", "error")
        return redirect(url_for("vehicles.vehicle_detail", vehicle_id=job.vehicle_id))

    rate_raw = request.form.get("rate_at_time", "").strip()
    try:
        rate = float(rate_raw) if rate_raw else entry.rate_at_time
        if rate < 0:
            raise ValueError
    except ValueError:
        flash("Rate must be a valid number.", "error")
        return redirect(url_for("vehicles.vehicle_detail", vehicle_id=job.vehicle_id))

    user_id_raw = request.form.get("user_id", "").strip()
    entry.user_id = int(user_id_raw) if user_id_raw else None
    entry.hours = hours
    entry.rate_at_time = rate
    entry.notes = request.form.get("notes", "").strip() or None
    db.session.commit()
    flash("Labor entry updated.", "success")
    return redirect(url_for("vehicles.vehicle_detail", vehicle_id=job.vehicle_id))


@jobs_bp.route("/labor/<int:labor_id>/delete", methods=["POST"])
@require_permission("manage_jobs")
def delete_labor(labor_id: int) -> ResponseReturnValue:
    """Delete a labor entry from a job."""
    from ..models.job import JobLabor
    from ..extensions import db
    entry = JobLabor.query.get_or_404(labor_id)
    job = get_job(entry.job_id)
    if request.form.get("job_id", type=int) != job.id:
        flash("Invalid request.", "error")
        return redirect(url_for("customers.list_customers"))
    vehicle_id = job.vehicle_id
    db.session.delete(entry)
    db.session.commit()
    flash("Labor entry removed.", "success")
    return redirect(url_for("vehicles.vehicle_detail", vehicle_id=vehicle_id))


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
