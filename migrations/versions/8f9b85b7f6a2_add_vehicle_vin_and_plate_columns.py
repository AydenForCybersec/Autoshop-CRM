"""Add vehicle VIN and plate columns when missing.

Revision ID: 8f9b85b7f6a2
Revises: 265fe6e8833b
Create Date: 2026-02-15 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "8f9b85b7f6a2"
down_revision = "265fe6e8833b"
branch_labels = None
depends_on = None


def upgrade():
    """Apply schema changes."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("vehicles")}

    with op.batch_alter_table("vehicles") as batch_op:
        if "vin" not in columns:
            batch_op.add_column(sa.Column("vin", sa.String(length=17), nullable=True))
        if "plate" not in columns:
            batch_op.add_column(sa.Column("plate", sa.String(length=30), nullable=True))


def downgrade():
    """Revert schema changes."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("vehicles")}

    with op.batch_alter_table("vehicles") as batch_op:
        if "plate" in columns:
            batch_op.drop_column("plate")
        if "vin" in columns:
            batch_op.drop_column("vin")
