from flask import Blueprint, jsonify
from .database import get_db_connection

main = Blueprint("main", __name__)

@main.route("/")
def index():
    conn = mysql.connector.connect(
        host=current_app.config["DB_HOST"],
        user=current_app.config["DB_USER"],
        password=current_app.config["DB_PASSWORD"],
        database=current_app.config["DB_NAME"]
    )
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT setup_complete FROM settings LIMIT 1;")
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if not row or not row["setup_complete"]:
        return redirect(url_for("setup.setup"))

    return "✅ CRM Dashboard (coming soon)"
