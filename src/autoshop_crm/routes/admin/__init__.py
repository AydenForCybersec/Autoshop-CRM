"""Admin panel blueprint package."""

from flask import Blueprint

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

from . import panel  # noqa: E402, F401
from . import updates_ui  # noqa: E402, F401
from . import danger  # noqa: E402, F401
from . import plugins_ui  # noqa: E402, F401
