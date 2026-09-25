"""Helpers for the MACEXTRA tests: pictures and PDFs with text, the QR window."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def text_image(path, lines, size=64, width=1400):
    """Black text on white, one line under the other, large enough to read."""
    font = ImageFont.load_default(size=size)
    height = 60 + len(lines) * int(size * 1.8)
    img = Image.new("RGB", (width, height), "white")
    d = ImageDraw.Draw(img)
    for i, line in enumerate(lines):
        d.text((40, 30 + i * int(size * 1.8)), line, fill="black", font=font)
    img.save(path)
    return Path(path)


def blank_image(path, width=600, height=300):
    Image.new("RGB", (width, height), "white").save(path)
    return Path(path)


def text_pdf(path, pages, size=72):
    """A raster PDF, one page per text."""
    images = []
    font = ImageFont.load_default(size=size)
    for text in pages:
        img = Image.new("RGB", (1700, 2200), "white")
        ImageDraw.Draw(img).text((120, 300), text, fill="black", font=font)
        images.append(img)
    images[0].save(path, save_all=True, append_images=images[1:], resolution=200.0)
    return Path(path)


def qr_window(app):
    for w in app.windows():
        if w["visible"] and w["title"] == "QR Code":
            return w
    return None


def close_qr(app):
    w = qr_window(app)
    if w:
        app.close_window(w["number"])


def caption(app, w):
    for c in app.ui(w["number"])["controls"]:
        if c.get("class") == "NSTextField" and c.get("path") == "0.1.0.1":
            return c.get("value")
    return None


def image_control(app, w):
    for c in app.ui(w["number"])["controls"]:
        if c.get("class") == "NSImageView":
            return c
    return None


def alerts(log):
    return [e for e in log if e.get("kind") == "alert"]
