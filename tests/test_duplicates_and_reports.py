"""Tests for duplicate handling, backdating, and reporting endpoints."""

from pathlib import Path

from autoshop_crm.models.customer import Customer
from autoshop_crm.models.job import Job
from autoshop_crm.models.settings import BusinessSettings
from autoshop_crm.models.vehicle import Vehicle
from autoshop_crm.extensions import db
from autoshop_crm.services.customers import create_customer
from autoshop_crm.services.jobs import create_job_part
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

    job_id = None
    with app.app_context():
        job = Job.query.first()
        assert job is not None
        job_id = job.id
        assert job.created_at.year == 2020
        assert job.created_at.month == 1
        assert job.created_at.day == 1
        create_job_part(
            job=job,
            part_name="Front Brake Pads",
            supplier="OEM Supply",
            part_price=240.0,
            labor_cost=80.0,
            warranty_years=2,
            notes="Parts warranty validated at pickup.",
        )
        settings = BusinessSettings.query.first()
        assert settings is not None
        settings.shop_phone = "(555) 000-1212"
        settings.shop_email = "service@northside.test"
        settings.shop_address = "123 Service Ln, Detroit, MI"
        settings.tax_percentage = 7.5
        settings.shop_logo = "uploads/logos/test-logo.png"
        logo_path = Path(app.static_folder) / settings.shop_logo
        logo_path.parent.mkdir(parents=True, exist_ok=True)
        logo_path.write_bytes(
            bytes.fromhex(
                "89504E470D0A1A0A0000000D4948445200000001000000010802000000907753DE"
                "0000000C49444154789C63F8CFC0000003010100C9FE92EF0000000049454E44AE426082"
            )
        )
        db.session.commit()

    pdf_response = client.get(f"/vehicles/{vehicle.id}/history.pdf")
    assert pdf_response.status_code == 200
    assert pdf_response.mimetype == "application/pdf"
    pdf_text = pdf_response.data.decode("latin-1", errors="ignore")
    assert "Northside Auto" in pdf_text
    assert "000-1212" in pdf_text
    assert "service@northside.test" in pdf_text
    assert "Warranty Coverage Summary" in pdf_text
    assert "Front Brake Pads" in pdf_text
    assert "OEM Supply" not in pdf_text
    assert b"/Subtype /Image" in pdf_response.data
    assert b"/Im1" in pdf_response.data

    accounting_response = client.get("/accounting/")
    assert accounting_response.status_code == 200
    assert b"Completed Parts Revenue" in accounting_response.data
    assert b"Completed Labor Revenue" in accounting_response.data
    assert b"Parts $240.00" in accounting_response.data
    assert b"Labor $80.00" in accounting_response.data
    assert b"Tax $24.00" in accounting_response.data
    assert b"Total $344.00" in accounting_response.data

    csv_response = client.get("/accounting/jobs.csv")
    assert csv_response.status_code == 200
    assert csv_response.mimetype == "text/csv"
    csv_text = csv_response.data.decode("utf-8")
    assert "parts_total,labor_total,subtotal,tax_amount,total_with_tax" in csv_text
    assert ",240.0,80.0,320.0,24.0,344.0," in csv_text

    assert job_id is not None
    invoice_response = client.get(f"/jobs/{job_id}/invoice")
    assert invoice_response.status_code == 200
    assert b"Invoice" in invoice_response.data
    assert b"Front Brake Pads" in invoice_response.data
    assert b"OEM Supply" not in invoice_response.data
    assert b"$320.00" in invoice_response.data  # part + labor subtotal
    assert b"$24.00" in invoice_response.data  # tax at 7.5%
    assert b"$344.00" in invoice_response.data
