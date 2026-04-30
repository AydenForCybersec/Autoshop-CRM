"""Curated in-app help content services."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from html import escape
from pathlib import Path
import re


@dataclass(frozen=True)
class HelpArticleMeta:
    """Metadata used on help index cards."""

    slug: str
    title: str
    summary: str
    audience: tuple[str, ...]
    updated_at: str
    related_links: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class HelpArticle(HelpArticleMeta):
    """Single help article with rendered HTML body."""

    content_html: str


@dataclass(frozen=True)
class _HelpArticleSource(HelpArticleMeta):
    """Internal article source descriptor bound to a filename."""

    filename: str


HELP_AUDIENCES: tuple[str, ...] = ("Staff", "Admin", "Developer")

HELP_ARTICLE_REGISTRY: dict[str, _HelpArticleSource] = {
    "getting-started": _HelpArticleSource(
        slug="getting-started",
        title="Getting Started",
        summary="What this program is, how to sign in, and how jobs flow from start to finish.",
        audience=("Staff", "Admin"),
        updated_at="2026-04-28",
        related_links=(
            ("Adding Customers and Vehicles", "/help/daily-workflows"),
            ("Parts and Labor", "/help/parts-and-labor"),
        ),
        filename="getting-started.md",
    ),
    "daily-workflows": _HelpArticleSource(
        slug="daily-workflows",
        title="Adding Customers and Vehicles",
        summary="How to find or add a customer, add their vehicle, and create a work order.",
        audience=("Staff", "Admin"),
        updated_at="2026-04-28",
        related_links=(
            ("Parts and Labor", "/help/parts-and-labor"),
            ("Printing an Invoice", "/help/invoices"),
        ),
        filename="daily-workflows.md",
    ),
    "parts-and-labor": _HelpArticleSource(
        slug="parts-and-labor",
        title="Tracking Parts and Labor",
        summary="How to add parts with prices, log mechanic hours, and understand how the total is calculated.",
        audience=("Staff", "Admin"),
        updated_at="2026-04-28",
        related_links=(
            ("Printing an Invoice", "/help/invoices"),
            ("Common Problems", "/help/common-problems"),
        ),
        filename="parts-and-labor.md",
    ),
    "invoices": _HelpArticleSource(
        slug="invoices",
        title="Printing an Invoice",
        summary="How to open, review, and print a customer invoice. Covers cash vs. card and the PAID stamp.",
        audience=("Staff", "Admin"),
        updated_at="2026-04-28",
        related_links=(
            ("Accounting and Reports", "/help/accounting"),
            ("Common Problems", "/help/common-problems"),
        ),
        filename="invoices.md",
    ),
    "accounting": _HelpArticleSource(
        slug="accounting",
        title="Accounting and Reports",
        summary="How to view revenue, export a spreadsheet, and print an invoice report for your accountant.",
        audience=("Admin",),
        updated_at="2026-04-28",
        related_links=(
            ("Printing an Invoice", "/help/invoices"),
            ("Owner and Admin Setup", "/help/admin-setup"),
        ),
        filename="accounting.md",
    ),
    "common-problems": _HelpArticleSource(
        slug="common-problems",
        title="Common Problems",
        summary="Something not working right? Find quick answers here.",
        audience=("Staff", "Admin"),
        updated_at="2026-04-28",
        related_links=(
            ("Getting Started", "/help/getting-started"),
            ("Adding Customers and Vehicles", "/help/daily-workflows"),
        ),
        filename="common-problems.md",
    ),
    "admin-setup": _HelpArticleSource(
        slug="admin-setup",
        title="Owner and Admin Setup",
        summary="First-time setup: shop info, tax rates, card fees, and staff accounts.",
        audience=("Admin",),
        updated_at="2026-04-28",
        related_links=(("Managing Users and Permissions", "/help/users-permissions"),),
        filename="admin-setup.md",
    ),
    "users-permissions": _HelpArticleSource(
        slug="users-permissions",
        title="Managing Users and Permissions",
        summary="Add staff accounts, set roles, configure labor rates, and fine-tune access.",
        audience=("Admin",),
        updated_at="2026-04-28",
        related_links=(("Owner and Admin Setup", "/help/admin-setup"),),
        filename="users-permissions.md",
    ),
}

_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_CODE_RE = re.compile(r"`([^`]+)`")
_ORDERED_ITEM_RE = re.compile(r"^\d+\.\s+(.+)$")
_UNORDERED_ITEM_RE = re.compile(r"^-\s+(.+)$")
_HEADING_RE = re.compile(r"^(#{1,3})\s+(.+)$")


def _help_content_root() -> Path:
    """Return absolute help content directory path."""
    return Path(__file__).resolve().parents[1] / "help_content"


def _safe_href(raw_url: str) -> str:
    """Allow only safe URL schemes for rendered links."""
    url = raw_url.strip()
    if url.startswith(("http://", "https://", "/", "#")):
        return escape(url, quote=True)
    return "#"


def _render_inline(text: str) -> str:
    """Render safe inline markdown-like tokens."""
    escaped = escape(text)
    escaped = _CODE_RE.sub(lambda match: f"<code>{escape(match.group(1))}</code>", escaped)

    def _replace_link(match: re.Match[str]) -> str:
        label = escape(match.group(1))
        href = _safe_href(match.group(2))
        return f'<a href="{href}">{label}</a>'

    return _LINK_RE.sub(_replace_link, escaped)


def _render_markdown(markdown_text: str) -> str:
    """Render a constrained markdown subset to safe HTML."""
    parts: list[str] = []
    in_ul = False
    in_ol = False

    def close_lists() -> None:
        nonlocal in_ul, in_ol
        if in_ul:
            parts.append("</ul>")
            in_ul = False
        if in_ol:
            parts.append("</ol>")
            in_ol = False

    for raw_line in markdown_text.splitlines():
        line = raw_line.strip()
        if not line:
            close_lists()
            continue

        heading_match = _HEADING_RE.match(line)
        if heading_match:
            close_lists()
            level = len(heading_match.group(1))
            parts.append(f"<h{level}>{_render_inline(heading_match.group(2))}</h{level}>")
            continue

        unordered_match = _UNORDERED_ITEM_RE.match(line)
        if unordered_match:
            if in_ol:
                parts.append("</ol>")
                in_ol = False
            if not in_ul:
                parts.append("<ul>")
                in_ul = True
            parts.append(f"<li>{_render_inline(unordered_match.group(1))}</li>")
            continue

        ordered_match = _ORDERED_ITEM_RE.match(line)
        if ordered_match:
            if in_ul:
                parts.append("</ul>")
                in_ul = False
            if not in_ol:
                parts.append("<ol>")
                in_ol = True
            parts.append(f"<li>{_render_inline(ordered_match.group(1))}</li>")
            continue

        close_lists()
        parts.append(f"<p>{_render_inline(line)}</p>")

    close_lists()
    return "\n".join(parts)


@lru_cache(maxsize=32)
def _load_article(slug: str) -> HelpArticle | None:
    """Load and render one curated article by slug."""
    source = HELP_ARTICLE_REGISTRY.get(slug)
    if source is None:
        return None

    root = _help_content_root().resolve()
    candidate = (root / source.filename).resolve()
    if root not in candidate.parents:
        return None
    if not candidate.is_file():
        return None

    markdown_text = candidate.read_text(encoding="utf-8")
    return HelpArticle(
        slug=source.slug,
        title=source.title,
        summary=source.summary,
        audience=source.audience,
        updated_at=source.updated_at,
        related_links=source.related_links,
        content_html=_render_markdown(markdown_text),
    )


def get_help_index(role_key: str | None = None, audience: str | None = None) -> list[HelpArticleMeta]:
    """Return sorted help metadata for index display.

    role_key is accepted for future role-tailored ordering.
    """
    del role_key
    selected = audience.strip() if audience else None
    results: list[HelpArticleMeta] = []
    for source in HELP_ARTICLE_REGISTRY.values():
        if selected and selected not in source.audience:
            continue
        results.append(
            HelpArticleMeta(
                slug=source.slug,
                title=source.title,
                summary=source.summary,
                audience=source.audience,
                updated_at=source.updated_at,
                related_links=source.related_links,
            )
        )
    return sorted(results, key=lambda item: item.title.lower())


def get_help_article(slug: str) -> HelpArticle | None:
    """Return rendered help article or None when slug is not valid."""
    return _load_article(slug)
