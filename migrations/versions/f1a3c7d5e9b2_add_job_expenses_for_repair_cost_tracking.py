"""Add job expenses table for repair expense tracking.

Revision ID: f1a3c7d5e9b2
Revises: e7c1a4d9b2f0
Create Date: 2026-02-15 12:35:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f1a3c7d5e9b2"
down_revision = "e7c1a4d9b2f0"
branch_labels = None
depends_on = None


def upgrade():
    """Apply schema changes for job expense storage."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "job_expenses" in tables:
        return

    op.create_table(
        "job_expenses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(length=180), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("vendor", sa.String(length=180), nullable=True),
        sa.Column("incurred_on", sa.Date(), nullable=False),
        sa.Column("notes", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["repair_orders.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("job_expenses") as batch_op:
        batch_op.create_index("ix_job_expenses_job_id", ["job_id"], unique=False)
        batch_op.create_index("ix_job_expenses_incurred_on", ["incurred_on"], unique=False)


def downgrade():
    """Rollback schema changes."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "job_expenses" not in tables:
        return

    indexes = {index["name"] for index in inspector.get_indexes("job_expenses")}
    with op.batch_alter_table("job_expenses") as batch_op:
        if "ix_job_expenses_incurred_on" in indexes:
            batch_op.drop_index("ix_job_expenses_incurred_on")
        if "ix_job_expenses_job_id" in indexes:
            batch_op.drop_index("ix_job_expenses_job_id")
    op.drop_table("job_expenses")
