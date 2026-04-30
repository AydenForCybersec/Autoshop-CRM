"""Custom Flask CLI commands for setup and demo data seeding."""

from __future__ import annotations

from datetime import datetime, timedelta
import click
from flask import Flask
from flask.cli import with_appcontext

from .extensions import db
from .models.customer import Customer
from .models.job import Job, JobLabor, JobPart
from .models.settings import BusinessSettings
from .models.user import User
from .models.vehicle import Vehicle


@click.command("create-db")
@with_appcontext
def create_db() -> None:
    """Create all database tables using SQLAlchemy metadata."""
    db.create_all()
    click.echo("Database created.")


@click.command("clear-db")
@with_appcontext
def clear_db() -> None:
    """Drop all tables and recreate them. Deletes all data."""
    click.echo("Dropping all tables...")
    db.drop_all()
    db.create_all()
    click.echo("Done. Database is empty and ready.")


@click.command("reset-password")
@click.argument("username")
@with_appcontext
def reset_password(username: str) -> None:
    """Reset a user's password interactively."""
    user = User.query.filter_by(username=username).first()
    if not user:
        click.echo(f"No user found with username '{username}'.")
        return
    password = click.prompt("New password", hide_input=True, confirmation_prompt=True)
    if len(password) < 8:
        click.echo("Password must be at least 8 characters.")
        return
    user.set_password(password)
    db.session.commit()
    click.echo(f"Password updated for '{username}'.")


