"""Add job parts table for warranty tracking.

Revision ID: e7c1a4d9b2f0
Revises: d2b6f7e9a8c1
Create Date: 2026-02-15 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e7c1a4d9b2f0"
down_revision = "d2b6f7e9a8c1"
branch_labels = None
depends_on = None


def upgrade():
    """Apply schema changes for job part storage."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "job_parts" in tables:
        return

    op.create_table(
        "job_parts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("part_name", sa.String(length=180), nullable=False),
        sa.Column("supplier", sa.String(length=180), nullable=True),
        sa.Column("warranty_years", sa.Integer(), nullable=True),
        sa.Column("purchased_on", sa.Date(), nullable=False),
        sa.Column("warranty_expires_on", sa.Date(), nullable=True),
        sa.Column("notes", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["repair_orders.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("job_parts") as batch_op:
        batch_op.create_index("ix_job_parts_job_id", ["job_id"], unique=False)
        batch_op.create_index("ix_job_parts_warranty_expires_on", ["warranty_expires_on"], unique=False)


def downgrade():
    """Rollback schema changes."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "job_parts" not in tables:
        return

    indexes = {index["name"] for index in inspector.get_indexes("job_parts")}
    with op.batch_alter_table("job_parts") as batch_op:
        if "ix_job_parts_warranty_expires_on" in indexes:
            batch_op.drop_index("ix_job_parts_warranty_expires_on")
        if "ix_job_parts_job_id" in indexes:
            batch_op.drop_index("ix_job_parts_job_id")
    op.drop_table("job_parts")
