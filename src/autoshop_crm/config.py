import os


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")

    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "sqlite:///autoshop.db",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Flask settings
    TEMPLATES_AUTO_RELOAD = True


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


def get_config():
    env = os.getenv("FLASK_ENV", "development").lower()

    if env == "production":
        return ProductionConfig

    return DevelopmentConfig
