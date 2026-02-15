"""Vehicle-related HTTP routes."""

from flask.typing import ResponseReturnValue
from flask import Blueprint, render_template, request, redirect, url_for

from ..services.vehicles import (
    get_vehicle,
    create_vehicle,
)
from ..services.jobs import get_jobs_for_vehicle

vehicles_bp = Blueprint("vehicles", __name__)


@vehicles_bp.route("/<int:vehicle_id>")
def vehicle_detail(vehicle_id: int) -> ResponseReturnValue:
    """Render vehicle details and associated jobs."""
    vehicle = get_vehicle(vehicle_id)
    jobs = get_jobs_for_vehicle(vehicle_id)
    return render_template("vehicles/detail.html", vehicle=vehicle, jobs=jobs)


@vehicles_bp.route("/create", methods=["POST"])
def create() -> ResponseReturnValue:
    """Create a vehicle from form data and redirect to its detail page."""
    vehicle = create_vehicle(
        customer_id=request.form["customer_id"],
        make=request.form["make"],
        model=request.form["model"],
        year=request.form.get("year"),
    )
    return redirect(url_for("vehicles.vehicle_detail", vehicle_id=vehicle.id))
