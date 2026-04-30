"""Add plugin_states table.

Revision ID: c1d2e3f4a5b6
Revises: b2d4f8a1c6e3
Create Date: 2026-04-29 00:00:00
"""

revision = "c1d2e3f4a5b6"
down_revision = "b2d4f8a1c6e3"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    """Create plugin_states table."""
    op.create_table(
        "plugin_states",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("plugin_id", sa.String(64), nullable=False, unique=True),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("settings", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("installed_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("failed", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("fail_reason", sa.Text, nullable=True),
    )


def downgrade():
    """Drop plugin_states table."""
    op.drop_table("plugin_states")
