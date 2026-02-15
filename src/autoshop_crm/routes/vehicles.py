"""Vehicle-related HTTP routes."""

from flask.typing import ResponseReturnValue
from flask import Blueprint, Response, current_app, flash, render_template, request, redirect, url_for

from ..services.authorization import require_permission
from ..services.vehicles import (
    find_vehicle_duplicates,
    get_vehicle,
    create_vehicle,
    merge_vehicle_data,
)
from ..services.jobs import get_active_warranty_parts_for_vehicle, get_jobs_for_vehicle
from ..services.dates import parse_optional_datetime
from ..services.reports import build_vehicle_history_pdf
from ..models.settings import BusinessSettings

vehicles_bp = Blueprint("vehicles", __name__)


@vehicles_bp.route("/<int:vehicle_id>")
@require_permission("view_vehicles")
def vehicle_detail(vehicle_id: int) -> ResponseReturnValue:
    """Render vehicle details and associated jobs."""
    vehicle = get_vehicle(vehicle_id)
    jobs = get_jobs_for_vehicle(vehicle_id)
    warranty_parts = get_active_warranty_parts_for_vehicle(vehicle_id=vehicle_id)
    settings = BusinessSettings.query.first()
    tax_percentage = float(settings.tax_percentage if settings and settings.tax_percentage is not None else 0.0)
    return render_template(
        "vehicles/detail.html",
        vehicle=vehicle,
        jobs=jobs,
        warranty_parts=warranty_parts,
        tax_percentage=tax_percentage,
    )


@vehicles_bp.route("/create", methods=["POST"])
@require_permission("manage_vehicles")
def create() -> ResponseReturnValue:
    """Create a vehicle from form data and redirect to its detail page."""
    year_raw = request.form.get("year", "").strip()
    customer_id = request.form.get("customer_id", type=int)
    make = request.form.get("make", "").strip()
    model = request.form.get("model", "").strip()
    vin = request.form.get("vin", "").strip() or None
    license_plate = request.form.get("license_plate", "").strip() or None
    created_at_raw = request.form.get("created_at", "").strip()
    duplicate_action = request.form.get("duplicate_action", "").strip()
    selected_vehicle_id = request.form.get("selected_vehicle_id", type=int)

    if not customer_id:
        flash("Customer is required.")
        return redirect(url_for("customers.list_customers"))

    try:
        created_at = parse_optional_datetime(created_at_raw)
    except ValueError as exc:
        flash(str(exc))
        return redirect(url_for("customers.customer_detail", customer_id=customer_id))

    try:
        year = int(year_raw) if year_raw else None
    except ValueError:
        flash("Year must be a valid number.")
        return redirect(url_for("customers.customer_detail", customer_id=customer_id))

    duplicates = find_vehicle_duplicates(
        customer_id=customer_id,
        make=make,
        model=model,
        year=year,
        vin=vin,
        license_plate=license_plate,
    )
    if duplicates and not duplicate_action:
        return render_template(
            "vehicles/confirm_duplicate.html",
            pending={
                "customer_id": customer_id,
                "make": make,
                "model": model,
                "year": year_raw,
                "vin": vin or "",
                "license_plate": license_plate or "",
                "created_at": created_at_raw,
            },
            duplicates=duplicates,
        )

    if duplicate_action in {"use_existing", "merge_existing"}:
        if not selected_vehicle_id:
            flash("Please select a vehicle to continue.")
            return redirect(url_for("customers.customer_detail", customer_id=customer_id))
        existing_vehicle = get_vehicle(selected_vehicle_id)
        if duplicate_action == "merge_existing":
            merge_vehicle_data(
                existing_vehicle,
                make=make,
                model=model,
                year=year,
                vin=vin,
                license_plate=license_plate,
                created_at=created_at,
            )
            flash("Vehicle data merged into existing record.")
        else:
            flash("Used existing vehicle record.")
        return redirect(url_for("vehicles.vehicle_detail", vehicle_id=existing_vehicle.id))

    vehicle = create_vehicle(
        customer_id=customer_id,
        make=make,
        model=model,
        year=year,
        vin=vin,
        license_plate=license_plate,
        created_at=created_at,
    )
    return redirect(url_for("vehicles.vehicle_detail", vehicle_id=vehicle.id))


@vehicles_bp.route("/<int:vehicle_id>/history.pdf")
@require_permission("view_vehicles")
def vehicle_history_pdf(vehicle_id: int) -> ResponseReturnValue:
    """Download a printable service history PDF for a vehicle."""
    vehicle = get_vehicle(vehicle_id)
    jobs = get_jobs_for_vehicle(vehicle_id)
    settings = BusinessSettings.query.first()
    shop_name = settings.shop_name if settings and settings.shop_name else "Autoshop CRM"
    pdf_bytes = build_vehicle_history_pdf(
        vehicle=vehicle,
        jobs=jobs,
        shop_name=shop_name,
        shop_phone=settings.shop_phone if settings else None,
        shop_email=settings.shop_email if settings else None,
        shop_address=settings.shop_address if settings else None,
        shop_logo_path=settings.shop_logo if settings else None,
        static_folder=current_app.static_folder,
    )
    filename = f"vehicle-{vehicle.id}-service-history.pdf"

    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
