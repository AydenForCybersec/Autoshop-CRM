"""Report helpers (PDF/CSV generation)."""

from __future__ import annotations

from datetime import date
from pathlib import Path
import struct
from textwrap import wrap
import zlib

from ..models.job import Job
from ..models.vehicle import Vehicle
from .time import utc_now_aware, utc_now_naive


def _pdf_escape(value: str) -> str:
    """Escape content for a PDF literal string."""
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _wrap_text(value: str, *, width: int) -> list[str]:
    """Return wrapped lines with safe fallback for empty strings."""
    normalized = " ".join((value or "").split())
    if not normalized:
        return [""]
    return wrap(normalized, width=width)


def _draw_text(ops: list[str], *, x: float, y: float, text: str, font: str, size: int) -> None:
    """Append a text drawing operation for one line."""
    escaped = _pdf_escape(text)
    ops.append(f"BT /{font} {size} Tf {x:.2f} {y:.2f} Td ({escaped}) Tj ET")


def _warranty_status(expires_on: date | None, *, reference: date) -> str:
    """Return a readable warranty status label."""
    if expires_on is None:
        return "No warranty recorded"
    return "Active" if expires_on >= reference else "Expired"


class _PdfImage:
    """PDF image payload used as an XObject resource."""

    def __init__(
        self,
        *,
        width: int,
        height: int,
        data: bytes,
        image_filter: str,
        color_space: str,
        bits_per_component: int = 8,
        smask_data: bytes | None = None,
    ):
        self.width = width
        self.height = height
        self.data = data
        self.image_filter = image_filter
        self.color_space = color_space
        self.bits_per_component = bits_per_component
        self.smask_data = smask_data


def _png_paeth(left: int, up: int, up_left: int) -> int:
    """Return Paeth predictor for PNG filtering."""
    p = left + up - up_left
    pa = abs(p - left)
    pb = abs(p - up)
    pc = abs(p - up_left)
    if pa <= pb and pa <= pc:
        return left
    if pb <= pc:
        return up
    return up_left


