"""Make part_price and labor_cost nullable on job_parts.

Revision ID: d3f9a2b1c7e5
Revises: 74772a3e5a8b
Branch Labels: None
Depends On: None
"""

from alembic import op
import sqlalchemy as sa

revision = "d3f9a2b1c7e5"
down_revision = "74772a3e5a8b"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("job_parts") as batch_op:
        batch_op.alter_column("part_price", existing_type=sa.Float(), nullable=True, server_default=None)
        batch_op.alter_column("labor_cost", existing_type=sa.Float(), nullable=True, server_default=None)


def downgrade():
    with op.batch_alter_table("job_parts") as batch_op:
        batch_op.alter_column("part_price", existing_type=sa.Float(), nullable=False, server_default="0")
        batch_op.alter_column("labor_cost", existing_type=sa.Float(), nullable=False, server_default="0")
