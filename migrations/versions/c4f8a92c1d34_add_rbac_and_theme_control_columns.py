"""Add RBAC and advanced theme preference columns.

Revision ID: c4f8a92c1d34
Revises: 3e379f97d91d
Create Date: 2026-02-15 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c4f8a92c1d34"
down_revision = "3e379f97d91d"
branch_labels = None
depends_on = None


def upgrade():
    """Apply schema changes."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    user_columns = {column["name"] for column in inspector.get_columns("users")}
    with op.batch_alter_table("users") as batch_op:
        if "role" in user_columns:
            # First normalize the column type without forcing constraints/defaults yet.
            # This avoids MySQL strict-mode failures when legacy rows contain values that
            # cannot satisfy the final NOT NULL + DEFAULT update in one step.
            batch_op.alter_column(
                "role",
                existing_type=sa.String(length=30),
                type_=sa.String(length=30),
                nullable=True,
            )
        if "permission_overrides" not in user_columns:
            batch_op.add_column(
                sa.Column("permission_overrides", sa.JSON(), nullable=False, server_default="{}")
            )
        if "is_active" not in user_columns:
            batch_op.add_column(
                sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true())
            )

    user_rows = bind.execute(sa.text("SELECT id, role FROM users")).fetchall()
    for user_row in user_rows:
        role_value = (user_row.role or "").strip()
        normalized_role = role_value[:30] if role_value else "owner"
        bind.execute(
            sa.text("UPDATE users SET role = :role WHERE id = :user_id"),
            {"role": normalized_role, "user_id": user_row.id},
        )
    bind.execute(sa.text("UPDATE users SET permission_overrides = '{}' WHERE permission_overrides IS NULL"))
    bind.execute(sa.text("UPDATE users SET is_active = 1 WHERE is_active IS NULL"))

    with op.batch_alter_table("users") as batch_op:
        if "role" in user_columns:
            batch_op.alter_column(
                "role",
                existing_type=sa.String(length=30),
                nullable=False,
                server_default="owner",
            )

    pref_columns = {column["name"] for column in inspector.get_columns("app_preferences")}
    with op.batch_alter_table("app_preferences") as batch_op:
        if "text_color" not in pref_columns:
            batch_op.add_column(sa.Column("text_color", sa.String(length=7), nullable=False, server_default="#1d2a22"))
        if "muted_color" not in pref_columns:
            batch_op.add_column(sa.Column("muted_color", sa.String(length=7), nullable=False, server_default="#607164"))
        if "line_color" not in pref_columns:
            batch_op.add_column(sa.Column("line_color", sa.String(length=7), nullable=False, server_default="#d7e3da"))
        if "success_color" not in pref_columns:
            batch_op.add_column(sa.Column("success_color", sa.String(length=7), nullable=False, server_default="#1f7a4f"))
        if "warning_color" not in pref_columns:
            batch_op.add_column(sa.Column("warning_color", sa.String(length=7), nullable=False, server_default="#8e5d13"))
        if "danger_color" not in pref_columns:
            batch_op.add_column(sa.Column("danger_color", sa.String(length=7), nullable=False, server_default="#b34444"))
        if "radius_px" not in pref_columns:
            batch_op.add_column(sa.Column("radius_px", sa.Integer(), nullable=False, server_default="16"))


def downgrade():
    """Revert schema changes."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    pref_columns = {column["name"] for column in inspector.get_columns("app_preferences")}
    with op.batch_alter_table("app_preferences") as batch_op:
        if "radius_px" in pref_columns:
            batch_op.drop_column("radius_px")
        if "danger_color" in pref_columns:
            batch_op.drop_column("danger_color")
        if "warning_color" in pref_columns:
            batch_op.drop_column("warning_color")
        if "success_color" in pref_columns:
            batch_op.drop_column("success_color")
        if "line_color" in pref_columns:
            batch_op.drop_column("line_color")
        if "muted_color" in pref_columns:
            batch_op.drop_column("muted_color")
        if "text_color" in pref_columns:
            batch_op.drop_column("text_color")

    user_columns = {column["name"] for column in inspector.get_columns("users")}
    with op.batch_alter_table("users") as batch_op:
        if "is_active" in user_columns:
            batch_op.drop_column("is_active")
        if "permission_overrides" in user_columns:
            batch_op.drop_column("permission_overrides")
        if "role" in user_columns:
            batch_op.alter_column(
                "role",
                existing_type=sa.String(length=30),
                nullable=True,
                server_default=None,
            )
