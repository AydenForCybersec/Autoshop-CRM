from ..extensions import db
from ..models.vehicle import Vehicle


def get_vehicle(vehicle_id: int):
    return Vehicle.query.get_or_404(vehicle_id)


def get_vehicles_for_customer(customer_id: int):
    return Vehicle.query.filter_by(customer_id=customer_id).all()


def create_vehicle(customer_id, make, model, year=None):
    vehicle = Vehicle(
        customer_id=customer_id,
        make=make,
        model=model,
        year=year,
    )
    db.session.add(vehicle)
    db.session.commit()
    return vehicle
