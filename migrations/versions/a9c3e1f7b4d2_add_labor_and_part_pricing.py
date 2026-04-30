"""Add job labor table, part unit pricing, and user labor rate.

Revision ID: a9c3e1f7b4d2
Revises: f1a3c7d5e9b2
Create Date: 2026-04-28 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "a9c3e1f7b4d2"
down_revision = "f1a3c7d5e9b2"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    # Add unit_price to job_parts
    existing_cols = {c["name"] for c in inspector.get_columns("job_parts")}
    with op.batch_alter_table("job_parts") as batch_op:
        if "unit_price" not in existing_cols:
            batch_op.add_column(sa.Column("unit_price", sa.Float(), nullable=True))

    # Add labor_rate to users
    existing_user_cols = {c["name"] for c in inspector.get_columns("users")}
    with op.batch_alter_table("users") as batch_op:
        if "labor_rate" not in existing_user_cols:
            batch_op.add_column(sa.Column("labor_rate", sa.Float(), nullable=True))

    # Create job_labor table
    if "job_labor" not in tables:
        op.create_table(
            "job_labor",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("job_id", sa.Integer(), sa.ForeignKey("repair_orders.id"), nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("hours", sa.Float(), nullable=False),
            sa.Column("rate_at_time", sa.Float(), nullable=False),
            sa.Column("notes", sa.String(255), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
        with op.batch_alter_table("job_labor") as batch_op:
            batch_op.create_index("ix_job_labor_job_id", ["job_id"], unique=False)
            batch_op.create_index("ix_job_labor_user_id", ["user_id"], unique=False)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "job_labor" in tables:
        indexes = {i["name"] for i in inspector.get_indexes("job_labor")}
        with op.batch_alter_table("job_labor") as batch_op:
            if "ix_job_labor_job_id" in indexes:
                batch_op.drop_index("ix_job_labor_job_id")
            if "ix_job_labor_user_id" in indexes:
                batch_op.drop_index("ix_job_labor_user_id")
        op.drop_table("job_labor")

    existing_cols = {c["name"] for c in inspector.get_columns("job_parts")}
    with op.batch_alter_table("job_parts") as batch_op:
        if "unit_price" in existing_cols:
            batch_op.drop_column("unit_price")

    existing_user_cols = {c["name"] for c in inspector.get_columns("users")}
    with op.batch_alter_table("users") as batch_op:
        if "labor_rate" in existing_user_cols:
            batch_op.drop_column("labor_rate")
