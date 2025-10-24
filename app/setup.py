from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
import mysql.connector

setup_bp = Blueprint("setup", __name__, url_prefix="/setup")

def get_conn():
    """Open a new MySQL connection using app config"""
    return mysql.connector.connect(
        host=current_app.config["DB_HOST"],
        user=current_app.config["DB_USER"],
        password=current_app.config["DB_PASSWORD"],
        database=current_app.config["DB_NAME"],
    )


def needs_setup():
    """Check if setup_complete flag exists and is true."""
    try:
        conn = get_conn()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT setup_complete FROM settings LIMIT 1;")
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        return not (row and row.get("setup_complete"))
    except Exception:
        return True


@setup_bp.before_app_request
def redirect_if_unset():
    """Redirect to setup page if the system isn’t initialized yet."""
    from flask import request
    if not request.path.startswith("/setup") and needs_setup():
        return redirect(url_for("setup.setup"))
    return None


@setup_bp.route("/", methods=["GET", "POST"])
def setup():
    """Render setup page or process setup form submission."""
    if request.method == "POST":
        shop_name = request.form.get("shop_name")
        shop_phone = request.form.get("shop_phone")
        shop_email = request.form.get("shop_email")
        shop_address = request.form.get("shop_address")

        conn = get_conn()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id FROM settings LIMIT 1;")
        existing = cursor.fetchone()

        if existing:
            cursor.execute(
                """
                UPDATE settings
                SET shop_name=%s, shop_phone=%s, shop_email=%s, shop_address=%s, setup_complete=1
                WHERE id=%s
                """,
                (shop_name, shop_phone, shop_email, shop_address, existing["id"]),
            )
        else:
            cursor.execute(
                """
                INSERT INTO settings (shop_name, shop_phone, shop_email, shop_address, setup_complete)
                VALUES (%s, %s, %s, %s, 1)
                """,
                (shop_name, shop_phone, shop_email, shop_address),
            )

        conn.commit()
        cursor.close()
        conn.close()

        flash("✅ Setup complete!", "success")
        return redirect(url_for("main.dashboard"))

    # GET — load existing data if present
    conn = get_conn()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM settings LIMIT 1;")
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    return render_template("setup.html", settings=row or {})
