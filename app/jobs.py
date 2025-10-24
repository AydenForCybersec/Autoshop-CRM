from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
import mysql.connector

# Define the blueprint FIRST
jobs_bp = Blueprint("jobs", __name__, url_prefix="/jobs")

def get_conn():
    """Open a new MySQL connection using app config"""
    return mysql.connector.connect(
        host=current_app.config["DB_HOST"],
        user=current_app.config["DB_USER"],
        password=current_app.config["DB_PASSWORD"],
        database=current_app.config["DB_NAME"],
    )

@jobs_bp.route("/add", methods=["GET", "POST"])
def add_job():
    """Add a job and automatically create customer/vehicle if needed"""
    if request.method == "POST":
        customer_name = request.form.get("customer_name")
        phone = request.form.get("phone")
        vehicle_make = request.form.get("vehicle_make")
        vehicle_model = request.form.get("vehicle_model")
        plate = request.form.get("plate")
        description = request.form.get("description")
        total = request.form.get("total", 0)

        conn = get_conn()
        cursor = conn.cursor(dictionary=True)

        # Create or get customer
        cursor.execute("SELECT id FROM customers WHERE name=%s LIMIT 1", (customer_name,))
        customer = cursor.fetchone()
        if not customer:
            cursor.execute("INSERT INTO customers (name, phone) VALUES (%s, %s)", (customer_name, phone))
            conn.commit()
            cursor.execute("SELECT id FROM customers WHERE name=%s LIMIT 1", (customer_name,))
            customer = cursor.fetchone()
        customer_id = customer["id"]

        # Create or get vehicle
        cursor.execute("SELECT id FROM vehicles WHERE plate=%s LIMIT 1", (plate,))
        vehicle = cursor.fetchone()
        if not vehicle:
            cursor.execute(
                "INSERT INTO vehicles (make, model, plate, customer_id) VALUES (%s, %s, %s, %s)",
                (vehicle_make, vehicle_model, plate, customer_id)
            )
            conn.commit()
            cursor.execute("SELECT id FROM vehicles WHERE plate=%s LIMIT 1", (plate,))
            vehicle = cursor.fetchone()
        vehicle_id = vehicle["id"]

        # Create job (repair order)
        cursor.execute(
            "INSERT INTO repair_orders (vehicle_id, description, total, status) VALUES (%s, %s, %s, %s)",
            (vehicle_id, description, total, "open")
        )
        conn.commit()

        cursor.close()
        conn.close()

        flash("✅ Job added successfully!", "success")
        return redirect(url_for("main.dashboard"))

    return render_template("jobs_add.html")
