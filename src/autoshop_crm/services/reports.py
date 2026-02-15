"""Report helpers (PDF/CSV generation)."""

from __future__ import annotations

from datetime import datetime

from ..models.job import Job
from ..models.vehicle import Vehicle


def _pdf_escape(value: str) -> str:
    """Escape content for a PDF literal string."""
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def build_vehicle_history_pdf(vehicle: Vehicle, jobs: list[Job], shop_name: str) -> bytes:
    """Build a simple one-page PDF with vehicle service history."""
    lines: list[str] = []
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    title = f"{vehicle.year or 'Year N/A'} {vehicle.make} {vehicle.model}".strip()

    lines.append(shop_name or "Autoshop CRM")
    lines.append("Vehicle Service History")
    lines.append(f"Generated: {now}")
    lines.append("")
    lines.append(f"Vehicle ID: {vehicle.id}")
    lines.append(f"Customer ID: {vehicle.customer_id}")
    lines.append(f"Vehicle: {title}")
    lines.append(f"VIN: {vehicle.vin or 'N/A'}")
    lines.append(f"Plate: {vehicle.license_plate or 'N/A'}")
    lines.append("")
    lines.append("Jobs:")

    if not jobs:
        lines.append("No jobs recorded.")
    else:
        for job in jobs:
            created = job.created_at.strftime("%Y-%m-%d") if job.created_at else "Unknown date"
            status = (job.status or "open").replace("_", " ").title()
            cost = f"${job.cost:.2f}" if job.cost is not None else "N/A"
            description = " ".join((job.description or "").split())
            lines.append(f"- {created} | {status} | {cost} | {description}")

    max_lines = 52
    lines = lines[:max_lines]

    content_lines = ["BT", "/F1 11 Tf", "50 780 Td", "14 TL"]
    for i, line in enumerate(lines):
        escaped = _pdf_escape(line)
        if i == 0:
            content_lines.append(f"({escaped}) Tj")
        else:
            content_lines.append(f"T* ({escaped}) Tj")
    content_lines.append("ET")
    content_stream = "\n".join(content_lines) + "\n"
    content_bytes = content_stream.encode("latin-1", errors="replace")

    objects = [
        "1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        "2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
        (
            "3 0 obj\n"
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            "/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>\n"
            "endobj\n"
        ),
        f"4 0 obj\n<< /Length {len(content_bytes)} >>\nstream\n{content_stream}endstream\nendobj\n",
        "5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
    ]

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(len(pdf))
        pdf.extend(obj.encode("latin-1"))

    xref_start = len(pdf)
    pdf.extend(f"xref\n0 {len(offsets)}\n".encode("latin-1"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("latin-1"))
    pdf.extend(
        (
            f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\n"
            f"startxref\n{xref_start}\n%%EOF\n"
        ).encode("latin-1")
    )
    return bytes(pdf)
