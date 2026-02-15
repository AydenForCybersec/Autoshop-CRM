"""Add invoice footer message to business settings.

Revision ID: aa9d4f2b31c7
Revises: b7d4e2f9c1a0
Create Date: 2026-02-15 16:10:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "aa9d4f2b31c7"
down_revision = "b7d4e2f9c1a0"
branch_labels = None
depends_on = None


def upgrade():
    """Add printable invoice footer message field."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "settings" not in tables:
        return

    settings_columns = {col["name"] for col in inspector.get_columns("settings")}
    with op.batch_alter_table("settings") as batch_op:
        if "invoice_footer_message" not in settings_columns:
            batch_op.add_column(sa.Column("invoice_footer_message", sa.Text(), nullable=True))


def downgrade():
    """Remove printable invoice footer message field."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "settings" not in tables:
        return

    settings_columns = {col["name"] for col in inspector.get_columns("settings")}
    with op.batch_alter_table("settings") as batch_op:
        if "invoice_footer_message" in settings_columns:
            batch_op.drop_column("invoice_footer_message")
