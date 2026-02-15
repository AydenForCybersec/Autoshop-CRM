"""Environment-driven application configuration objects."""

import os
from pathlib import Path
from typing import Type


def _env_bool(name: str, default: bool = False) -> bool:
    """Return True when env var is a truthy value."""
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _env_list(name: str) -> tuple[str, ...]:
    """Return comma-delimited env var items as a tuple."""
    raw_value = os.getenv(name, "")
    return tuple(item.strip() for item in raw_value.split(",") if item.strip())


def _env_int(name: str, default: int) -> int:
    """Return integer env var value with safe fallback."""
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        return int(raw_value.strip())
    except ValueError:
        return default


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

    # In-app update management settings
    PROJECT_ROOT = str(Path(__file__).resolve().parents[2])
    UPDATE_ENABLED = _env_bool("UPDATE_ENABLED", default=True)
    UPDATE_REPO_PATH = os.getenv("UPDATE_REPO_PATH", PROJECT_ROOT)
    UPDATE_REMOTE = os.getenv("UPDATE_REMOTE", "origin")
    UPDATE_BRANCH = os.getenv("UPDATE_BRANCH", "").strip() or None
    UPDATE_ALLOW_DIRTY = _env_bool("UPDATE_ALLOW_DIRTY", default=False)
    UPDATE_ROLLBACK_LIMIT = _env_int("UPDATE_ROLLBACK_LIMIT", default=6)
    UPDATE_COMMAND_TIMEOUT = _env_int("UPDATE_COMMAND_TIMEOUT", default=300)
    UPDATE_POST_UPDATE_COMMANDS = _env_list("UPDATE_POST_UPDATE_COMMANDS")
    UPDATE_POST_ROLLBACK_COMMANDS = _env_list("UPDATE_POST_ROLLBACK_COMMANDS")


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
