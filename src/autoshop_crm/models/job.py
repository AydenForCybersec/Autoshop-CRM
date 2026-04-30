"""Job/work-order ORM models."""

from datetime import date
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
    parts = db.relationship(
        "JobPart",
        back_populates="job",
        cascade="all, delete-orphan",
    )
    expenses = db.relationship(
        "JobExpense",
        back_populates="job",
        cascade="all, delete-orphan",
        order_by="desc(JobExpense.incurred_on), desc(JobExpense.id)",
    )
    labor = db.relationship(
        "JobLabor",
        back_populates="job",
        cascade="all, delete-orphan",
        order_by="desc(JobLabor.created_at), desc(JobLabor.id)",
    )

    @validates("status")
    def _validate_status(self, _key: str, value: str | None) -> str:
        normalized = (value or "").strip().lower()
        if normalized not in JOB_STATUSES:
            raise ValueError("Invalid job status.")
        return normalized

    def __repr__(self) -> str:
        """Return a compact debug representation for logs/shell."""
        return f"<Job {self.id} status={self.status}>"

    @property
    def expenses_total(self) -> float:
        """Return summed legacy expenses attached to this repair."""
        return float(sum((expense.amount or 0.0) for expense in self.expenses))

    @property
    def parts_total(self) -> float:
        """Return summed part costs (unit_price × 1) for this repair."""
        return float(sum((part.unit_price or 0.0) for part in self.parts))

    @property
    def labor_total(self) -> float:
        """Return summed labor cost (hours × rate) for this repair."""
        return float(sum((entry.hours * entry.rate_at_time) for entry in self.labor))

    @property
    def invoice_subtotal(self) -> float:
        """Return invoice subtotal: sum of per-part part_price + labor_cost."""
        return float(
            sum((p.part_price or 0.0) + (p.labor_cost or 0.0) for p in self.parts)
        )

    def invoice_tax(self, tax_rate: float) -> float:
        """Return tax amount for the given rate (percentage)."""
        return round(self.invoice_subtotal * tax_rate / 100, 2)

    def invoice_total(self, tax_rate: float) -> float:
        """Return invoice total including tax."""
        return round(self.invoice_subtotal + self.invoice_tax(tax_rate), 2)


class JobPart(db.Model):
    """Represents a part used in a job, optionally with warranty details."""

    __tablename__ = "job_parts"

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("repair_orders.id"), nullable=False, index=True)
    part_name = db.Column(db.String(180), nullable=False)
    unit_price = db.Column(db.Float, nullable=True)
    part_price = db.Column(db.Float, nullable=True)
    labor_cost = db.Column(db.Float, nullable=True)
    supplier = db.Column(db.String(180))
    warranty_years = db.Column(db.Integer)
    purchased_on = db.Column(db.Date, nullable=False)
    warranty_expires_on = db.Column(db.Date)
    notes = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=utc_now_naive, nullable=False)

    job = db.relationship("Job", back_populates="parts")

    @validates("part_name")
    def _validate_part_name(self, _key: str, value: str | None) -> str:
        normalized = (value or "").strip()
        if not normalized:
            raise ValueError("Part name is required.")
        return normalized

    @validates("warranty_years")
    def _validate_warranty_years(self, _key: str, value: int | None) -> int | None:
        if value is None:
            return None
        if value < 0:
            raise ValueError("Warranty years cannot be negative.")
        return value

    @validates("purchased_on", "warranty_expires_on")
    def _validate_dates(self, _key: str, value: date | None) -> date | None:
        if value is None:
            return None
        if not isinstance(value, date):
            raise ValueError("Part date fields must be valid dates.")
        return value

    def __repr__(self) -> str:
        """Return a compact debug representation for logs/shell."""
        return f"<JobPart {self.id} job={self.job_id} part={self.part_name!r}>"


class JobExpense(db.Model):
    """Represents an expense line item tied to a job."""

    __tablename__ = "job_expenses"

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("repair_orders.id"), nullable=False, index=True)
    description = db.Column(db.String(180), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    vendor = db.Column(db.String(180))
    incurred_on = db.Column(db.Date, nullable=False)
    notes = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=utc_now_naive, nullable=False)

    job = db.relationship("Job", back_populates="expenses")

    @validates("description")
    def _validate_description(self, _key: str, value: str | None) -> str:
        normalized = (value or "").strip()
        if not normalized:
            raise ValueError("Expense description is required.")
        return normalized

    @validates("amount")
    def _validate_amount(self, _key: str, value: float | None) -> float:
        if value is None:
            raise ValueError("Expense amount is required.")
        if value < 0:
            raise ValueError("Expense amount cannot be negative.")
        return float(value)

    @validates("incurred_on")
    def _validate_incurred_on(self, _key: str, value: date | None) -> date:
        if value is None:
            raise ValueError("Expense date is required.")
        if not isinstance(value, date):
            raise ValueError("Expense date must be valid.")
        return value

    def __repr__(self) -> str:
        """Return a compact debug representation for logs/shell."""
        return f"<JobExpense {self.id} job={self.job_id} amount={self.amount}>"


class JobLabor(db.Model):
    """Represents a labor entry for a job, linked to a mechanic."""

    __tablename__ = "job_labor"

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("repair_orders.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    hours = db.Column(db.Float, nullable=False)
    rate_at_time = db.Column(db.Float, nullable=False)
    notes = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now_naive, nullable=False)

    job = db.relationship("Job", back_populates="labor")
    mechanic = db.relationship("User")

    @property
    def line_total(self) -> float:
        """Return hours × rate."""
        return float(self.hours * self.rate_at_time)

    @validates("hours")
    def _validate_hours(self, _key: str, value: float | None) -> float:
        if value is None or value <= 0:
            raise ValueError("Hours must be greater than zero.")
        return float(value)

    @validates("rate_at_time")
    def _validate_rate(self, _key: str, value: float | None) -> float:
        if value is None or value < 0:
            raise ValueError("Labor rate cannot be negative.")
        return float(value)

    def __repr__(self) -> str:
        return f"<JobLabor {self.id} job={self.job_id} hours={self.hours} rate={self.rate_at_time}>"
