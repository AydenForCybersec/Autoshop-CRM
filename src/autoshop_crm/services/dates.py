"""Date/time parsing helpers for form inputs."""

from __future__ import annotations

from datetime import datetime


def parse_optional_datetime(value: str | None) -> datetime | None:
    """Parse form datetime input from ``datetime-local`` or ``date`` fields."""
    if value is None:
        return None

    cleaned = value.strip()
    if not cleaned:
        return None

    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue

    raise ValueError("Invalid date format. Use YYYY-MM-DD or YYYY-MM-DDTHH:MM.")
