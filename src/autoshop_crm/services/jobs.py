from ..extensions import db
from ..models.job import Job


def get_job(job_id: int):
    return Job.query.get_or_404(job_id)


def get_jobs_for_vehicle(vehicle_id: int):
    return Job.query.filter_by(vehicle_id=vehicle_id).all()


def create_job(vehicle_id, description, cost=None):
    job = Job(
        vehicle_id=vehicle_id,
        description=description,
        cost=cost,
    )
    db.session.add(job)
    db.session.commit()
    return job


def update_job_status(job: Job, status: str):
    job.status = status
    db.session.commit()
    return job
