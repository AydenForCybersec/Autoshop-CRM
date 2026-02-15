"""Vehicle service functions for data access and persistence."""

from __future__ import annotations

from typing import Optional

from ..extensions import db
from ..models.vehicle import Vehicle


def get_vehicle(vehicle_id: int) -> Vehicle:
    """Fetch one vehicle by id or raise 404."""
    return Vehicle.query.get_or_404(vehicle_id)


def get_vehicles_for_customer(customer_id: int) -> list[Vehicle]:
    """Return all vehicles assigned to a given customer id."""
    return Vehicle.query.filter_by(customer_id=customer_id).all()


def create_vehicle(
    customer_id: int,
    make: str,
    model: str,
    year: Optional[int] = None,
    vin: Optional[str] = None,
    license_plate: Optional[str] = None,
) -> Vehicle:
    """Create and persist a vehicle record."""
    normalized_vin = vin.strip().upper() if vin and vin.strip() else None
    normalized_plate = license_plate.strip() if license_plate and license_plate.strip() else None

    vehicle = Vehicle(
        customer_id=customer_id,
        make=make,
        model=model,
        year=year,
        vin=normalized_vin,
        license_plate=normalized_plate,
    )
    db.session.add(vehicle)
    db.session.commit()
    return vehicle
