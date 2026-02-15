import click
from flask.cli import with_appcontext

from .extensions import db
from .models.customer import Customer
from .models.job import Job
from .models.user import User
from .models.vehicle import Vehicle


@click.command("create-db")
@with_appcontext
def create_db():
    db.create_all()
    click.echo("Database created")


@click.command("seed-demo-data")
@click.option("--username", default="demo", show_default=True, help="Username for demo login user.")
@click.option("--password", default="demo123", show_default=True, help="Password for demo login user.")
@with_appcontext
def seed_demo_data(username: str, password: str):
    """Seed demo users, customers, vehicles, and jobs."""
    db.create_all()

    user = User.query.filter_by(username=username).first()
    if not user:
        user = User(username=username)
        user.set_password(password)
        db.session.add(user)

    demo_customers = [
        {
            "name": "Jordan Lee",
            "email": "jordan.lee@example.com",
            "phone": "555-0101",
            "vehicles": [
                {
                    "make": "Toyota",
                    "model": "Camry",
                    "year": 2018,
                    "jobs": [
                        {"description": "Oil change and filter", "status": "open", "cost": 79.99},
                        {"description": "Brake pad replacement", "status": "in_progress", "cost": 320.00},
                    ],
                },
                {
                    "make": "Subaru",
                    "model": "Outback",
                    "year": 2020,
                    "jobs": [
                        {"description": "Tire rotation", "status": "completed", "cost": 49.99},
                    ],
                },
            ],
        },
        {
            "name": "Priya Patel",
            "email": "priya.patel@example.com",
            "phone": "555-0102",
            "vehicles": [
                {
                    "make": "Honda",
                    "model": "Civic",
                    "year": 2017,
                    "jobs": [
                        {"description": "Battery diagnostic", "status": "open", "cost": 35.00},
                        {"description": "Alternator replacement", "status": "on_hold", "cost": 540.00},
                    ],
                }
            ],
        },
        {
            "name": "Marta Garcia",
            "email": "marta.garcia@example.com",
            "phone": "555-0103",
            "vehicles": [
                {
                    "make": "Ford",
                    "model": "F-150",
                    "year": 2015,
                    "jobs": [
                        {"description": "Transmission inspection", "status": "in_progress", "cost": 180.00},
                        {"description": "Coolant flush", "status": "completed", "cost": 120.00},
                    ],
                },
                {
                    "make": "Tesla",
                    "model": "Model 3",
                    "year": 2022,
                    "jobs": [
                        {"description": "Cabin air filter replacement", "status": "open", "cost": 65.00},
                    ],
                },
            ],
        },
    ]

    for customer_data in demo_customers:
        customer = Customer.query.filter_by(email=customer_data["email"]).first()
        if customer:
            continue

        customer = Customer(
            name=customer_data["name"],
            email=customer_data["email"],
            phone=customer_data["phone"],
        )
        db.session.add(customer)
        db.session.flush()

        for vehicle_data in customer_data["vehicles"]:
            vehicle = Vehicle(
                customer_id=customer.id,
                make=vehicle_data["make"],
                model=vehicle_data["model"],
                year=vehicle_data["year"],
            )
            db.session.add(vehicle)
            db.session.flush()

            for job_data in vehicle_data["jobs"]:
                db.session.add(
                    Job(
                        vehicle_id=vehicle.id,
                        description=job_data["description"],
                        status=job_data["status"],
                        cost=job_data["cost"],
                    )
                )

    db.session.commit()

    click.echo("Demo data seeded")
    click.echo(f"Login with username='{username}' and password='{password}'")


def register_commands(app):
    app.cli.add_command(create_db)
    app.cli.add_command(seed_demo_data)
