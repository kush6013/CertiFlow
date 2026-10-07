import os
import math
from pathlib import Path
from typing import Any, Dict, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph

from app.config import STORAGE_DIR


def draw_geometric_corner(c: canvas.Canvas, x: float, y: float, size: float = 24):
    """Draws a clean decorative gold corner ornament."""
    c.saveState()
    c.setStrokeColor(colors.HexColor("#b45309"))
    c.setFillColor(colors.HexColor("#d97706"))
    c.setLineWidth(1.5)
    c.rect(x - size/2, y - size/2, size, size, stroke=1, fill=0)
    c.circle(x, y, size/4, stroke=1, fill=1)
    c.restoreState()


def draw_certificate_seal(c: canvas.Canvas, cx: float, cy: float, radius: float = 38):
    """Draws a rich vector gold seal with rosette points and inner star."""
    c.saveState()
    # Ribbon tail
    c.setFillColor(colors.HexColor("#92400e"))
    c.setStrokeColor(colors.HexColor("#78350f"))
    c.setLineWidth(1)
    # Left ribbon
    path_l = c.beginPath()
    path_l.moveTo(cx - 15, cy - radius + 10)
    path_l.lineTo(cx - 30, cy - radius - 35)
    path_l.lineTo(cx - 15, cy - radius - 25)
    path_l.lineTo(cx, cy - radius - 35)
    path_l.lineTo(cx - 5, cy - radius + 10)
    c.drawPath(path_l, fill=1, stroke=1)

    # Right ribbon
    path_r = c.beginPath()
    path_r.moveTo(cx + 5, cy - radius + 10)
    path_r.lineTo(cx, cy - radius - 35)
    path_r.lineTo(cx + 15, cy - radius - 25)
    path_r.lineTo(cx + 30, cy - radius - 35)
    path_r.lineTo(cx + 15, cy - radius + 10)
    c.drawPath(path_r, fill=1, stroke=1)

    # Rosette scalloped edge
    c.setFillColor(colors.HexColor("#d97706"))
    c.setStrokeColor(colors.HexColor("#b45309"))
    points = 32
    outer_r = radius
    inner_r = radius - 4
    path_star = c.beginPath()
    for i in range(points * 2):
        angle = i * math.pi / points
        r = outer_r if i % 2 == 0 else inner_r
        px = cx + r * math.cos(angle)
        py = cy + r * math.sin(angle)
        if i == 0:
            path_star.moveTo(px, py)
        else:
            path_star.lineTo(px, py)
    path_star.close()
    c.drawPath(path_star, fill=1, stroke=1)

    # Inner medallion
    c.setFillColor(colors.HexColor("#fef3c7"))
    c.setStrokeColor(colors.HexColor("#b45309"))
    c.setLineWidth(1.5)
    c.circle(cx, cy, radius - 8, fill=1, stroke=1)

    # Seal center text
    c.setFillColor(colors.HexColor("#92400e"))
    c.setFont("Helvetica-Bold", 7.5)
    c.drawCentredString(cx, cy + 8, "OFFICIAL")
    c.drawCentredString(cx, cy - 2, "SEAL OF")
    c.drawCentredString(cx, cy - 12, "EXCELLENCE")

    c.restoreState()


