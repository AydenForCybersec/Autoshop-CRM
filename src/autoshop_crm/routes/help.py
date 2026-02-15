"""In-app help center routes."""

from __future__ import annotations

from flask import Blueprint, abort, redirect, render_template, request, url_for
from flask.typing import ResponseReturnValue
from flask_login import current_user

from ..models.user import User
from ..services.authorization import require_permission
from ..services.help import HELP_AUDIENCES, get_help_article, get_help_index

help_bp = Blueprint("help", __name__)


@help_bp.route("/help")
@require_permission("view_dashboard")
def index() -> ResponseReturnValue:
    """Render help home with audience filters."""
    selected_audience = request.args.get("audience", "").strip().title()
    if selected_audience not in HELP_AUDIENCES:
        selected_audience = ""

    role_key = current_user.role_key if current_user.is_authenticated else None
    articles = get_help_index(role_key=role_key, audience=selected_audience or None)

    return render_template(
        "help/index.html",
        title="Help Center",
        selected_audience=selected_audience,
        audience_filters=HELP_AUDIENCES,
        articles=articles,
    )


@help_bp.route("/help/<slug>")
@require_permission("view_dashboard")
def article(slug: str) -> ResponseReturnValue:
    """Render one help article from curated registry."""
    help_article = get_help_article(slug)
    if help_article is None:
        abort(404)

    return render_template(
        "help/article.html",
        title=help_article.title,
        summary=help_article.summary,
        audience=help_article.audience,
        updated_at=help_article.updated_at,
        content_html=help_article.content_html,
        related_links=help_article.related_links,
    )


@help_bp.route("/help/quick-start")
def quick_start() -> ResponseReturnValue:
    """Allow first-run setups to open a minimal public getting-started guide."""
    has_user = User.query.first() is not None
    if has_user and not current_user.is_authenticated:
        return redirect(url_for("auth.login_view"))

    help_article = get_help_article("getting-started")
    if help_article is None:
        abort(404)

    return render_template(
        "help/article.html",
        title=help_article.title,
        summary=help_article.summary,
        audience=help_article.audience,
        updated_at=help_article.updated_at,
        content_html=help_article.content_html,
        related_links=help_article.related_links,
    )
