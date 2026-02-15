from flask import Blueprint, request, redirect, url_for

from ..services.jobs import create_job, update_job_status, get_job

jobs_bp = Blueprint("jobs", __name__)


@jobs_bp.route("/create", methods=["POST"])
def create():
    job = create_job(
        vehicle_id=request.form["vehicle_id"],
        description=request.form["description"],
        cost=request.form.get("cost"),
    )
    return redirect(url_for("vehicles.vehicle_detail", vehicle_id=job.vehicle_id))


@jobs_bp.route("/<int:job_id>/status", methods=["POST"])
def update_status(job_id):
    job = get_job(job_id)
    update_job_status(job, request.form["status"])
    return redirect(url_for("vehicles.vehicle_detail", vehicle_id=job.vehicle_id))
