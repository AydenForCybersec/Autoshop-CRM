import os
from pathlib import Path
from flask import Flask
from dotenv import load_dotenv
from .auth import auth_bp, init_login  # ✅ import here

env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

def create_app():
    app = Flask(__name__, instance_relative_config=False)
    
    # base config
    app.config.from_object('app.config.Config')

    # override DB config from environment if present (ensures .env values used)
    app.config['SQLALCHEMY_DATABASE_URI'] = (
        f"mysql+mysqlconnector://{os.getenv('DB_USER', app.config.get('DB_USER'))}:"
        f"{os.getenv('DB_PASSWORD', app.config.get('DB_PASSWORD'))}@"
        f"{os.getenv('DB_HOST', app.config.get('DB_HOST'))}:"
        f"{os.getenv('DB_PORT', app.config.get('DB_PORT', 3306))}/"
        f"{os.getenv('DB_NAME', app.config.get('DB_NAME'))}"
    )

    # init extensions
    from .database import db, migrate
    db.init_app(app)
    migrate.init_app(app, db)
    init_login(app)  # ✅ this line actually enables current_user globally

    # blueprints
    from .setup import setup_bp
    from .main import main_bp
    from .customers import customers_bp
    from .vehicles import vehicles_bp
    from .orders import orders_bp

    app.register_blueprint(setup_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(customers_bp, url_prefix="/customers")
    app.register_blueprint(vehicles_bp, url_prefix="/vehicles")
    app.register_blueprint(orders_bp, url_prefix="/orders")

    return app
