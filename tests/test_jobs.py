"""Tests for job creation and status updates."""

from datetime import date

from autoshop_crm.services.customers import create_customer
from autoshop_crm.services.vehicles import create_vehicle
from autoshop_crm.services.jobs import (
    create_job,
    create_job_expense,
    create_job_part,
    get_active_warranty_parts_for_vehicle,
    update_job_cost,
    update_job_status,
)


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


def test_update_job_status_rejects_invalid_value(app):
    """Unknown statuses should be rejected."""
    customer = create_customer("Status Tester")
    vehicle = create_vehicle(customer.id, "Ford", "Fusion")
    job = create_job(vehicle.id, "Inspection")

    try:
        update_job_status(job, "done")
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError for invalid job status")


def test_create_job_part_computes_warranty_expiry(app):
    """Parts with warranty years should compute expiry from purchase date."""
    customer = create_customer("Parts Customer")
    vehicle = create_vehicle(customer.id, "Nissan", "Altima")
    job = create_job(vehicle.id, "Alternator replacement")

    part = create_job_part(
        job=job,
        part_name="Alternator",
        supplier="AutoZone",
        warranty_years=3,
        purchased_on=date(2026, 2, 15),
    )

    assert part.id is not None
    assert part.warranty_expires_on == date(2029, 2, 15)
    assert part.supplier == "AutoZone"


def test_get_active_warranty_parts_for_vehicle_filters_expired(app):
    """Warranty report should only include parts still in warranty."""
    customer = create_customer("Warranty Customer")
    vehicle = create_vehicle(customer.id, "Chevrolet", "Malibu")
    job = create_job(vehicle.id, "Cooling system service")

    create_job_part(
        job=job,
        part_name="Radiator",
        supplier="AutoZone",
        warranty_years=2,
        purchased_on=date(2025, 1, 10),
    )
    create_job_part(
        job=job,
        part_name="Thermostat",
        supplier="NAPA",
        warranty_years=1,
        purchased_on=date(2022, 1, 10),
    )
    create_job_part(
        job=job,
        part_name="Coolant",
        supplier="AutoZone",
        warranty_years=None,
        purchased_on=date(2025, 1, 10),
    )

    parts = get_active_warranty_parts_for_vehicle(vehicle_id=vehicle.id, as_of=date(2026, 2, 15))

    assert len(parts) == 1
    assert parts[0].part_name == "Radiator"


def test_create_job_expense_and_total(app):
    """Expense lines should be saved and included in job total expenses."""
    customer = create_customer("Expense Customer")
    vehicle = create_vehicle(customer.id, "Hyundai", "Elantra")
    job = create_job(vehicle.id, "Starter replacement")

    create_job_expense(
        job=job,
        description="Starter motor",
        amount=189.99,
        vendor="AutoZone",
        incurred_on=None,
    )
    create_job_expense(
        job=job,
        description="Shipping",
        amount=15.01,
    )

    assert round(job.expenses_total, 2) == 205.00


def test_update_job_cost(app):
    """Editable job total cost should persist."""
    customer = create_customer("Cost Customer")
    vehicle = create_vehicle(customer.id, "Kia", "Forte")
    job = create_job(vehicle.id, "Transmission service", cost=300.0)

    update_job_cost(job, 425.5)
    assert job.cost == 425.5


def test_update_job_cost_rejects_negative(app):
    """Negative total cost should be rejected."""
    customer = create_customer("Negative Cost Customer")
    vehicle = create_vehicle(customer.id, "Mazda", "3")
    job = create_job(vehicle.id, "Alignment")

    try:
        update_job_cost(job, -1)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError for negative total cost")
