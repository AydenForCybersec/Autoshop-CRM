"""Customer ORM model."""

from datetime import datetime
import re

from sqlalchemy.orm import validates

from ..extensions import db


class Customer(db.Model):
    """Represents a customer who owns one or more vehicles."""

    __tablename__ = "customers"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True)
    phone = db.Column(db.String(50))
    address = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    vehicles = db.relationship("Vehicle", back_populates="customer")

    @staticmethod
    def _normalize_phone(value: str | None) -> str | None:
        """Parse phone-like input and return a standard US display format."""
        if value is None:
            return None

        stripped = value.strip()
        if not stripped:
            return None

        digits = re.sub(r"\D", "", stripped)
        if len(digits) == 11 and digits.startswith("1"):
            digits = digits[1:]

        if len(digits) == 10:
            return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"

        return stripped

    @validates("phone")
    def _validate_phone(self, _key: str, value: str | None) -> str | None:
        """Normalize phone values before persisting."""
        return self._normalize_phone(value)

    def __repr__(self) -> str:
        """Return a compact debug representation for logs/shell."""
        return f"<Customer {self.id} {self.name}>"
