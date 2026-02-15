"""Convenience exports for ORM models."""

from .customer import Customer
from .vehicle import Vehicle
from .job import Job
from .user import User

__all__ = [
    "Customer",
    "Vehicle",
    "Job",
    "User",
]
