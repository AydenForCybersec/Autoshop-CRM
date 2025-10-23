from flask import Blueprint, render_template, request, redirect, url_for
import mysql.connector
from flask import current_app

setup_bp = Blueprint("setup", __name__)

@setup_bp.route("/setup", methods=["GET", "POST"])
def setup():
    if request.method == "POST":
        data = {
            "shop_name": request.form["shop_name"],
            "shop_phone": request.form["shop_phone"],
            "shop_email": request.form["shop_email"],
            "shop_address": request.form["shop_address"]
        }

        conn = mysql.connector.connect(
            host=current_app.config["DB_HOST"],
            user=current_app.config["DB_USER"],
            password=current_app.config["DB_PASSWORD"],
            database=current_app.config["DB_NAME"]
        )
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO settings (shop_name, shop_phone, shop_email, shop_address, setup_complete)
            VALUES (%s, %s, %s, %s, TRUE)
        """, tuple(data.values()))
        conn.commit()
        cursor.close()
        conn.close()

        return redirect(url_for("main.index"))

    return render_template("setup.html")
