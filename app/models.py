from .database import db
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from flask_login import UserMixin

class Setting(db.Model):
    __tablename__ = "settings"
    id = db.Column(db.Integer, primary_key=True)
    shop_name = db.Column(db.String(120))
    shop_phone = db.Column(db.String(50))
    shop_email = db.Column(db.String(120))
    shop_address = db.Column(db.Text)
    shop_logo = db.Column(db.String(255))
    setup_complete = db.Column(db.Boolean, default=False)

class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, index=True)
    email = db.Column(db.String(120), unique=True, index=True)
    password_hash = db.Column(db.String(255))
    role = db.Column(db.String(30), default="admin")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @classmethod
    def create_admin(cls, name, email, password):
        u = cls(name=name, email=email, role="admin")
        u.set_password(password)
        db.session.add(u)
        db.session.commit()
        return u


class Customer(db.Model):
    __tablename__ = "customers"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    phone = db.Column(db.String(50))
    email = db.Column(db.String(120))
    address = db.Column(db.Text)
    vehicles = db.relationship("Vehicle", backref="owner", lazy=True)

class Vehicle(db.Model):
    __tablename__ = "vehicles"
    id = db.Column(db.Integer, primary_key=True)
    vin = db.Column(db.String(60))
    plate = db.Column(db.String(30))
    make = db.Column(db.String(80))
    model = db.Column(db.String(80))
    year = db.Column(db.String(6))
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"))

class RepairOrder(db.Model):
    __tablename__ = "repair_orders"
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey("vehicles.id"))
    description = db.Column(db.Text)
    status = db.Column(db.String(50), default="open")
    total = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
