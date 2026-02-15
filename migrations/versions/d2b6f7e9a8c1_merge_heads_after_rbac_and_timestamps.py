"""Merge migration heads after RBAC and timestamp/index updates.

Revision ID: d2b6f7e9a8c1
Revises: c4f8a92c1d34, a1f4b6c8d2e0
Create Date: 2026-02-15 02:10:00.000000
"""


# revision identifiers, used by Alembic.
revision = "d2b6f7e9a8c1"
down_revision = ("c4f8a92c1d34", "a1f4b6c8d2e0")
branch_labels = None
depends_on = None


def upgrade():
    """Merge branch heads; no schema changes."""
    pass


def downgrade():
    """Unmerge branch heads; no schema changes."""
    pass