def generate_certificate_pdf(
    certificate_code: str,
    recipient_name: str,
    title: str,
    issuer_name: str,
    issue_date: str,
    description: Optional[str] = None,
    custom_attributes: Optional[Dict[str, Any]] = None,
    output_dir: Optional[Path] = None
) -> str:
    """
    Renders a high-resolution, vector PDF certificate for a recipient.
    Returns the absolute path to the generated PDF.
    """
    # Fault injection hook for automated testing:
    # If custom_attributes contains "_fail_generate": True, simulate generator error
    if custom_attributes and custom_attributes.get("_fail_generate") is True:
        raise RuntimeError("Simulated certificate rendering failure for testing.")

    dest_dir = output_dir or STORAGE_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{certificate_code}.pdf"
    file_path = dest_dir / filename

    # Standard landscape A4: width ~841.89, height ~595.27
    page_width, page_height = landscape(A4)
    c = canvas.Canvas(str(file_path), pagesize=(page_width, page_height))
    c.setTitle(f"Certificate - {recipient_name}")
    c.setAuthor(issuer_name)
    c.setSubject(title)

    # 1. Warm parchment / ivory background
    c.setFillColor(colors.HexColor("#fcfbf9"))
    c.rect(0, 0, page_width, page_height, fill=1, stroke=0)

    # 2. Dual borders
    # Outer dark navy border
    c.setStrokeColor(colors.HexColor("#0f172a"))
    c.setLineWidth(6)
    margin = 25
    c.rect(margin, margin, page_width - (2 * margin), page_height - (2 * margin), stroke=1, fill=0)

    # Inner gold border
    c.setStrokeColor(colors.HexColor("#d97706"))
    c.setLineWidth(2)
    inner_margin = 35
    c.rect(inner_margin, inner_margin, page_width - (2 * inner_margin), page_height - (2 * inner_margin), stroke=1, fill=0)

    # Inner faint hairline border
    c.setStrokeColor(colors.HexColor("#cbd5e1"))
    c.setLineWidth(0.75)
    c.rect(inner_margin + 5, inner_margin + 5, page_width - (2 * (inner_margin + 5)), page_height - (2 * (inner_margin + 5)), stroke=1, fill=0)

    # 3. Corner Ornaments
    draw_geometric_corner(c, inner_margin + 5, page_height - (inner_margin + 5))
    draw_geometric_corner(c, page_width - (inner_margin + 5), page_height - (inner_margin + 5))
    draw_geometric_corner(c, inner_margin + 5, inner_margin + 5)
    draw_geometric_corner(c, page_width - (inner_margin + 5), inner_margin + 5)

    center_x = page_width / 2

    # 4. Top Header
    c.setFillColor(colors.HexColor("#d97706"))
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(center_x, page_height - 95, "★ ★ ★   CERTIFICATE OF ACHIEVEMENT   ★ ★ ★")

    c.setFillColor(colors.HexColor("#475569"))
    c.setFont("Helvetica", 13)
    c.drawCentredString(center_x, page_height - 135, "THIS IS PROUDLY PRESENTED TO")

    # 5. Recipient Name (with dynamic font scaling for long names)
    c.setFillColor(colors.HexColor("#0f172a"))
    name_font_size = 34
    if len(recipient_name) > 26:
        name_font_size = max(18, int(34 * 26 / len(recipient_name)))
    c.setFont("Helvetica-Bold", name_font_size)
    c.drawCentredString(center_x, page_height - 185, recipient_name)

    # Gold decorative separator line under name
    c.setStrokeColor(colors.HexColor("#d97706"))
    c.setLineWidth(1.5)
    line_half_width = min(220, max(140, len(recipient_name) * 5))
    c.line(center_x - line_half_width, page_height - 198, center_x + line_half_width, page_height - 198)

    # Small diamond on line
    c.setFillColor(colors.HexColor("#b45309"))
    c.circle(center_x, page_height - 198, 3.5, stroke=0, fill=1)

    # 6. Presentation purpose & Title
    c.setFillColor(colors.HexColor("#475569"))
    c.setFont("Helvetica", 13)
    c.drawCentredString(center_x, page_height - 235, "in recognition of successful completion and dedication in")

    c.setFillColor(colors.HexColor("#1e293b"))
    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(center_x, page_height - 275, title)

    # 7. Description text
    body_text = description or "For demonstrated excellence and successful completion of all program requirements."
    c.setFillColor(colors.HexColor("#64748b"))
    c.setFont("Helvetica-Oblique", 11)
    
    # Split text if long
    if len(body_text) > 90:
        part1 = body_text[:90].rsplit(" ", 1)[0]
        part2 = body_text[len(part1):].strip()
        c.drawCentredString(center_x, page_height - 310, part1)
        c.drawCentredString(center_x, page_height - 325, part2)
        attr_y = page_height - 355
    else:
        c.drawCentredString(center_x, page_height - 315, body_text)
        attr_y = page_height - 345

    # 8. Custom Attributes Badge / Pill (if provided)
    clean_custom = {k: v for k, v in (custom_attributes or {}).items() if not k.startswith("_")}
    if clean_custom:
        attrs_formatted = "  •  ".join(f"{k.replace('_', ' ').title()}: {v}" for k, v in clean_custom.items())
        c.setFillColor(colors.HexColor("#0284c7"))
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(center_x, attr_y, attrs_formatted)

    # 9. Center Seal
    seal_y = 120
    draw_certificate_seal(c, center_x, seal_y, radius=36)

    # 10. Left Signature / Date Section
    left_x = 140
    c.setStrokeColor(colors.HexColor("#94a3b8"))
    c.setLineWidth(1)
    c.line(left_x - 60, 105, left_x + 60, 105)

    c.setFillColor(colors.HexColor("#0f172a"))
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(left_x, 88, issue_date)

    c.setFillColor(colors.HexColor("#64748b"))
    c.setFont("Helvetica", 9)
    c.drawCentredString(left_x, 72, "DATE OF ISSUANCE")

    # 11. Right Signature Section
    right_x = page_width - 140
    c.setStrokeColor(colors.HexColor("#94a3b8"))
    c.setLineWidth(1)
    c.line(right_x - 70, 105, right_x + 70, 105)

    c.setFillColor(colors.HexColor("#0f172a"))
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(right_x, 88, issuer_name)

    c.setFillColor(colors.HexColor("#64748b"))
    c.setFont("Helvetica", 9)
    c.drawCentredString(right_x, 72, "AUTHORIZED SIGNATORY")

    # 12. Bottom Security & Verification Bar
    c.setFillColor(colors.HexColor("#94a3b8"))
    c.setFont("Helvetica", 8)
    verify_text = f"Certificate Code: {certificate_code}  |  Official Record  |  Verified & Secured"
    c.drawCentredString(center_x, 44, verify_text)

    c.save()
    return str(file_path)
