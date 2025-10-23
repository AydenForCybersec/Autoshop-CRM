import mysql.connector
from flask import current_app

def create_settings_table():
    conn = mysql.connector.connect(
        host=current_app.config["DB_HOST"],
        port=current_app.config["DB_PORT"],
        database=current_app.config["DB_NAME"],
        user=current_app.config["DB_USER"],
        password=current_app.config["DB_PASSWORD"],
    )
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            id INT AUTO_INCREMENT PRIMARY KEY,
            shop_name VARCHAR(100),
            shop_phone VARCHAR(20),
            shop_email VARCHAR(100),
            shop_address TEXT,
            shop_logo VARCHAR(255),
            setup_complete BOOLEAN DEFAULT FALSE
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()
