from ..extensions import db


class Customer(db.Model):
    __tablename__ = "customers"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True)
    phone = db.Column(db.String(50))

    vehicles = db.relationship("Vehicle", back_populates="customer")

    def __repr__(self):
        return f"<Customer {self.id} {self.name}>"
