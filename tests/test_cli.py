"""Tests for custom Flask CLI commands."""

from autoshop_crm.models.customer import Customer
from autoshop_crm.models.job import Job
from autoshop_crm.models.user import User
from autoshop_crm.models.vehicle import Vehicle


def test_seed_demo_data_command(app):
    """Seed command should populate expected demo entities."""
    runner = app.test_cli_runner()

    result = runner.invoke(args=["seed-demo-data"])

    assert result.exit_code == 0
    assert "Demo data seeded" in result.output

    assert User.query.filter_by(username="demo").count() == 1
    assert Customer.query.count() >= 3
    assert Vehicle.query.count() >= 5
    assert Job.query.count() >= 8

    statuses = {status for (status,) in Job.query.with_entities(Job.status).distinct().all()}
    assert {"open", "in_progress", "completed", "on_hold"}.issubset(statuses)


def test_seed_demo_data_is_idempotent_for_user_and_customers(app):
    """Re-running seed should not duplicate user/customer records."""
    runner = app.test_cli_runner()

    first_run = runner.invoke(args=["seed-demo-data", "--username", "owner"])
    second_run = runner.invoke(args=["seed-demo-data", "--username", "owner"])

    assert first_run.exit_code == 0
    assert second_run.exit_code == 0
    assert User.query.filter_by(username="owner").count() == 1
    assert Customer.query.count() == 3
