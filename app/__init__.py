from flask import Flask

def create_app():
    app = Flask(__name__)
    app.secret_key = "autoshop_secret"

    # --- Database config ---
    app.config["DB_HOST"] = "localhost"
    app.config["DB_USER"] = "root"
    app.config["DB_PASSWORD"] = "yourpassword"  # change this if needed
    app.config["DB_NAME"] = "autoshop"

    # --- Register blueprints ---
    from .routes import main_bp
    from .jobs import jobs_bp
    from .customers import customers_bp
    from .vehicles import vehicles_bp
    from .orders import orders_bp
    from .setup import setup_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(jobs_bp, url_prefix="/jobs")
    app.register_blueprint(customers_bp, url_prefix="/customers")
    app.register_blueprint(vehicles_bp, url_prefix="/vehicles")
    app.register_blueprint(orders_bp, url_prefix="/orders")
    app.register_blueprint(setup_bp)

    return app
