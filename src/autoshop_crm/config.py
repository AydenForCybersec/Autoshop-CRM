"""Environment-driven application configuration objects."""

import os
import secrets
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

    SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_hex(32)

    DEFAULT_SQLITE_PATH = Path(__file__).resolve().parents[2] / "autoshop.db"
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{DEFAULT_SQLITE_PATH.as_posix()}",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Flask settings
    TEMPLATES_AUTO_RELOAD = True
    WTF_CSRF_TIME_LIMIT = _env_int("WTF_CSRF_TIME_LIMIT", 3600)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = os.getenv("REMEMBER_COOKIE_SAMESITE", "Lax")
    MAX_CONTENT_LENGTH = _env_int("MAX_CONTENT_LENGTH", 8 * 1024 * 1024)

    # Login throttling guardrails
    AUTH_MAX_ATTEMPTS = _env_int("AUTH_MAX_ATTEMPTS", 5)
    AUTH_WINDOW_SECONDS = _env_int("AUTH_WINDOW_SECONDS", 300)
    AUTH_LOCKOUT_SECONDS = _env_int("AUTH_LOCKOUT_SECONDS", 900)

    # In-app update management settings
    PROJECT_ROOT = str(Path(__file__).resolve().parents[2])
    UPDATE_ENABLED = _env_bool("UPDATE_ENABLED", default=False)
    UPDATE_REPO_PATH = os.getenv("UPDATE_REPO_PATH", PROJECT_ROOT)
    UPDATE_REMOTE = os.getenv("UPDATE_REMOTE", "origin")
    UPDATE_BRANCH = os.getenv("UPDATE_BRANCH", "").strip() or None
    UPDATE_LOCAL_ONLY = _env_bool("UPDATE_LOCAL_ONLY", default=True)
    UPDATE_CONFIRM_PHRASE = os.getenv("UPDATE_CONFIRM_PHRASE", "CONFIRM")
    UPDATE_ALLOW_DIRTY = _env_bool("UPDATE_ALLOW_DIRTY", default=False)
    UPDATE_ROLLBACK_LIMIT = _env_int("UPDATE_ROLLBACK_LIMIT", default=6)
    UPDATE_COMMAND_TIMEOUT = _env_int("UPDATE_COMMAND_TIMEOUT", default=300)
    UPDATE_POST_UPDATE_COMMANDS = _env_list("UPDATE_POST_UPDATE_COMMANDS")
    UPDATE_POST_ROLLBACK_COMMANDS = _env_list("UPDATE_POST_ROLLBACK_COMMANDS")
    UPDATE_ALLOWED_COMMAND_PREFIXES = _env_list("UPDATE_ALLOWED_COMMAND_PREFIXES")


class DevelopmentConfig(Config):
    """Configuration for local development."""

    DEBUG = True
    UPDATE_ENABLED = _env_bool("UPDATE_ENABLED", default=True)


class ProductionConfig(Config):
    """Configuration for production deployments."""

    DEBUG = False
    TEMPLATES_AUTO_RELOAD = False
    SESSION_COOKIE_SECURE = _env_bool("SESSION_COOKIE_SECURE", default=True)
    REMEMBER_COOKIE_SECURE = _env_bool("REMEMBER_COOKIE_SECURE", default=True)
    PREFERRED_URL_SCHEME = os.getenv("PREFERRED_URL_SCHEME", "https")


def is_placeholder_secret(value: str | None) -> bool:
    """Return True when the configured secret key is missing or a placeholder."""
    if not value:
        return True
    normalized = value.strip().lower()
    return normalized in {"change-me-in-production", "changeme", "replace-me"}


def get_config() -> Type[Config]:
    """Return the configuration class based on ``FLASK_ENV``."""
    env = os.getenv("FLASK_ENV", "development").lower()

    if env == "production":
        return ProductionConfig

    return DevelopmentConfig
