#!/usr/bin/env python3
"""Luggage Tag Generator for ESC/POS Thermal Printers.

Generates fold-over adhesive luggage tags designed to wrap around a
luggage handle.  The output is a single PNG image with two faces:

    [  BACK face, printed upside-down  ]
    [ - - - - FOLD HERE - - - - - - -  ]
    [  FRONT face, printed normally     ]

When the adhesive strip is draped over a handle and pressed together,
both faces read right-side-up from their respective sides.

Usage (standalone):
    python3 generate_tag.py \
        --name "John Smith" \
        --destination LAX \
        --origin JFK \
        --flight "UA 1234" \
        --date "28 FEB 2026" \
        --phone "+1 (555) 123-4567" \
        --email "john@example.com" \
        --design classic \
        --output /config/www/luggage_tag.png

Called from Home Assistant via shell_command (see scripts.yaml).

Three designs are provided:
    classic  - Resembles an airline baggage tag
    bold     - Huge text for maximum distance visibility
    contact  - Clean layout emphasising a QR vCard
"""

import argparse
import os
import sys

from PIL import Image, ImageDraw, ImageFont

try:
    import qrcode

    HAS_QRCODE = True
except ImportError:
    HAS_QRCODE = False

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
PAPER_WIDTH_80MM = 576  # 80 mm paper @ 203 DPI
PAPER_WIDTH_58MM = 384  # 58 mm paper @ 203 DPI

FACE_HEIGHT = 480  # height of each tag face (px)
FOLD_HEIGHT = 220  # handle gap between faces (px)
MARGIN = 16
BORDER = 4

# ---------------------------------------------------------------------------
# Font helpers
# ---------------------------------------------------------------------------
_FONT_SEARCH = [
    # Debian / Ubuntu
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    # Alpine (Home Assistant OS)
    "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/ttf-dejavu/DejaVuSans-Bold.ttf",
    # Fedora / RHEL
    "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-Bold.ttf",
    # Arch
    "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    # macOS
    "/System/Library/Fonts/Helvetica.ttc",
]

_font_path_cache: str | None = None
_font_cache: dict[tuple[int], ImageFont.FreeTypeFont] = {}


def _find_font_path() -> str | None:
    global _font_path_cache
    if _font_path_cache is not None:
        return _font_path_cache or None
    for p in _FONT_SEARCH:
        if os.path.isfile(p):
            _font_path_cache = p
            return p
    _font_path_cache = ""
    return None


