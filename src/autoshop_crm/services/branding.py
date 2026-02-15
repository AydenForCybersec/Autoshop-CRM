"""Shared branding utilities for logo upload and validation."""

from __future__ import annotations

from pathlib import Path
import uuid

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

ALLOWED_LOGO_EXTENSIONS = frozenset({"png", "jpg", "jpeg", "webp", "gif", "svg"})


def save_business_logo(logo_file: FileStorage | None, static_folder: str | Path) -> str | None:
    """Persist a validated logo upload and return its static-relative path."""
    if logo_file is None or not logo_file.filename:
        return None

    extension = Path(logo_file.filename).suffix.lower().lstrip(".")
    if extension not in ALLOWED_LOGO_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_LOGO_EXTENSIONS))
        raise ValueError(f"Logo must be one of: {allowed}.")

    filename_stem = secure_filename(Path(logo_file.filename).stem) or "shop-logo"
    unique_name = f"{filename_stem}-{uuid.uuid4().hex[:8]}.{extension}"

    logo_dir = Path(static_folder) / "uploads" / "logos"
    logo_dir.mkdir(parents=True, exist_ok=True)
    logo_file.save(logo_dir / unique_name)
    return f"uploads/logos/{unique_name}"
