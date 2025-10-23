from flask import Blueprint, render_template, redirect, url_for, request, flash
from .models import Setting
from .database import db
import os
from flask import current_app

setup_bp = Blueprint("setup", __name__, template_folder="templates")

def needs_setup():
    s = Setting.query.first()
    return not s or not s.setup_complete

@setup_bp.before_app_request
def redirect_if_unset():
    # allow static files, setup routes and login routes through
    if request.endpoint and request.endpoint.startswith(("setup.", "auth.")):
        return
    # if setup not complete, redirect to setup page
    if needs_setup():
        return redirect(url_for("setup.setup"))

@setup_bp.route("/setup", methods=["GET", "POST"])
def setup():
    s = Setting.query.first()
    if request.method == "POST":
        shop_name = request.form.get("shop_name")
        shop_phone = request.form.get("shop_phone")
        shop_email = request.form.get("shop_email")
        shop_address = request.form.get("shop_address")
        # handle logo upload
        logo = request.files.get("shop_logo")
        logo_filename = None
        if logo:
            os.makedirs(current_app.instance_path + "/uploads", exist_ok=True)
            logo_filename = os.path.join("uploads", logo.filename)
            logo.save(os.path.join(current_app.instance_path, logo_filename))
        if not s:
            s = Setting(shop_name=shop_name, shop_phone=shop_phone,
                        shop_email=shop_email, shop_address=shop_address,
                        shop_logo=logo_filename, setup_complete=True)
            db.session.add(s)
        else:
            s.shop_name = shop_name
            s.shop_phone = shop_phone
            s.shop_email = shop_email
            s.shop_address = shop_address
            s.shop_logo = logo_filename
            s.setup_complete = True
        db.session.commit()
        flash("Setup complete. You can now log in.", "success")
        return redirect(url_for("auth.login"))
    return render_template("setup.html", settings=s)
