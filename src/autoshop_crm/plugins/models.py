"""DB model for plugin installation state."""

from __future__ import annotations

from ..extensions import db
from ..services.time import utc_now_naive


class PluginState(db.Model):
    """Tracks each installed plugin's enabled state and settings."""

    __tablename__ = "plugin_states"

    id = db.Column(db.Integer, primary_key=True)
    plugin_id = db.Column(db.String(64), unique=True, nullable=False)
    enabled = db.Column(db.Boolean, nullable=False, default=True)
    settings = db.Column(db.JSON, nullable=False, default=dict)
    installed_at = db.Column(db.DateTime, nullable=False, default=utc_now_naive)
    failed = db.Column(db.Boolean, nullable=False, default=False)
    fail_reason = db.Column(db.Text, nullable=True)

    def __repr__(self) -> str:
        return f"<PluginState {self.id} {self.plugin_id!r}>"
