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
    op.create_table(
        "plugin_states",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("plugin_id", sa.String(64), nullable=False, unique=True),
        sa.Column("enabled", sa.Boolean, nullable=False),
        sa.Column("settings", sa.JSON, nullable=False),
        sa.Column("installed_at", sa.DateTime, nullable=False),
        sa.Column("failed", sa.Boolean, nullable=False),
        sa.Column("fail_reason", sa.Text, nullable=True),
    )
    op.create_index("ix_plugin_states_plugin_id", "plugin_states", ["plugin_id"])


def downgrade():
    op.drop_index("ix_plugin_states_plugin_id", "plugin_states")
    op.drop_table("plugin_states")
