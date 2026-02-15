"""Vehicle service functions for data access and persistence."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import and_, func, or_

from ..extensions import db
from ..models.vehicle import Vehicle
from .time import utc_now_naive


def get_vehicle(vehicle_id: int) -> Vehicle:
    """Fetch one vehicle by id or raise 404."""
    return Vehicle.query.get_or_404(vehicle_id)


def get_vehicles_for_customer(customer_id: int) -> list[Vehicle]:
    """Return all vehicles assigned to a given customer id."""
    return Vehicle.query.filter_by(customer_id=customer_id).all()


def find_vehicle_duplicates(
    customer_id: int,
    make: str,
    model: str,
    year: Optional[int] = None,
    vin: Optional[str] = None,
    license_plate: Optional[str] = None,
) -> list[Vehicle]:
    """Return likely duplicate vehicle records."""
    normalized_make = make.strip().lower()
    normalized_model = model.strip().lower()
    normalized_vin = vin.strip().upper() if vin and vin.strip() else None
    normalized_plate = license_plate.strip().upper() if license_plate and license_plate.strip() else None

    clauses = [
        and_(
            Vehicle.customer_id == int(customer_id),
            func.lower(Vehicle.make) == normalized_make,
            func.lower(Vehicle.model) == normalized_model,
            Vehicle.year == year,
        )
    ]
    if normalized_vin:
        clauses.append(func.upper(Vehicle.vin) == normalized_vin)
    if normalized_plate:
        clauses.append(func.upper(Vehicle.license_plate) == normalized_plate)

    return (
        Vehicle.query.filter(or_(*clauses))
        .order_by(Vehicle.id.asc())
        .all()
    )


def create_vehicle(
    customer_id: int,
    make: str,
    model: str,
    year: Optional[int] = None,
    vin: Optional[str] = None,
    license_plate: Optional[str] = None,
    created_at: Optional[datetime] = None,
) -> Vehicle:
    """Create and persist a vehicle record."""
    normalized_vin = vin.strip().upper() if vin and vin.strip() else None
    normalized_plate = license_plate.strip().upper() if license_plate and license_plate.strip() else None

    vehicle = Vehicle(
        customer_id=customer_id,
        make=make.strip(),
        model=model.strip(),
        year=year,
        vin=normalized_vin,
        license_plate=normalized_plate,
        created_at=created_at or utc_now_naive(),
    )
    db.session.add(vehicle)
    db.session.commit()
    return vehicle


def merge_vehicle_data(
    existing_vehicle: Vehicle,
    make: str,
    model: str,
    year: Optional[int] = None,
    vin: Optional[str] = None,
    license_plate: Optional[str] = None,
    created_at: Optional[datetime] = None,
) -> Vehicle:
    """Merge candidate vehicle data into an existing vehicle."""
    normalized_vin = vin.strip().upper() if vin and vin.strip() else None
    normalized_plate = license_plate.strip().upper() if license_plate and license_plate.strip() else None

    if year and existing_vehicle.year is None:
        existing_vehicle.year = year
    if normalized_vin and not existing_vehicle.vin:
        existing_vehicle.vin = normalized_vin
    if normalized_plate and not existing_vehicle.license_plate:
        existing_vehicle.license_plate = normalized_plate
    if make.strip() and not existing_vehicle.make:
        existing_vehicle.make = make.strip()
    if model.strip() and not existing_vehicle.model:
        existing_vehicle.model = model.strip()
    if created_at:
        if existing_vehicle.created_at is None or created_at < existing_vehicle.created_at:
            existing_vehicle.created_at = created_at

    db.session.commit()
    return existing_vehicle
