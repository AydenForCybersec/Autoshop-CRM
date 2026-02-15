"""Add created_at timestamps and duplicate-prevention indexes.

Revision ID: a1f4b6c8d2e0
Revises: 3e379f97d91d
Create Date: 2026-02-15 02:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a1f4b6c8d2e0"
down_revision = "3e379f97d91d"
branch_labels = None
depends_on = None


def upgrade():
    """Apply schema changes for timestamped records and lookups."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    customer_columns = {column["name"] for column in inspector.get_columns("customers")}
    vehicle_columns = {column["name"] for column in inspector.get_columns("vehicles")}
    repair_columns = {column["name"] for column in inspector.get_columns("repair_orders")}

    if "created_at" not in customer_columns:
        with op.batch_alter_table("customers") as batch_op:
            batch_op.add_column(sa.Column("created_at", sa.DateTime(), nullable=True))
    if "created_at" not in vehicle_columns:
        with op.batch_alter_table("vehicles") as batch_op:
            batch_op.add_column(sa.Column("created_at", sa.DateTime(), nullable=True))

    if "created_at" in customer_columns or "created_at" in {column["name"] for column in inspector.get_columns("customers")}:
        op.execute("UPDATE customers SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
        with op.batch_alter_table("customers") as batch_op:
            batch_op.alter_column("created_at", existing_type=sa.DateTime(), nullable=False)

    if "created_at" in vehicle_columns or "created_at" in {column["name"] for column in inspector.get_columns("vehicles")}:
        op.execute("UPDATE vehicles SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
        with op.batch_alter_table("vehicles") as batch_op:
            batch_op.alter_column("created_at", existing_type=sa.DateTime(), nullable=False)

    if "created_at" in repair_columns:
        op.execute("UPDATE repair_orders SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
        with op.batch_alter_table("repair_orders") as batch_op:
            batch_op.alter_column("created_at", existing_type=sa.DateTime(), nullable=False)

    op.execute("UPDATE vehicles SET vin = UPPER(vin) WHERE vin IS NOT NULL")
    op.execute("UPDATE vehicles SET plate = UPPER(plate) WHERE plate IS NOT NULL")

    vehicle_indexes = {index["name"] for index in inspector.get_indexes("vehicles")}
    with op.batch_alter_table("vehicles") as batch_op:
        if "ix_vehicles_vin" not in vehicle_indexes:
            batch_op.create_index("ix_vehicles_vin", ["vin"], unique=False)
        if "ix_vehicles_plate" not in vehicle_indexes:
            batch_op.create_index("ix_vehicles_plate", ["plate"], unique=False)


def downgrade():
    """Rollback schema changes."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    vehicle_indexes = {index["name"] for index in inspector.get_indexes("vehicles")}
    if "ix_vehicles_plate" in vehicle_indexes or "ix_vehicles_vin" in vehicle_indexes:
        with op.batch_alter_table("vehicles") as batch_op:
            if "ix_vehicles_plate" in vehicle_indexes:
                batch_op.drop_index("ix_vehicles_plate")
            if "ix_vehicles_vin" in vehicle_indexes:
                batch_op.drop_index("ix_vehicles_vin")

    customer_columns = {column["name"] for column in inspector.get_columns("customers")}
    vehicle_columns = {column["name"] for column in inspector.get_columns("vehicles")}
    repair_columns = {column["name"] for column in inspector.get_columns("repair_orders")}

    if "created_at" in repair_columns:
        with op.batch_alter_table("repair_orders") as batch_op:
            batch_op.alter_column("created_at", existing_type=sa.DateTime(), nullable=True)
    if "created_at" in vehicle_columns:
        with op.batch_alter_table("vehicles") as batch_op:
            batch_op.drop_column("created_at")
    if "created_at" in customer_columns:
        with op.batch_alter_table("customers") as batch_op:
            batch_op.drop_column("created_at")
