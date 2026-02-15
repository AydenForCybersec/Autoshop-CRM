"""Job/work-order ORM model."""

from sqlalchemy.orm import validates

from ..extensions import db
from ..services.time import utc_now_naive

JOB_STATUSES: tuple[str, ...] = ("open", "in_progress", "on_hold", "completed")


class Job(db.Model):
    """Represents maintenance or repair work for a vehicle."""

    # Keep app-facing model name as Job while mapping to the existing legacy
    # table name used by the current database schema.
    __tablename__ = "repair_orders"

    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey("vehicles.id"), nullable=False)

    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), default="open", nullable=False)
    # Legacy schema stores this as `total`; expose it as `cost` in code.
    cost = db.Column("total", db.Float)
    created_at = db.Column(db.DateTime, default=utc_now_naive, nullable=False)

    vehicle = db.relationship("Vehicle", back_populates="jobs")

    @validates("status")
    def _validate_status(self, _key: str, value: str | None) -> str:
        normalized = (value or "").strip().lower()
        if normalized not in JOB_STATUSES:
            raise ValueError("Invalid job status.")
        return normalized

    def __repr__(self) -> str:
        """Return a compact debug representation for logs/shell."""
        return f"<Job {self.id} status={self.status}>"
