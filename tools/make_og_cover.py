#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_og_cover.py — generate the Open Graph share image (1200x630).

Uses the same brand mark and palette as assets/img/favicon.svg so the
browser tab icon, the header logo and the social share card read as one
identity. Re-run whenever the brand mark or tagline changes.

Run from the site root:  python tools/make_og_cover.py
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "img" / "og-cover.png"

PAPER = (250, 248, 243)      # --paper   #faf8f3
INK = (28, 26, 23)           # --ink     #1c1a17
INK2 = (67, 63, 58)          # --ink-2   #433f3a
ACCENT = (184, 80, 58)       # --accent  #b8503a
RULE = (214, 205, 191)       # hairline rule

W, H = 1200, 630
MARGIN = 96


def font(name, size, bold=False):
    """Try a serif stack; fall back to the built-in bitmap font."""
    cands = [
        f"C:/Windows/Fonts/{name}{'bd' if bold else ''}.ttf",
        f"C:/Windows/Fonts/{name}.ttf",
    ]
    for p in cands:
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size)
            except OSError:
                pass
    return ImageFont.load_default()


def draw_mark(d: ImageDraw.ImageDraw, x: int, y: int, size: int) -> None:
    """The PickWorth mark — identical geometry to favicon.svg, solid variant."""
    d.rounded_rectangle([x, y, x + size, y + size], radius=size * 0.22, fill=ACCENT)
    s = size
    tri = [
        (x + s * 8 / 32, y + s * 23.5 / 32),
        (x + s * 16 / 32, y + s * 9 / 32),
        (x + s * 24 / 32, y + s * 23.5 / 32),
    ]
    w = max(3, int(s * 2.4 / 32))
    d.line(tri + [tri[0]], fill=PAPER, width=w, joint="curve")
    r = s * 1.8 / 32
    cx, cy = x + s * 16 / 32, y + s * 19.4 / 32
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=PAPER)


def main() -> None:
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)

    # --- brand row ---
    draw_mark(d, MARGIN, 64, 68)
    d.text((MARGIN + 68 + 20, 72), "PickWorth",
           font=font("georgia", 42, bold=True), fill=INK)

    d.line([MARGIN, 172, W - MARGIN, 172], fill=RULE, width=2)

    # --- headline (two lines, kept inside the safe width) ---
    f_h1 = font("georgia", 62, bold=True)
    d.text((MARGIN, 214), "Honest AI tool reviews", font=f_h1, fill=INK)
    d.text((MARGIN, 296), "& clear comparisons", font=f_h1, fill=INK)

    # --- one-line subtitle ---
    d.text((MARGIN, 402),
           "What each tool is genuinely good at — and what it really costs.",
           font=font("georgia", 30), fill=INK2)

    # --- footer ---
    d.text((MARGIN, 500), "pickworthhq.com",
           font=font("georgia", 26), fill=INK2)
    d.rectangle([MARGIN, H - 74, MARGIN + 120, H - 68], fill=ACCENT)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT, "PNG", optimize=True)
    print(f"wrote {OUT.relative_to(ROOT)}  ({W}x{H})")


if __name__ == "__main__":
    main()
