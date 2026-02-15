"""Job/work-order ORM models."""

from datetime import date
from decimal import Decimal, ROUND_CEILING
from sqlalchemy.orm import validates

from ..extensions import db
from ..services.time import utc_now_naive

JOB_STATUSES: tuple[str, ...] = ("open", "in_progress", "on_hold", "completed")


def _ceil_money(value: float) -> float:
    """Round non-negative monetary values up to the nearest cent.

    Tiny binary-float noise (for example 30.020000000000003) should not trigger an
    extra cent when the monetary value is already at a cent boundary.
    """
    normalized = Decimal(str(value)) - Decimal("0.000000001")
    if normalized < Decimal("0"):
        normalized = Decimal("0")
    return float(normalized.quantize(Decimal("0.01"), rounding=ROUND_CEILING))


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

    @validates("status")
    def _validate_status(self, _key: str, value: str | None) -> str:
        normalized = (value or "").strip().lower()
        if normalized not in JOB_STATUSES:
            raise ValueError("Invalid job status.")
        return normalized

    @validates("cost")
    def _validate_cost(self, _key: str, value: float | None) -> float | None:
        if value is None:
            return None
        if value < 0:
            raise ValueError("Cost cannot be negative.")
        return _ceil_money(float(value))

    def __repr__(self) -> str:
        """Return a compact debug representation for logs/shell."""
        return f"<Job {self.id} status={self.status}>"

    @property
    def expenses_total(self) -> float:
        """Return summed expenses attached to this repair."""
        return float(sum((expense.amount or 0.0) for expense in self.expenses))

    @property
    def invoice_subtotal(self) -> float:
        """Return customer-facing subtotal based on per-part price + labor."""
        return float(sum((part.invoice_line_total for part in self.parts)))

    def invoice_tax(self, tax_percentage: float | None) -> float:
        """Return tax amount for invoice subtotal based on configured rate."""
        rate = float(tax_percentage or 0.0)
        if rate < 0:
            rate = 0.0
        return self.invoice_subtotal * (rate / 100.0)

    def invoice_total(self, tax_percentage: float | None) -> float:
        """Return invoice grand total (subtotal + tax)."""
        return self.invoice_subtotal + self.invoice_tax(tax_percentage)


class JobPart(db.Model):
    """Represents a part used in a job, optionally with warranty details."""

    __tablename__ = "job_parts"

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("repair_orders.id"), nullable=False, index=True)
    part_name = db.Column(db.String(180), nullable=False)
    supplier = db.Column(db.String(180))
    part_price = db.Column(db.Float, nullable=False, default=0.0)
    labor_cost = db.Column(db.Float, nullable=False, default=0.0)
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

    @validates("part_price", "labor_cost")
    def _validate_prices(self, _key: str, value: float | None) -> float:
        if value is None:
            return 0.0
        if value < 0:
            raise ValueError("Part price and labor cost cannot be negative.")
        return _ceil_money(float(value))

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

    @property
    def invoice_line_total(self) -> float:
        """Return customer-facing line total (part price + labor)."""
        return float(self.part_price or 0.0) + float(self.labor_cost or 0.0)


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
        return _ceil_money(float(value))

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
