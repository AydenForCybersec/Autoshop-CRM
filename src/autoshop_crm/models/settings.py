"""Business settings model for first-run setup and branding."""

from ..extensions import db


class BusinessSettings(db.Model):
    """Singleton settings row containing business identity fields."""

    __tablename__ = "settings"

    id = db.Column(db.Integer, primary_key=True)
    shop_name = db.Column(db.String(120), nullable=False)
    shop_phone = db.Column(db.String(50))
    shop_email = db.Column(db.String(120))
    shop_address = db.Column(db.Text)
    shop_logo = db.Column(db.String(255))
    setup_complete = db.Column(db.Boolean, nullable=False, default=False)
