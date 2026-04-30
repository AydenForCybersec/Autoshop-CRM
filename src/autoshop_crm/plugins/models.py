"""DB model for plugin installation state."""

from __future__ import annotations

from datetime import datetime

from ..extensions import db


class PluginState(db.Model):
    """Tracks each installed plugin's enabled state and settings."""

    __tablename__ = "plugin_states"

    id = db.Column(db.Integer, primary_key=True)
    plugin_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    enabled = db.Column(db.Boolean, nullable=False, default=True)
    settings = db.Column(db.JSON, nullable=False, default=dict)
    installed_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    failed = db.Column(db.Boolean, nullable=False, default=False)
    fail_reason = db.Column(db.Text, nullable=True)