@click.command("seed-demo-data")
@with_appcontext
def seed_demo_data() -> None:
    """Clear the database and populate it with realistic demo shop data."""
    click.echo("Clearing existing data...")
    db.drop_all()
    db.create_all()

    # ── Business settings ──────────────────────────────────────────────────
    settings = BusinessSettings(
        shop_name="Autoworks By Davy LLC",
        shop_phone="(573) 550-6212",
        shop_email="service@autoworksbydavy.com",
        shop_address="444 County Route P\nCamdenton, MO 65020",
        sales_tax_rate=6.225,
        card_fee_rate=3.0,
        setup_complete=True,
    )
    db.session.add(settings)

    # ── Users ──────────────────────────────────────────────────────────────
    davy = User(username="davy", role="owner", is_active=True)
    davy.set_password("demo1234")

    mike = User(username="mike", role="staff", is_active=True, labor_rate=85.00)
    mike.set_password("demo1234")

    jake = User(username="jake", role="staff", is_active=True, labor_rate=75.00)
    jake.set_password("demo1234")

    db.session.add_all([davy, mike, jake])
    db.session.flush()

    # ── Helper ─────────────────────────────────────────────────────────────
    def days_ago(n: int) -> datetime:
        return datetime.now() - timedelta(days=n)

    def add_part(job: Job, name: str, price: float, supplier: str = "AutoZone",
                 warranty_years: int | None = None) -> None:
        from datetime import date
        wp = None
        today = date.today()
        if warranty_years:
            try:
                wp = today.replace(year=today.year + warranty_years)
            except ValueError:
                wp = today.replace(month=2, day=28, year=today.year + warranty_years)
        db.session.add(JobPart(
            job_id=job.id,
            part_name=name,
            unit_price=price,
            supplier=supplier,
            purchased_on=today,
            warranty_expires_on=wp,
            warranty_years=warranty_years,
        ))

    def add_labor(job: Job, mechanic: User, hours: float, notes: str = "") -> None:
        db.session.add(JobLabor(
            job_id=job.id,
            user_id=mechanic.id,
            hours=hours,
            rate_at_time=mechanic.labor_rate or 0.0,
            notes=notes or None,
            created_at=job.created_at,
        ))

    def add_job(vehicle: Vehicle, description: str, status: str,
                created_days_ago: int = 0, cost: float | None = None) -> Job:
        job = Job(
            vehicle_id=vehicle.id,
            description=description,
            status=status,
            cost=cost,
            created_at=days_ago(created_days_ago),
        )
        db.session.add(job)
        db.session.flush()
        return job

    # ── Customers & vehicles & jobs ────────────────────────────────────────

    # 1. Denise Hoelscher — regular customer, older truck
    denise = Customer(name="Denise Hoelscher", phone="(816) 318-1920",
                      address="45 Owl Lane\nCamdenton, MO 65020")
    db.session.add(denise)
    db.session.flush()

    maverick = Vehicle(customer_id=denise.id, make="Ford", model="Maverick",
                       year=2023, vin="1FTVS2BN4PWA00001", license_plate="MO-AB1234")
    db.session.add(maverick)
    db.session.flush()

    j = add_job(maverick, "Oil change and filter replacement", "completed", 14, cost=89.71)
    add_part(j, "Oil Filter", 9.99, "AutoZone")
    add_part(j, "Synthetic Motor Oil (5qt)", 34.95, "AutoZone")
    add_labor(j, mike, 0.5, "Oil change and filter swap")

    j = add_job(maverick, "Front brake pad and rotor replacement", "completed", 7, cost=387.50)
    add_part(j, "Front Brake Pads (set)", 64.99, "NAPA", warranty_years=2)
    add_part(j, "Front Rotors (pair)", 129.98, "NAPA", warranty_years=2)
    add_part(j, "Brake Cleaner", 5.99, "AutoZone")
    add_labor(j, mike, 2.5, "Pull wheels, replace pads and rotors both sides")

    j = add_job(maverick, "Check engine light — P0420 catalyst efficiency", "completed", 3, cost=245.00)
    add_part(j, "O2 Sensor (downstream)", 54.99, "AutoZone", warranty_years=1)
    add_labor(j, jake, 1.5, "Diagnose code, replace downstream O2 sensor, clear codes, road test")

    j = add_job(maverick, "AC not blowing cold — recharge and leak check", "open", 1)
    db.session.flush()

    # 2. Bobby Ray Tucker — old pickup, regular visitor
    bobby = Customer(name="Bobby Ray Tucker", phone="(573) 492-0087",
                     address="12 Ridgeline Rd\nOsage Beach, MO 65065")
    db.session.add(bobby)
    db.session.flush()

    f150 = Vehicle(customer_id=bobby.id, make="Ford", model="F-150",
                   year=2009, vin="1FTPX14V09FA00002", license_plate="MO-RT5599")
    db.session.add(f150)
    db.session.flush()

    j = add_job(f150, "Transmission service — fluid and filter", "completed", 30, cost=310.00)
    add_part(j, "Transmission Filter Kit", 28.99, "AutoZone")
    add_part(j, "Mercon V ATF (12qt)", 71.88, "NAPA")
    add_labor(j, jake, 2.0, "Drop pan, replace filter and gasket, refill fluid")

    j = add_job(f150, "Serpentine belt replacement", "completed", 18, cost=178.00)
    add_part(j, "Serpentine Belt", 38.99, "AutoZone", warranty_years=1)
    add_labor(j, mike, 1.0, "Route new belt, tension and verify")

    j = add_job(f150, "Fuel pump replacement", "in_progress", 2)
    add_part(j, "Fuel Pump Assembly", 189.99, "NAPA", warranty_years=2)
    add_labor(j, jake, 1.0, "Drop tank, partial — waiting on return line fitting")

    ranger = Vehicle(customer_id=bobby.id, make="Ford", model="Ranger",
                     year=1998, license_plate="MO-RT1102")
    db.session.add(ranger)
    db.session.flush()

    j = add_job(ranger, "Won't start — starter replacement", "completed", 45, cost=265.00)
    add_part(j, "Starter Motor", 129.99, "AutoZone", warranty_years=1)
    add_labor(j, mike, 1.5, "Remove old starter, bench test new one, install and verify")

    # 3. Linda Sue Carpenter — newer SUV, warranty work
    linda = Customer(name="Linda Sue Carpenter", phone="(573) 374-8821",
                     address="88 Lakewood Drive\nLake Ozark, MO 65049",
                     email="linda.carpenter@gmail.com")
    db.session.add(linda)
    db.session.flush()

    equinox = Vehicle(customer_id=linda.id, make="Chevrolet", model="Equinox",
                      year=2021, vin="2GNALCEK5M6000003", license_plate="MO-LC7744")
    db.session.add(equinox)
    db.session.flush()

    j = add_job(equinox, "Tire rotation and multi-point inspection", "completed", 10, cost=55.00)
    add_labor(j, mike, 0.5, "Rotate all four, check brakes and fluids, top off washer fluid")

    j = add_job(equinox, "Cabin air filter replacement", "completed", 10, cost=64.50)
    add_part(j, "Cabin Air Filter", 19.99, "AutoZone")
    add_labor(j, jake, 0.5, "Remove glove box, swap filter, reinstall")

    j = add_job(equinox, "Power steering noise — inspect and fluid flush", "on_hold", 3)
    add_labor(j, mike, 0.5, "Inspected — confirmed whine under load. Waiting on customer approval for pump replacement.")

    # 4. Gary and Pam Whitfield — couple with two vehicles
    gary = Customer(name="Gary Whitfield", phone="(573) 302-1144",
                    address="3 Mill Creek Ln\nCamdenton, MO 65020")
    db.session.add(gary)
    db.session.flush()

    silverado = Vehicle(customer_id=gary.id, make="Chevrolet", model="Silverado 1500",
                        year=2016, vin="3GCUKREC5GG000004", license_plate="MO-GW2281")
    db.session.add(silverado)
    db.session.flush()

    j = add_job(silverado, "Full tune-up — plugs, wires, air filter", "completed", 22, cost=425.00)
    add_part(j, "Spark Plugs (set of 8)", 79.99, "AutoZone", warranty_years=1)
    add_part(j, "Spark Plug Wires", 54.99, "AutoZone", warranty_years=1)
    add_part(j, "Air Filter", 24.99, "AutoZone")
    add_labor(j, jake, 2.5, "Full tune-up, reset monitors, road test")

    j = add_job(silverado, "Oil change — full synthetic", "completed", 5, cost=94.00)
    add_part(j, "Oil Filter", 11.99, "AutoZone")
    add_part(j, "Dexos 5W-30 Full Synthetic (6qt)", 47.94, "AutoZone")
    add_labor(j, mike, 0.5)

    pam_camry = Vehicle(customer_id=gary.id, make="Toyota", model="Camry",
                        year=2019, license_plate="MO-PW0932")
    db.session.add(pam_camry)
    db.session.flush()

    j = add_job(pam_camry, "Check engine — P0171 system lean bank 1", "completed", 12, cost=195.00)
    add_part(j, "MAF Sensor Cleaner", 7.99, "AutoZone")
    add_part(j, "Vacuum Line (3ft)", 4.99, "AutoZone")
    add_labor(j, jake, 1.5, "Cleaned MAF, replaced cracked vacuum line on intake, cleared code, verified fix")

    j = add_job(pam_camry, "Rear strut replacement", "open", 0)

    # 5. Dale Simmons — diesel truck
    dale = Customer(name="Dale Simmons", phone="(573) 889-4400",
                    address="Rural Rt 2 Box 14\nEldon, MO 65026")
    db.session.add(dale)
    db.session.flush()

    powerstroke = Vehicle(customer_id=dale.id, make="Ford", model="F-250 Super Duty",
                          year=2012, vin="1FT7W2BT5CEB00005", license_plate="MO-DS4411")
    db.session.add(powerstroke)
    db.session.flush()

    j = add_job(powerstroke, "6.7 Powerstroke — oil and filter service", "completed", 8, cost=185.00)
    add_part(j, "Diesel Oil Filter", 24.99, "NAPA")
    add_part(j, "15W-40 Diesel Oil (13qt)", 84.87, "NAPA")
    add_labor(j, mike, 0.75, "Diesel oil service, check DEF level and topped off")

    j = add_job(powerstroke, "EGR cooler replacement — overheating issue", "in_progress", 1)
    add_part(j, "EGR Cooler Kit", 389.99, "NAPA", warranty_years=1)
    add_labor(j, jake, 3.0, "Coolant drained, EGR removed, new cooler installed — still need to refill and pressure test")

    # 6. Rhonda Jean Mills — older car, budget conscious
    rhonda = Customer(name="Rhonda Jean Mills", phone="(573) 765-0033",
                      address="501 Oak Street\nCamdenton, MO 65020")
    db.session.add(rhonda)
    db.session.flush()

    cavalier = Vehicle(customer_id=rhonda.id, make="Chevrolet", model="Cavalier",
                       year=2004, license_plate="MO-RM8823")
    db.session.add(cavalier)
    db.session.flush()

    j = add_job(cavalier, "Belt squeal — belt and tensioner replacement", "completed", 35, cost=172.00)
    add_part(j, "Serpentine Belt", 29.99, "AutoZone", warranty_years=1)
    add_part(j, "Belt Tensioner", 49.99, "AutoZone", warranty_years=1)
    add_labor(j, mike, 1.0, "Replace belt and tensioner, verify alignment")

    j = add_job(cavalier, "Exhaust patch — rusted flex pipe", "completed", 19, cost=135.00)
    add_part(j, "Flex Pipe Section", 39.99, "NAPA")
    add_part(j, "Exhaust Clamps (2)", 12.00, "NAPA")
    add_labor(j, jake, 1.0, "Cut out rusted section, weld in flex pipe, seal clamps")

    j = add_job(cavalier, "Heater not working — blend door actuator", "on_hold", 6)
    add_labor(j, jake, 0.5, "Confirmed actuator failure. Customer approved repair — part on order from NAPA.")

    db.session.commit()

    click.echo("")
    click.echo("Demo database ready.")
    click.echo("")
    click.echo("  Login accounts:")
    click.echo("    davy  / demo1234  (owner)")
    click.echo("    mike  / demo1234  (mechanic — $85/hr)")
    click.echo("    jake  / demo1234  (mechanic — $75/hr)")
    click.echo("")
    click.echo("  Customers: 6")
    click.echo("  Vehicles:  9")
    click.echo("  Jobs:      22  (mix of open, in progress, on hold, completed)")


def register_commands(app: Flask) -> None:
    """Register custom CLI commands on the Flask app instance."""
    app.cli.add_command(create_db)
    app.cli.add_command(clear_db)
    app.cli.add_command(reset_password)
    app.cli.add_command(seed_demo_data)
