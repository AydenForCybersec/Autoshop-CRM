"""Job/work-order ORM model."""

from datetime import datetime

from ..extensions import db


class Job(db.Model):
    """Represents maintenance or repair work for a vehicle."""

    # Keep app-facing model name as Job while mapping to the existing legacy
    # table name used by the current database schema.
    __tablename__ = "repair_orders"

    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey("vehicles.id"), nullable=False)

    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), default="open")
    # Legacy schema stores this as `total`; expose it as `cost` in code.
    cost = db.Column("total", db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    vehicle = db.relationship("Vehicle", back_populates="jobs")

    def __repr__(self) -> str:
        """Return a compact debug representation for logs/shell."""
        return f"<Job {self.id} status={self.status}>"
