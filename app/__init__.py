from flask import Flask
from app.routes_setup import setup_bp
from app.routes import main

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    app.register_blueprint(main)
    app.register_blueprint(setup_bp)

    return app
