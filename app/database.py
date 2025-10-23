import mysql.connector
from mysql.connector import Error
from flask import current_app
import logging

def get_db_connection():
    """Create and return a MySQL connection."""
    try:
        conn = mysql.connector.connect(
            host=current_app.config["DB_HOST"],
            port=current_app.config["DB_PORT"],
            database=current_app.config["DB_NAME"],
            user=current_app.config["DB_USER"],
            password=current_app.config["DB_PASSWORD"],
        )
        return conn
    except Error as e:
        logging.error(f"❌ Database connection failed: {e}")
        raise