def _unfilter_png_scanlines(raw: bytes, *, width: int, height: int, bytes_per_pixel: int) -> bytes:
    """Decode PNG scanlines into raw unfiltered pixel bytes."""
    stride = width * bytes_per_pixel
    expected = (stride + 1) * height
    if len(raw) != expected:
        raise ValueError("Unexpected PNG payload size.")

    result = bytearray(stride * height)
    src = 0
    dst = 0

    for row in range(height):
        filter_type = raw[src]
        src += 1
        current_row = bytearray(raw[src : src + stride])
        src += stride
        previous_row = result[dst - stride : dst] if row > 0 else b"\x00" * stride

        if filter_type == 0:
            pass
        elif filter_type == 1:
            for i in range(stride):
                left = current_row[i - bytes_per_pixel] if i >= bytes_per_pixel else 0
                current_row[i] = (current_row[i] + left) & 0xFF
        elif filter_type == 2:
            for i in range(stride):
                current_row[i] = (current_row[i] + previous_row[i]) & 0xFF
        elif filter_type == 3:
            for i in range(stride):
                left = current_row[i - bytes_per_pixel] if i >= bytes_per_pixel else 0
                up = previous_row[i]
                current_row[i] = (current_row[i] + ((left + up) // 2)) & 0xFF
        elif filter_type == 4:
            for i in range(stride):
                left = current_row[i - bytes_per_pixel] if i >= bytes_per_pixel else 0
                up = previous_row[i]
                up_left = previous_row[i - bytes_per_pixel] if i >= bytes_per_pixel else 0
                current_row[i] = (current_row[i] + _png_paeth(left, up, up_left)) & 0xFF
        else:
            raise ValueError("Unsupported PNG filter type.")

        result[dst : dst + stride] = current_row
        dst += stride

    return bytes(result)


def _extract_jpeg_dimensions(data: bytes) -> tuple[int, int]:
    """Return JPEG width/height by scanning SOF markers."""
    if len(data) < 4 or data[0:2] != b"\xFF\xD8":
        raise ValueError("Invalid JPEG file.")

    offset = 2
    while offset + 3 < len(data):
        if data[offset] != 0xFF:
            offset += 1
            continue
        marker = data[offset + 1]
        offset += 2

        while marker == 0xFF and offset < len(data):
            marker = data[offset]
            offset += 1

        if marker in {0xD8, 0xD9}:
            continue
        if marker == 0xDA:
            break
        if offset + 2 > len(data):
            break
        segment_length = struct.unpack(">H", data[offset : offset + 2])[0]
        if segment_length < 2 or offset + segment_length > len(data):
            break
        if marker in {
            0xC0,
            0xC1,
            0xC2,
            0xC3,
            0xC5,
            0xC6,
            0xC7,
            0xC9,
            0xCA,
            0xCB,
            0xCD,
            0xCE,
            0xCF,
        }:
            if segment_length >= 7:
                height = struct.unpack(">H", data[offset + 3 : offset + 5])[0]
                width = struct.unpack(">H", data[offset + 5 : offset + 7])[0]
                if width > 0 and height > 0:
                    return width, height
        offset += segment_length

    raise ValueError("JPEG dimensions could not be read.")


def _load_png_logo(path: Path) -> _PdfImage:
    """Load PNG bytes and convert into PDF Flate image payload."""
    data = path.read_bytes()
    signature = b"\x89PNG\r\n\x1a\n"
    if not data.startswith(signature):
        raise ValueError("Invalid PNG signature.")

    offset = len(signature)
    width = height = 0
    bit_depth = color_type = compression = png_filter = interlace = -1
    idat_payload = bytearray()

    while offset + 8 <= len(data):
        chunk_len = struct.unpack(">I", data[offset : offset + 4])[0]
        chunk_type = data[offset + 4 : offset + 8]
        chunk_data_start = offset + 8
        chunk_data_end = chunk_data_start + chunk_len
        chunk_crc_end = chunk_data_end + 4
        if chunk_crc_end > len(data):
            raise ValueError("Corrupt PNG chunk boundaries.")
        chunk_data = data[chunk_data_start:chunk_data_end]

        if chunk_type == b"IHDR":
            if chunk_len != 13:
                raise ValueError("Invalid IHDR chunk size.")
            width, height, bit_depth, color_type, compression, png_filter, interlace = struct.unpack(
                ">IIBBBBB", chunk_data
            )
        elif chunk_type == b"IDAT":
            idat_payload.extend(chunk_data)
        elif chunk_type == b"IEND":
            break

        offset = chunk_crc_end

    if width <= 0 or height <= 0:
        raise ValueError("PNG dimensions missing.")
    if bit_depth != 8 or compression != 0 or png_filter != 0 or interlace != 0:
        raise ValueError("Unsupported PNG encoding.")
    if color_type not in {2, 6}:
        raise ValueError("Unsupported PNG color mode.")

    decompressed = zlib.decompress(bytes(idat_payload))
    bpp = 3 if color_type == 2 else 4
    raw = _unfilter_png_scanlines(decompressed, width=width, height=height, bytes_per_pixel=bpp)

    if color_type == 2:
        return _PdfImage(
            width=width,
            height=height,
            data=zlib.compress(raw, level=9),
            image_filter="/FlateDecode",
            color_space="/DeviceRGB",
            bits_per_component=8,
        )

    rgb = bytearray(width * height * 3)
    alpha = bytearray(width * height)
    pixel_count = width * height
    for i in range(pixel_count):
        source = i * 4
        rgb_target = i * 3
        rgb[rgb_target : rgb_target + 3] = raw[source : source + 3]
        alpha[i] = raw[source + 3]

    return _PdfImage(
        width=width,
        height=height,
        data=zlib.compress(bytes(rgb), level=9),
        image_filter="/FlateDecode",
        color_space="/DeviceRGB",
        bits_per_component=8,
        smask_data=zlib.compress(bytes(alpha), level=9),
    )


def _load_logo_image(shop_logo_path: str | None, static_folder: str | Path | None) -> _PdfImage | None:
    """Load an uploaded logo file and convert to a PDF image resource."""
    if not shop_logo_path or not static_folder:
        return None

    static_root = Path(static_folder).resolve()
    logo_path = (static_root / shop_logo_path).resolve()
    if not logo_path.exists() or not logo_path.is_file():
        return None
    if static_root not in logo_path.parents:
        return None

    extension = logo_path.suffix.lower()
    try:
        if extension in {".jpg", ".jpeg"}:
            jpeg_data = logo_path.read_bytes()
            width, height = _extract_jpeg_dimensions(jpeg_data)
            return _PdfImage(
                width=width,
                height=height,
                data=jpeg_data,
                image_filter="/DCTDecode",
                color_space="/DeviceRGB",
                bits_per_component=8,
            )
        if extension == ".png":
            return _load_png_logo(logo_path)
    except (OSError, ValueError, zlib.error):
        return None
    return None


def _build_pdf_document(page_streams: list[str], *, logo_image: _PdfImage | None = None) -> bytes:
    """Build a valid PDF document from already-rendered page content streams."""
    page_count = len(page_streams)
    if page_count == 0:
        page_streams = ["BT /F1 11 Tf 50 750 Td (No content available.) Tj ET\n"]
        page_count = 1

    page_first_id = 3
    content_first_id = page_first_id + page_count
    font_regular_id = content_first_id + page_count
    font_bold_id = font_regular_id + 1
    image_main_id = font_bold_id + 1 if logo_image else None
    image_smask_id = (image_main_id + 1) if (logo_image and logo_image.smask_data) else None

    page_ids = [page_first_id + idx for idx in range(page_count)]
    content_ids = [content_first_id + idx for idx in range(page_count)]
    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)

    objects: list[str] = [
        "1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        f"2 0 obj\n<< /Type /Pages /Kids [{kids}] /Count {page_count} >>\nendobj\n",
    ]

    for idx, page_id in enumerate(page_ids):
        content_id = content_ids[idx]
        objects.append(
            (
                f"{page_id} 0 obj\n"
                "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                f"/Resources << /Font << /F1 {font_regular_id} 0 R /F2 {font_bold_id} 0 R >> "
                f"{f'/XObject << /Im1 {image_main_id} 0 R >> ' if image_main_id else ''}>> "
                f"/Contents {content_id} 0 R >>\n"
                "endobj\n"
            )
        )

    for idx, content_id in enumerate(content_ids):
        content_stream = page_streams[idx]
        content_bytes = content_stream.encode("latin-1", errors="replace")
        objects.append(
            f"{content_id} 0 obj\n<< /Length {len(content_bytes)} >>\nstream\n{content_stream}endstream\nendobj\n"
        )

    objects.append(
        f"{font_regular_id} 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
    )
    objects.append(
        f"{font_bold_id} 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>\nendobj\n"
    )
    if logo_image and image_main_id:
        smask_entry = f"/SMask {image_smask_id} 0 R " if image_smask_id else ""
        main_header = (
            f"{image_main_id} 0 obj\n"
            "<< /Type /XObject /Subtype /Image "
            f"/Width {logo_image.width} /Height {logo_image.height} "
            f"/ColorSpace {logo_image.color_space} /BitsPerComponent {logo_image.bits_per_component} "
            f"/Filter {logo_image.image_filter} {smask_entry}/Length {len(logo_image.data)} >>\n"
            "stream\n"
        ).encode("latin-1")
        objects.append((main_header + logo_image.data + b"\nendstream\nendobj\n").decode("latin-1"))

        if image_smask_id and logo_image.smask_data is not None:
            smask_header = (
                f"{image_smask_id} 0 obj\n"
                "<< /Type /XObject /Subtype /Image "
                f"/Width {logo_image.width} /Height {logo_image.height} "
                "/ColorSpace /DeviceGray /BitsPerComponent 8 "
                f"/Filter /FlateDecode /Length {len(logo_image.smask_data)} >>\n"
                "stream\n"
            ).encode("latin-1")
            objects.append((smask_header + logo_image.smask_data + b"\nendstream\nendobj\n").decode("latin-1"))

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


def build_vehicle_history_pdf(
    vehicle: Vehicle,
    jobs: list[Job],
    shop_name: str,
    *,
    shop_phone: str | None = None,
    shop_email: str | None = None,
    shop_address: str | None = None,
    shop_logo_path: str | None = None,
    static_folder: str | Path | None = None,
) -> bytes:
    """Build a printable PDF with branded vehicle history and warranty details."""
    page_width = 612.0
    margin_x = 44.0
    bottom_margin = 56.0
    line_height = 13.0
    body_start_y = 640.0
    section_gap = 12.0

    now = utc_now_aware().strftime("%Y-%m-%d %H:%M UTC")
    warranty_reference = utc_now_naive().date()
    vehicle_title = f"{vehicle.year or 'Year N/A'} {vehicle.make} {vehicle.model}".strip()
    shop_display_name = (shop_name or "Autoshop CRM").strip()

    contact_parts = [part.strip() for part in [shop_phone, shop_email] if part and part.strip()]
    if shop_address and shop_address.strip():
        contact_parts.append(shop_address.strip())
    contact_line = " | ".join(contact_parts) if contact_parts else "Contact details unavailable."
    logo_image = _load_logo_image(shop_logo_path, static_folder)

    pages: list[list[str]] = []
    current_ops: list[str] = []
    y = body_start_y

    def start_page() -> None:
        nonlocal current_ops, y
        current_ops = []
        pages.append(current_ops)
        y = body_start_y

        current_ops.extend(
            [
                "q 0.92 0.95 0.99 rg 0 710 612 82 re f Q",
                "q 0.90 0.90 0.90 rg 44 632 524 1 re f Q",
                "q 0.95 0.95 0.95 rg 44 140 524 468 re f Q",
            ]
        )
        _draw_text(current_ops, x=margin_x, y=760, text=shop_display_name, font="F2", size=18)
        _draw_text(current_ops, x=margin_x, y=742, text=contact_line, font="F1", size=10)
        _draw_text(current_ops, x=margin_x, y=722, text="Vehicle Service History Record", font="F2", size=13)
        _draw_text(current_ops, x=page_width - 190, y=722, text=f"Generated {now}", font="F1", size=9)
        if logo_image:
            scale = min(120.0 / logo_image.width, 48.0 / logo_image.height, 1.0)
            draw_w = logo_image.width * scale
            draw_h = logo_image.height * scale
            draw_x = page_width - margin_x - draw_w
            draw_y = 736.0
            current_ops.append(f"q {draw_w:.2f} 0 0 {draw_h:.2f} {draw_x:.2f} {draw_y:.2f} cm /Im1 Do Q")

    def ensure_space(lines_needed: int = 1, *, extra: float = 0.0) -> None:
        nonlocal y
        required = (lines_needed * line_height) + extra
        if y - required < bottom_margin:
            start_page()

    def add_heading(text: str) -> None:
        nonlocal y
        ensure_space(2, extra=section_gap)
        _draw_text(current_ops, x=margin_x, y=y, text=text, font="F2", size=12)
        y -= line_height + 2

    def add_wrapped(text: str, *, font: str = "F1", size: int = 10, width: int = 94) -> None:
        nonlocal y
        wrapped = _wrap_text(text, width=width)
        ensure_space(len(wrapped))
        for line in wrapped:
            _draw_text(current_ops, x=margin_x, y=y, text=line, font=font, size=size)
            y -= line_height

    start_page()
    add_heading("Vehicle Information")
    add_wrapped(f"Vehicle: {vehicle_title}", font="F2", size=11)
    add_wrapped(f"VIN: {vehicle.vin or 'N/A'}")
    add_wrapped(f"License Plate: {vehicle.license_plate or 'N/A'}")
    add_wrapped(f"Vehicle ID: {vehicle.id} | Customer ID: {vehicle.customer_id}")
    y -= section_gap

    add_heading("Service Jobs")
    if not jobs:
        add_wrapped("No service jobs have been recorded for this vehicle yet.")
    else:
        for index, job in enumerate(jobs, start=1):
            created = job.created_at.strftime("%Y-%m-%d") if job.created_at else "Unknown date"
            status = (job.status or "open").replace("_", " ").title()
            cost = f"${job.cost:.2f}" if job.cost is not None else "N/A"
            header = f"Job {index}: {created} | {status} | Total {cost}"
            ensure_space(3, extra=8)
            add_wrapped(header, font="F2", size=10, width=96)
            add_wrapped(f"Description: {' '.join((job.description or '').split())}", width=95)

            if job.parts:
                add_wrapped("Parts & Warranty:", font="F2", size=10, width=95)
                for part in job.parts:
                    supplier = f" from {part.supplier}" if part.supplier else ""
                    purchased = part.purchased_on.strftime("%Y-%m-%d") if part.purchased_on else "Unknown"
                    expiry = (
                        part.warranty_expires_on.strftime("%Y-%m-%d")
                        if part.warranty_expires_on
                        else "N/A"
                    )
                    duration = f"{part.warranty_years} yr" if part.warranty_years else "N/A"
                    status_label = _warranty_status(part.warranty_expires_on, reference=warranty_reference)
                    add_wrapped(f"- {part.part_name}{supplier}", width=92)
                    add_wrapped(
                        f"  Purchased: {purchased} | Warranty: {duration} | Expires: {expiry} | Status: {status_label}",
                        width=92,
                    )
                    if part.notes:
                        add_wrapped(f"  Notes: {' '.join(part.notes.split())}", width=92)
            else:
                add_wrapped("Parts & Warranty: No parts recorded on this job.", width=95)
            y -= 6

    y -= section_gap
    add_heading("Warranty Coverage Summary")
    warranty_parts = [part for job in jobs for part in job.parts if part.warranty_expires_on is not None]
    if not warranty_parts:
        add_wrapped("No warranty-backed parts have been recorded for this vehicle.")
    else:
        active_count = sum(
            1 for part in warranty_parts if part.warranty_expires_on and part.warranty_expires_on >= warranty_reference
        )
        expired_count = len(warranty_parts) - active_count
        add_wrapped(
            f"Warranty-tracked parts: {len(warranty_parts)} | Active: {active_count} | Expired: {expired_count}",
            font="F2",
            width=96,
        )
        for part in sorted(warranty_parts, key=lambda item: (item.warranty_expires_on, item.id)):
            expires = part.warranty_expires_on.strftime("%Y-%m-%d") if part.warranty_expires_on else "N/A"
            status_label = _warranty_status(part.warranty_expires_on, reference=warranty_reference)
            add_wrapped(f"- {part.part_name}: {status_label} through {expires}", width=95)

    page_count = len(pages)
    for idx, page_ops in enumerate(pages, start=1):
        _draw_text(
            page_ops,
            x=margin_x,
            y=30,
            text="This report is for service reference only. Warranty eligibility is subject to supplier terms.",
            font="F1",
            size=8,
        )
        _draw_text(page_ops, x=page_width - 94, y=30, text=f"Page {idx}/{page_count}", font="F1", size=8)

    page_streams = ["\n".join(ops) + "\n" for ops in pages]
    return _build_pdf_document(page_streams, logo_image=logo_image)
