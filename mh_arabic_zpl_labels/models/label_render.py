"""Draw label text with Pillow so Arabic is joined and right-to-left, then turn it into ZPL ^GFA graphics.

Zebra printers do not shape Arabic: text sent with ^FD comes out empty or as separated, reversed letters.
Sending the text as a graphic makes every printer print it exactly as it looks on screen.
"""
import re

from PIL import Image, ImageDraw, ImageFont, features

ARABIC_RE = re.compile(r"[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]")
HAS_RAQM = features.check("raqm")
THRESHOLD = 150


class ShapingUnavailable(Exception):
    pass


def has_arabic(text):
    return bool(ARABIC_RE.search(text or ""))


def _prepare(text):
    """Return (text to draw, Pillow layout kwargs)."""
    if not has_arabic(text):
        return text, {}
    if HAS_RAQM:
        # libraqm joins the letters and orders mixed Arabic / Latin / digits itself.
        return text, {"direction": "rtl", "language": "ar"}
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
    except ImportError:
        raise ShapingUnavailable() from None
    return get_display(arabic_reshaper.reshape(text)), {}


def _font(font_path, size):
    return ImageFont.truetype(font_path, size)


def text_width(text, font_path, size):
    drawn, kw = _prepare(text)
    return _font(font_path, size).getlength(drawn, **kw)


def wrap(text, font_path, size, max_width, max_lines):
    """Split text into at most max_lines lines that fit max_width; shrink the font if needed.

    Returns (lines, size).
    """
    text = " ".join((text or "").split())
    while True:
        lines, current = [], ""
        for word in text.split(" "):
            candidate = (current + " " + word).strip()
            if not current or text_width(candidate, font_path, size) <= max_width:
                current = candidate
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)
        fits = len(lines) <= max_lines and all(text_width(l, font_path, size) <= max_width for l in lines)
        if fits or size <= 10:
            return lines[:max_lines], size
        size -= 1


def draw_text(text, font_path, size):
    """Black-on-white 1-bit image of one line of text, cropped to the ink."""
    drawn, kw = _prepare(text)
    font = _font(font_path, size)
    left, top, right, bottom = font.getbbox(drawn, **kw)
    w, h = max(1, right - left), max(1, bottom - top)
    img = Image.new("L", (w + 2, h + 2), 255)
    ImageDraw.Draw(img).text((1 - left, 1 - top), drawn, font=font, fill=0, **kw)
    return img.point(lambda p: 0 if p < THRESHOLD else 255, "1")


def image_to_gfa(img):
    """ZPL ^GFA command (ASCII hex) for a 1-bit image; black pixels print."""
    img = img.convert("1")
    w, h = img.size
    row_bytes = (w + 7) // 8
    px = img.load()
    data = bytearray()
    for y in range(h):
        for xb in range(row_bytes):
            byte = 0
            for bit in range(8):
                x = xb * 8 + bit
                if x < w and not px[x, y]:
                    byte |= 0x80 >> bit
            data.append(byte)
    total = len(data)
    return "^GFA,%d,%d,%d,%s" % (total, total, row_bytes, data.hex().upper())


def is_ean13(value):
    return bool(re.fullmatch(r"\d{13}", value or "")) and _ean_ok(value)


def barcode_zpl(value, module_width, height):
    """Native ZPL barcode: EAN-13 when the value is a valid EAN-13, Code 128 (automatic mode) otherwise."""
    if is_ean13(value):
        return "^BY%d^BEN,%d,Y,N^FD%s^FS" % (module_width, height, value[:12])
    clean = value.replace("^", "").replace("~", "")
    return "^BY%d^BCN,%d,Y,N,N,A^FD%s^FS" % (module_width, height, clean)


def barcode_modules(value):
    """Width of the barcode in modules (narrow bars), to center it and to fit it on the label."""
    if is_ean13(value):
        return 95
    if value.isdigit() and len(value) >= 4:
        # Code 128 automatic mode packs two digits per symbol (subset C); an odd digit costs a switch + 1 symbol.
        pairs, odd = divmod(len(value), 2)
        return 11 * (pairs + 2 * odd) + 35
    return 11 * len(value) + 35


def _ean_ok(value):
    digits = [int(c) for c in value]
    check = (10 - (sum(digits[-2::-2]) * 3 + sum(digits[-3::-2])) % 10) % 10
    return check == digits[-1]


def mm_to_dots(mm, dpi):
    return int(round(mm / 25.4 * dpi))
