import click
from flask.cli import with_appcontext

from .extensions import db


@click.command("create-db")
@with_appcontext
def create_db():
    db.create_all()
    click.echo("Database created")


def register_commands(app):
    app.cli.add_command(create_db)
