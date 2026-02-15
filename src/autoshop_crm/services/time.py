"""UTC time helpers used across models and services."""

from datetime import UTC, datetime


def utc_now_naive() -> datetime:
    """Return current UTC timestamp without tzinfo for legacy DB columns."""
    return datetime.now(UTC).replace(tzinfo=None)


def utc_now_aware() -> datetime:
    """Return current UTC timestamp with timezone info."""
    return datetime.now(UTC)
