"""Tests for job creation and status updates."""

from autoshop_crm.services.customers import create_customer
from autoshop_crm.services.vehicles import create_vehicle
from autoshop_crm.services.jobs import create_job, update_job_status


def test_create_job(app):
    """Creating a job should default status to ``open``."""
    customer = create_customer("Jane")
    vehicle = create_vehicle(
        customer_id=customer.id,
        make="Toyota",
        model="Camry",
        year=2020,
    )

    job = create_job(
        vehicle_id=vehicle.id,
        description="Oil change",
        cost=49.99,
    )

    assert job.id is not None
    assert job.description == "Oil change"
    assert job.status == "open"


def test_update_job_status(app):
    """Status updates should persist to the job record."""
    customer = create_customer("Mike")
    vehicle = create_vehicle(customer.id, "Honda", "Civic")
    job = create_job(vehicle.id, "Brake pads")

    update_job_status(job, "completed")
    assert job.status == "completed"