def get_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Return a font at *size* pixels, with graceful fallback."""
    if size in _font_cache:
        return _font_cache[size]
    path = _find_font_path()
    font = None
    if path:
        try:
            font = ImageFont.truetype(path, size)
        except Exception:
            pass
    if font is None:
        try:
            font = ImageFont.load_default(size=size)  # Pillow >= 10.1
        except TypeError:
            font = ImageFont.load_default()
    _font_cache[size] = font
    return font


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------
def _text_size(draw: ImageDraw.ImageDraw, text: str, font) -> tuple[int, int]:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def center_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font,
    y: int,
    canvas_width: int,
    fill="black",
) -> int:
    """Draw *text* horizontally centred at vertical position *y*.

    Returns the rendered text height so callers can advance *y*.
    """
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = (canvas_width - tw) // 2 - bbox[0]
    draw.text((x, y - bbox[1]), text, font=font, fill=fill)
    return th


def right_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font,
    y: int,
    canvas_width: int,
    fill="black",
) -> int:
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = canvas_width - MARGIN - tw - bbox[0]
    draw.text((x, y - bbox[1]), text, font=font, fill=fill)
    return th


def draw_dashed_line(
    draw: ImageDraw.ImageDraw,
    x1: int,
    y: int,
    x2: int,
    dash: int = 10,
    gap: int = 6,
    fill="black",
    width: int = 1,
):
    x = x1
    while x < x2:
        end = min(x + dash, x2)
        draw.line([(x, y), (end, y)], fill=fill, width=width)
        x = end + gap


def draw_double_border(draw: ImageDraw.ImageDraw, w: int, h: int, thickness: int = 3):
    """Draw a double-rule border around the full image."""
    draw.rectangle([(0, 0), (w - 1, h - 1)], outline="black", width=thickness)
    gap = thickness + 2
    draw.rectangle([(gap, gap), (w - 1 - gap, h - 1 - gap)], outline="black", width=1)


# ---------------------------------------------------------------------------
# QR / vCard
# ---------------------------------------------------------------------------
def make_vcard(name: str, phone: str = "", email: str = "") -> str:
    lines = ["BEGIN:VCARD", "VERSION:3.0", f"FN:{name}"]
    if phone:
        lines.append(f"TEL;TYPE=CELL:{phone}")
    if email:
        lines.append(f"EMAIL:{email}")
    lines.append("END:VCARD")
    return "\n".join(lines)


def generate_qr(data: str, size: int = 160) -> Image.Image | None:
    if not HAS_QRCODE or not data.strip():
        return None
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=4,
        border=2,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    return img.resize((size, size), Image.NEAREST)


# ===================================================================
# DESIGN 1 — Classic Airline
# ===================================================================
# Styled after a real airline baggage check tag:
# double-rule border, large IATA code, route line, flight details,
# and a QR vCard on the front.
# ===================================================================


def _classic_face(data: dict, w: int, *, back: bool = False) -> Image.Image:
    h = FACE_HEIGHT
    img = Image.new("RGB", (w, h), "white")
    draw = ImageDraw.Draw(img)

    draw_double_border(draw, w, h, thickness=3)

    f_huge = get_font(76)
    f_large = get_font(32)
    f_med = get_font(20)
    f_small = get_font(16)

    y = 22

    # --- Destination code ---
    dest = data.get("destination", "???").upper()[:6]
    y += center_text(draw, dest, f_huge, y, w) + 6

    # --- Route ---
    origin = data.get("origin", "").upper()[:6]
    if origin:
        y += center_text(draw, f"{origin}  -->  {dest}", f_med, y, w) + 4

    # --- Divider ---
    draw.line([(MARGIN + 6, y), (w - MARGIN - 6, y)], fill="black", width=2)
    y += 12

    # --- Passenger name ---
    name = data.get("name", "PASSENGER").upper()
    y += center_text(draw, name, f_large, y, w) + 8

    if back:
        # Back: phone + "if found" message
        phone = data.get("phone", "")
        if phone:
            y += center_text(draw, phone, f_med, y, w) + 16
        y += 12
        center_text(draw, "IF FOUND PLEASE CONTACT", f_small, y, w)
        y += 22
        center_text(draw, "OWNER AT NUMBER ABOVE", f_small, y, w)
    else:
        # Front: flight info, contact, QR
        flight = data.get("flight", "")
        date = data.get("date", "")
        parts = [p.upper() for p in (flight, date) if p]
        if parts:
            y += center_text(draw, "  |  ".join(parts), f_med, y, w) + 6

        phone = data.get("phone", "")
        if phone:
            y += center_text(draw, phone, f_small, y, w) + 4
        email = data.get("email", "")
        if email:
            y += center_text(draw, email, f_small, y, w) + 4

        # QR vCard
        vcard = make_vcard(data.get("name", ""), phone, email)
        qr = generate_qr(vcard, size=150)
        if qr:
            qx = (w - 150) // 2
            qy = h - 170
            img.paste(qr, (qx, qy))

    return img


def design_classic(data: dict, w: int) -> tuple[Image.Image, Image.Image]:
    """Return (front, back) faces for the Classic Airline design."""
    return _classic_face(data, w, back=False), _classic_face(data, w, back=True)


# ===================================================================
# DESIGN 2 — Bold & Visible
# ===================================================================
# Maximises readability from a distance.  Thick borders, inverted
# header/footer bars, and huge destination code.  No QR code — pure
# high-contrast text.
# ===================================================================


def _bold_face(data: dict, w: int, *, back: bool = False) -> Image.Image:
    h = FACE_HEIGHT
    img = Image.new("RGB", (w, h), "white")
    draw = ImageDraw.Draw(img)

    # Outer border
    draw.rectangle([(0, 0), (w - 1, h - 1)], outline="black", width=5)

    f_banner = get_font(18)
    f_huge = get_font(100)
    f_large = get_font(36)
    f_med = get_font(26)

    # --- Black header bar ---
    bar_h = 44
    draw.rectangle([(5, 5), (w - 6, 5 + bar_h)], fill="black")
    center_text(draw, "LUGGAGE TAG", f_banner, 16, w, fill="white")

    y = bar_h + 24

    # --- Destination code (huge) ---
    dest = data.get("destination", "???").upper()[:6]
    y += center_text(draw, dest, f_huge, y, w) + 10

    # --- Passenger name ---
    name = data.get("name", "PASSENGER").upper()
    y += center_text(draw, name, f_large, y, w) + 8

    if back:
        phone = data.get("phone", "")
        if phone:
            center_text(draw, phone, f_med, y, w)
    else:
        flight = data.get("flight", "")
        date = data.get("date", "")
        parts = [p.upper() for p in (flight, date) if p]
        if parts:
            y += center_text(draw, "  |  ".join(parts), f_med, y, w) + 6

        phone = data.get("phone", "")
        if phone:
            center_text(draw, phone, f_med, y, w)

    # --- Black footer bar ---
    draw.rectangle([(5, h - 5 - bar_h), (w - 6, h - 6)], fill="black")

    return img


def design_bold(data: dict, w: int) -> tuple[Image.Image, Image.Image]:
    """Return (front, back) faces for the Bold & Visible design."""
    return _bold_face(data, w, back=False), _bold_face(data, w, back=True)


# ===================================================================
# DESIGN 3 — Contact Card
# ===================================================================
# Clean, structured layout with labelled fields and a large QR vCard.
# Optimised for the "lost bag" scenario — a finder can scan the QR
# to get the owner's contact details instantly.
# ===================================================================


def _contact_face(data: dict, w: int, *, back: bool = False) -> Image.Image:
    h = FACE_HEIGHT
    img = Image.new("RGB", (w, h), "white")
    draw = ImageDraw.Draw(img)

    draw.rectangle([(0, 0), (w - 1, h - 1)], outline="black", width=2)

    f_label = get_font(14)
    f_value = get_font(22)
    f_name_val = get_font(28)
    f_small = get_font(13)

    label_x = MARGIN + 8
    value_x = MARGIN + 82
    y = 18

    def field(label: str, value: str, font_v=f_value):
        nonlocal y
        if not value:
            return
        draw.text((label_x, y + 4), label, font=f_label, fill="gray")
        draw.text((value_x, y), value.upper(), font=font_v, fill="black")
        bbox = draw.textbbox((0, 0), value.upper(), font=font_v)
        y += (bbox[3] - bbox[1]) + 10

    # --- Travel info ---
    field("DEST", data.get("destination", ""))
    if data.get("origin"):
        field("FROM", data["origin"])
    field("FLIGHT", data.get("flight", ""))
    field("DATE", data.get("date", ""))

    # --- Divider ---
    y += 2
    draw.line([(MARGIN + 4, y), (w - MARGIN - 4, y)], fill="black", width=1)
    y += 10

    # --- Contact info ---
    field("NAME", data.get("name", ""), font_v=f_name_val)
    field("PHONE", data.get("phone", ""))

    if not back:
        field("EMAIL", data.get("email", ""))

    # --- Divider ---
    y += 2
    draw.line([(MARGIN + 4, y), (w - MARGIN - 4, y)], fill="black", width=1)
    y += 8

    if back:
        y += 8
        center_text(draw, "IF FOUND PLEASE CONTACT", f_label, y, w, fill="gray")
        y += 20
        center_text(draw, "OWNER USING DETAILS ABOVE", f_label, y, w, fill="gray")
    else:
        # QR vCard
        vcard = make_vcard(
            data.get("name", ""), data.get("phone", ""), data.get("email", "")
        )
        qr = generate_qr(vcard, size=160)
        if qr:
            qx = (w - 160) // 2
            img.paste(qr, (qx, y))
            y += 166
            center_text(draw, "SCAN FOR CONTACT INFO", f_small, y, w, fill="gray")

    return img


def design_contact(data: dict, w: int) -> tuple[Image.Image, Image.Image]:
    """Return (front, back) faces for the Contact Card design."""
    return _contact_face(data, w, back=False), _contact_face(data, w, back=True)


# ===================================================================
# Fold-over assembly
# ===================================================================

DESIGNS = {
    "classic": design_classic,
    "bold": design_bold,
    "contact": design_contact,
}


def assemble_foldover(
    front: Image.Image,
    back: Image.Image,
    paper_width: int,
) -> Image.Image:
    """Combine front + back into a single fold-over strip.

    Physical layout once printed and folded over a handle:

        Handle
       /      \\
      Back    Front
     (top)   (bottom)

    The back face is printed 180-deg rotated so that both sides read
    right-side-up when the tag hangs from the handle.
    """
    total_h = back.size[1] + FOLD_HEIGHT + front.size[1]
    tag = Image.new("RGB", (paper_width, total_h), "white")
    draw = ImageDraw.Draw(tag)

    # Back face rotated 180 deg at the top of the strip
    back_rotated = back.rotate(180)
    tag.paste(back_rotated, (0, 0))

    # Fold area
    fold_top = back.size[1]
    fold_mid = fold_top + FOLD_HEIGHT // 2

    f_fold = get_font(13)
    draw_dashed_line(draw, MARGIN, fold_mid - 1, paper_width - MARGIN, dash=8, gap=5)
    center_text(draw, "FOLD OVER HANDLE", f_fold, fold_mid - 22, paper_width, fill="gray")
    center_text(draw, "v               v", f_fold, fold_mid + 6, paper_width, fill="gray")

    # Front face normal at the bottom
    tag.paste(front, (0, fold_top + FOLD_HEIGHT))

    return tag


# ===================================================================
# CLI
# ===================================================================


def main():
    parser = argparse.ArgumentParser(
        description="Generate a fold-over luggage tag for an ESC/POS thermal printer.",
    )
    parser.add_argument("--name", required=True, help="Passenger full name")
    parser.add_argument("--destination", required=True, help="Destination (e.g. LAX)")
    parser.add_argument("--origin", default="", help="Origin (e.g. JFK)")
    parser.add_argument("--flight", default="", help="Flight number (e.g. UA 1234)")
    parser.add_argument("--date", default="", help="Travel date (e.g. 28 FEB 2026)")
    parser.add_argument("--phone", default="", help="Contact phone number")
    parser.add_argument("--email", default="", help="Contact email address")
    parser.add_argument(
        "--design",
        default="classic",
        choices=list(DESIGNS.keys()),
        help="Tag design style (default: classic)",
    )
    parser.add_argument(
        "--output",
        default="luggage_tag.png",
        help="Output PNG path (default: luggage_tag.png)",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=PAPER_WIDTH_80MM,
        help=f"Paper width in pixels (default: {PAPER_WIDTH_80MM} for 80 mm)",
    )
    args = parser.parse_args()

    data = {
        "name": args.name,
        "destination": args.destination,
        "origin": args.origin,
        "flight": args.flight,
        "date": args.date,
        "phone": args.phone,
        "email": args.email,
    }

    design_fn = DESIGNS[args.design]
    front, back = design_fn(data, args.width)
    tag = assemble_foldover(front, back, args.width)

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    tag.save(args.output)
    print(f"Luggage tag saved to {args.output}")


if __name__ == "__main__":
    main()
