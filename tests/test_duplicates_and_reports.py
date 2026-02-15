"""Tests for duplicate handling, backdating, and reporting endpoints."""

from autoshop_crm.models.customer import Customer
from autoshop_crm.models.job import Job
from autoshop_crm.models.vehicle import Vehicle
from autoshop_crm.services.customers import create_customer
from autoshop_crm.services.vehicles import create_vehicle


def test_customer_duplicate_confirmation_and_use_existing(client, app):
    """Posting a likely duplicate customer should show confirmation options."""
    existing = create_customer("John Doe", "john@example.com", "(555) 111-2222")

    response = client.post(
        "/customers/create",
        data={"name": "John Doe", "email": "john@example.com", "phone": "(555) 111-2222"},
    )
    assert response.status_code == 200
    assert b"Potential duplicate customer found" in response.data

    follow_up = client.post(
        "/customers/create",
        data={
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "(555) 111-2222",
            "duplicate_action": "use_existing",
            "selected_customer_id": str(existing.id),
        },
        follow_redirects=True,
    )
    assert follow_up.status_code == 200
    assert b"Customer Profile" in follow_up.data

    with app.app_context():
        assert Customer.query.count() == 1


def test_vehicle_duplicate_merge_updates_missing_fields(client, app):
    """Vehicle duplicate flow should allow merge into existing record."""
    customer = create_customer("Jane")
    existing_vehicle = create_vehicle(customer.id, "Toyota", "Camry", year=2020, vin="VIN123")

    duplicate_response = client.post(
        "/vehicles/create",
        data={
            "customer_id": str(customer.id),
            "make": "Toyota",
            "model": "Camry",
            "year": "2020",
            "vin": "VIN123",
            "license_plate": "ABC123",
        },
    )
    assert duplicate_response.status_code == 200
    assert b"Potential duplicate vehicle found" in duplicate_response.data

    merged_response = client.post(
        "/vehicles/create",
        data={
            "customer_id": str(customer.id),
            "make": "Toyota",
            "model": "Camry",
            "year": "2020",
            "vin": "VIN123",
            "license_plate": "ABC123",
            "duplicate_action": "merge_existing",
            "selected_vehicle_id": str(existing_vehicle.id),
        },
        follow_redirects=True,
    )
    assert merged_response.status_code == 200

    with app.app_context():
        assert Vehicle.query.count() == 1
        vehicle = Vehicle.query.first()
        assert vehicle is not None
        assert vehicle.license_plate == "ABC123"


def test_backdated_job_and_reporting_exports(client, app):
    """Jobs should accept backdated created_at and export endpoints should work."""
    customer = create_customer("Backdate Tester")
    vehicle = create_vehicle(customer.id, "Honda", "Civic", year=2019)

    create_job_response = client.post(
        "/jobs/create",
        data={
            "vehicle_id": str(vehicle.id),
            "description": "Backdated service",
            "cost": "99.50",
            "created_at": "2020-01-01T10:30",
        },
        follow_redirects=True,
    )
    assert create_job_response.status_code == 200

    with app.app_context():
        job = Job.query.first()
        assert job is not None
        assert job.created_at.year == 2020
        assert job.created_at.month == 1
        assert job.created_at.day == 1

    pdf_response = client.get(f"/vehicles/{vehicle.id}/history.pdf")
    assert pdf_response.status_code == 200
    assert pdf_response.mimetype == "application/pdf"

    accounting_response = client.get("/accounting/")
    assert accounting_response.status_code == 200

    csv_response = client.get("/accounting/jobs.csv")
    assert csv_response.status_code == 200
    assert csv_response.mimetype == "text/csv"
