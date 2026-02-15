"""UI preference model for dashboard and theme customization."""

from ..extensions import db


class AppPreference(db.Model):
    """Singleton preferences for UI colors and dashboard behavior."""

    __tablename__ = "app_preferences"

    id = db.Column(db.Integer, primary_key=True)
    primary_color = db.Column(db.String(7), nullable=False, default="#1f7a4f")
    accent_color = db.Column(db.String(7), nullable=False, default="#d29a2f")
    background_color = db.Column(db.String(7), nullable=False, default="#f4f7f4")
    surface_color = db.Column(db.String(7), nullable=False, default="#ffffff")
    text_color = db.Column(db.String(7), nullable=False, default="#1d2a22")
    muted_color = db.Column(db.String(7), nullable=False, default="#607164")
    line_color = db.Column(db.String(7), nullable=False, default="#d7e3da")
    success_color = db.Column(db.String(7), nullable=False, default="#1f7a4f")
    warning_color = db.Column(db.String(7), nullable=False, default="#8e5d13")
    danger_color = db.Column(db.String(7), nullable=False, default="#b34444")
    radius_px = db.Column(db.Integer, nullable=False, default=16)
    dashboard_jobs_limit = db.Column(db.Integer, nullable=False, default=6)
