"""Vehicle ORM model."""

from ..extensions import db


class Vehicle(db.Model):
    """Represents a customer vehicle tracked by the shop."""

    __tablename__ = "vehicles"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=False)

    make = db.Column(db.String(100), nullable=False)
    model = db.Column(db.String(100), nullable=False)
    year = db.Column(db.Integer)
    vin = db.Column(db.String(17))
    license_plate = db.Column("plate", db.String(30))

    customer = db.relationship("Customer", back_populates="vehicles")
    jobs = db.relationship("Job", back_populates="vehicle")

    def __repr__(self) -> str:
        """Return a compact debug representation for logs/shell."""
        return f"<Vehicle {self.id} {self.make} {self.model}>"
