"""drift check

Revision ID: 3e379f97d91d
Revises: 8f9b85b7f6a2
Create Date: 2026-02-15 01:23:06.228186

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3e379f97d91d'
down_revision = '8f9b85b7f6a2'
branch_labels = None
depends_on = None


def upgrade():
    """Align legacy schema to current SQLAlchemy models."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "app_preferences" not in inspector.get_table_names():
        op.create_table(
            "app_preferences",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("primary_color", sa.String(length=7), nullable=False),
            sa.Column("accent_color", sa.String(length=7), nullable=False),
            sa.Column("background_color", sa.String(length=7), nullable=False),
            sa.Column("surface_color", sa.String(length=7), nullable=False),
            sa.Column("dashboard_jobs_limit", sa.Integer(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    op.execute("UPDATE customers SET name = 'Unknown Customer' WHERE name IS NULL OR TRIM(name) = ''")
    op.execute("UPDATE customers SET email = NULL WHERE email IS NOT NULL AND TRIM(email) = ''")
    rows = bind.execute(
        sa.text("SELECT id, email FROM customers WHERE email IS NOT NULL ORDER BY id")
    ).fetchall()
    seen_emails: set[str] = set()
    duplicate_ids: list[int] = []
    for row in rows:
        lowered = row.email.lower()
        if lowered in seen_emails:
            duplicate_ids.append(row.id)
            continue
        seen_emails.add(lowered)

    if duplicate_ids:
        bind.execute(
            sa.text("UPDATE customers SET email = NULL WHERE id = :id"),
            [{"id": customer_id} for customer_id in duplicate_ids],
        )

    op.execute("DELETE FROM repair_orders WHERE vehicle_id IS NULL")
    op.execute("UPDATE repair_orders SET description = '' WHERE description IS NULL")

    op.execute("UPDATE settings SET shop_name = 'Autoshop CRM' WHERE shop_name IS NULL OR TRIM(shop_name) = ''")
    op.execute("UPDATE settings SET setup_complete = 0 WHERE setup_complete IS NULL")

    users_missing_names = bind.execute(
        sa.text("SELECT id FROM users WHERE name IS NULL OR TRIM(name) = '' ORDER BY id")
    ).fetchall()
    if users_missing_names:
        bind.execute(
            sa.text("UPDATE users SET name = :name WHERE id = :id"),
            [{"id": row.id, "name": f"user_{row.id}"} for row in users_missing_names],
        )
    op.execute("UPDATE users SET password_hash = '' WHERE password_hash IS NULL")

    op.execute("DELETE FROM vehicles WHERE customer_id IS NULL")
    op.execute("UPDATE vehicles SET make = '' WHERE make IS NULL")
    op.execute("UPDATE vehicles SET model = '' WHERE model IS NULL")
    vehicle_year_rows = bind.execute(
        sa.text("SELECT id, year FROM vehicles WHERE year IS NOT NULL ORDER BY id")
    ).fetchall()
    invalid_year_ids: list[int] = []
    for row in vehicle_year_rows:
        year_value = row.year
        if isinstance(year_value, int):
            continue
        if year_value is None:
            continue
        year_text = str(year_value).strip()
        if not year_text:
            invalid_year_ids.append(row.id)
            continue
        try:
            int(year_text)
        except (TypeError, ValueError):
            invalid_year_ids.append(row.id)

    if invalid_year_ids:
        bind.execute(
            sa.text("UPDATE vehicles SET year = NULL WHERE id = :id"),
            [{"id": vehicle_id} for vehicle_id in invalid_year_ids],
        )

    with op.batch_alter_table('customers', schema=None) as batch_op:
        batch_op.alter_column('name',
               existing_type=sa.VARCHAR(length=120),
               nullable=False)
        batch_op.create_unique_constraint('uq_customers_email', ['email'])

    with op.batch_alter_table('repair_orders', schema=None) as batch_op:
        batch_op.alter_column('vehicle_id',
               existing_type=sa.INTEGER(),
               nullable=False)
        batch_op.alter_column('description',
               existing_type=sa.TEXT(),
               nullable=False)

    with op.batch_alter_table('settings', schema=None) as batch_op:
        batch_op.alter_column('shop_name',
               existing_type=sa.VARCHAR(length=120),
               nullable=False)
        batch_op.alter_column('setup_complete',
               existing_type=sa.BOOLEAN(),
               nullable=False)

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('name',
               existing_type=sa.VARCHAR(length=120),
               nullable=False)
        batch_op.alter_column('password_hash',
               existing_type=sa.VARCHAR(length=255),
               nullable=False)

    with op.batch_alter_table('vehicles', schema=None) as batch_op:
        batch_op.alter_column('customer_id',
               existing_type=sa.INTEGER(),
               nullable=False)
        batch_op.alter_column('make',
               existing_type=sa.VARCHAR(length=80),
               type_=sa.String(length=100),
               nullable=False)
        batch_op.alter_column('model',
               existing_type=sa.VARCHAR(length=80),
               type_=sa.String(length=100),
               nullable=False)
        batch_op.alter_column('year',
               existing_type=sa.VARCHAR(length=6),
               type_=sa.Integer(),
               existing_nullable=True)
        batch_op.alter_column('vin',
               existing_type=sa.VARCHAR(length=60),
               type_=sa.String(length=17),
               existing_nullable=True)


def downgrade():
    """Revert schema alignment changes."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    with op.batch_alter_table('vehicles', schema=None) as batch_op:
        batch_op.alter_column('vin',
               existing_type=sa.String(length=17),
               type_=sa.VARCHAR(length=60),
               existing_nullable=True)
        batch_op.alter_column('year',
               existing_type=sa.Integer(),
               type_=sa.VARCHAR(length=6),
               existing_nullable=True)
        batch_op.alter_column('model',
               existing_type=sa.String(length=100),
               type_=sa.VARCHAR(length=80),
               nullable=True)
        batch_op.alter_column('make',
               existing_type=sa.String(length=100),
               type_=sa.VARCHAR(length=80),
               nullable=True)
        batch_op.alter_column('customer_id',
               existing_type=sa.INTEGER(),
               nullable=True)

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('password_hash',
               existing_type=sa.VARCHAR(length=255),
               nullable=True)
        batch_op.alter_column('name',
               existing_type=sa.VARCHAR(length=120),
               nullable=True)

    with op.batch_alter_table('settings', schema=None) as batch_op:
        batch_op.alter_column('setup_complete',
               existing_type=sa.BOOLEAN(),
               nullable=True)
        batch_op.alter_column('shop_name',
               existing_type=sa.VARCHAR(length=120),
               nullable=True)

    with op.batch_alter_table('repair_orders', schema=None) as batch_op:
        batch_op.alter_column('description',
               existing_type=sa.TEXT(),
               nullable=True)
        batch_op.alter_column('vehicle_id',
               existing_type=sa.INTEGER(),
               nullable=True)

    with op.batch_alter_table('customers', schema=None) as batch_op:
        batch_op.drop_constraint('uq_customers_email', type_='unique')
        batch_op.alter_column('name',
               existing_type=sa.VARCHAR(length=120),
               nullable=True)

    if "app_preferences" in inspector.get_table_names():
        op.drop_table("app_preferences")
