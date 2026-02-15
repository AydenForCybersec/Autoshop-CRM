"""Environment-driven application configuration objects."""

import os
from typing import Type


class Config:
    """Base configuration shared across environments."""

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")

    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "sqlite:///autoshop.db",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Flask settings
    TEMPLATES_AUTO_RELOAD = True


class DevelopmentConfig(Config):
    """Configuration for local development."""

    DEBUG = True


class ProductionConfig(Config):
    """Configuration for production deployments."""

    DEBUG = False


def get_config() -> Type[Config]:
    """Return the configuration class based on ``FLASK_ENV``."""
    env = os.getenv("FLASK_ENV", "development").lower()

    if env == "production":
        return ProductionConfig

    return DevelopmentConfig
