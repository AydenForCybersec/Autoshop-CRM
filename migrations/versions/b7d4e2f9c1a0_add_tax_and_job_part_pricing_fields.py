"""Add tax setting and customer-facing job part pricing fields.

Revision ID: b7d4e2f9c1a0
Revises: f1a3c7d5e9b2
Create Date: 2026-02-15 13:10:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b7d4e2f9c1a0"
down_revision = "f1a3c7d5e9b2"
branch_labels = None
depends_on = None


def upgrade():
    """Apply schema changes for tax and invoice pricing."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "settings" in tables:
        settings_columns = {col["name"] for col in inspector.get_columns("settings")}
        with op.batch_alter_table("settings") as batch_op:
            if "tax_percentage" not in settings_columns:
                batch_op.add_column(sa.Column("tax_percentage", sa.Float(), nullable=False, server_default="0"))

    if "job_parts" in tables:
        part_columns = {col["name"] for col in inspector.get_columns("job_parts")}
        with op.batch_alter_table("job_parts") as batch_op:
            if "part_price" not in part_columns:
                batch_op.add_column(sa.Column("part_price", sa.Float(), nullable=False, server_default="0"))
            if "labor_cost" not in part_columns:
                batch_op.add_column(sa.Column("labor_cost", sa.Float(), nullable=False, server_default="0"))


def downgrade():
    """Rollback tax and invoice pricing fields."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "job_parts" in tables:
        part_columns = {col["name"] for col in inspector.get_columns("job_parts")}
        with op.batch_alter_table("job_parts") as batch_op:
            if "labor_cost" in part_columns:
                batch_op.drop_column("labor_cost")
            if "part_price" in part_columns:
                batch_op.drop_column("part_price")

    if "settings" in tables:
        settings_columns = {col["name"] for col in inspector.get_columns("settings")}
        with op.batch_alter_table("settings") as batch_op:
            if "tax_percentage" in settings_columns:
                batch_op.drop_column("tax_percentage")
