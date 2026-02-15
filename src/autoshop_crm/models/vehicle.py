from ..extensions import db


class Vehicle(db.Model):
    __tablename__ = "vehicles"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=False)

    make = db.Column(db.String(100), nullable=False)
    model = db.Column(db.String(100), nullable=False)
    year = db.Column(db.Integer)

    customer = db.relationship("Customer", back_populates="vehicles")
    jobs = db.relationship("Job", back_populates="vehicle")

    def __repr__(self):
        return f"<Vehicle {self.id} {self.make} {self.model}>"
