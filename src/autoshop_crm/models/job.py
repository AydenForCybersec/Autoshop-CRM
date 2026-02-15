"""Job/work-order ORM model."""

from ..extensions import db


class Job(db.Model):
    """Represents maintenance or repair work for a vehicle."""

    __tablename__ = "jobs"

    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey("vehicles.id"), nullable=False)

    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), default="open")
    cost = db.Column(db.Float)

    vehicle = db.relationship("Vehicle", back_populates="jobs")

    def __repr__(self) -> str:
        """Return a compact debug representation for logs/shell."""
        return f"<Job {self.id} status={self.status}>"
