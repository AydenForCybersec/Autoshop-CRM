"""Add sales tax rate and card fee rate to business settings.

Revision ID: b2d4f8a1c6e3
Revises: a9c3e1f7b4d2
Create Date: 2026-04-28 01:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "b2d4f8a1c6e3"
down_revision = "a9c3e1f7b4d2"
branch_labels = None
depends_on = None


def upgrade():
    existing_cols = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("settings")}
    with op.batch_alter_table("settings") as batch_op:
        if "sales_tax_rate" not in existing_cols:
            batch_op.add_column(sa.Column("sales_tax_rate", sa.Float(), nullable=True))
        if "card_fee_rate" not in existing_cols:
            batch_op.add_column(sa.Column("card_fee_rate", sa.Float(), nullable=True))


def downgrade():
    existing_cols = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("settings")}
    with op.batch_alter_table("settings") as batch_op:
        if "sales_tax_rate" in existing_cols:
            batch_op.drop_column("sales_tax_rate")
        if "card_fee_rate" in existing_cols:
            batch_op.drop_column("card_fee_rate")
