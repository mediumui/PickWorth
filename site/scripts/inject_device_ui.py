#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""inject_device_ui.py — one-shot, idempotent injection of the two-UI seam.

Adds to every index.html / 404.html (excluding content/, src/, .workbuddy/):
  1. <link rel="canonical"> self-reference (stable URL across both UIs)
  2. <script src=".../assets/js/device-ui.js"> in <head> (pre-paint class set)
  3. <nav class="mtab"> bottom tab bar after </footer> (mobile-only; hidden
     on desktop by CSS; carries NO body content — nav only)

Why: SEO/GEO-safe "same route, two independent UIs". The JS only toggles
body classes; it never edits text nodes, so desktop and mobile crawlers
both read the identical full article body.
Run from site root:  python tools/inject_device_ui.py
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = "https://www.pickworth.top"

def depth_of(p: Path) -> int:
    return len(p.relative_to(ROOT).parts) - 1  # 0 for root

def canonical_for(p: Path) -> str:
    if p.name == "404.html":
        return f"{BASE}/404.html"
    rel = p.with_suffix("").relative_to(ROOT)  # .../tools/claude/index -> .../tools/claude
    parts = list(rel.parts)[:-1]              # drop index.html
    if not parts:
        return f"{BASE}/"
    return f"{BASE}/{'/'.join(parts)}/"

TAB_TPL = """
<nav class="mtab" aria-label="Primary">
  <a href="{r}index.html"><svg viewBox="0 0 32 32" aria-hidden="true"><use href="#i-logo"></use></svg><span>Home</span></a>
  <a href="{r}tools/index.html"><svg viewBox="0 0 24 24" aria-hidden="true"><use href="#i-sources"></use></svg><span>Tools</span></a>
  <a href="{r}comparisons/index.html"><svg viewBox="0 0 24 24" aria-hidden="true"><use href="#i-compare"></use></svg><span>Compare</span></a>
  <a href="{r}lists/index.html"><svg viewBox="0 0 24 24" aria-hidden="true"><use href="#i-pick"></use></svg><span>Lists</span></a>
  <a href="{r}about/index.html"><svg viewBox="0 0 24 24" aria-hidden="true"><use href="#i-cite"></use></svg><span>About</span></a>
</nav>
"""

def process(page: Path) -> None:
    html = page.read_text(encoding="utf-8")
    orig = html
    d = depth_of(page)
    prefix = "../" * d
    canon = canonical_for(page)

    # 1) canonical (self-referencing; stable across both device UIs)
    if f'rel="canonical"' not in html:
        link = f'<link rel="canonical" href="{canon}" />'
        html = html.replace('<link rel="stylesheet"', link + "\n<link rel=\"stylesheet\"", 1)

    # 2) device-ui.js just before </head> (pre-paint class set)
    if "device-ui.js" not in html:
        script = f'<script src="{prefix}assets/js/device-ui.js"></script>\n</head>'
        html = html.replace("</head>", script, 1)

    # 3) bottom tab bar after the site footer (nav only, no body content)
    if 'class="mtab"' not in html:
        tab = TAB_TPL.format(r=prefix)
        html = html.replace("</footer>", "</footer>\n" + tab, 1)

    if html != orig:
        page.write_text(html, encoding="utf-8")
        print(f"  updated {page.relative_to(ROOT)}")
    else:
        print(f"  ok      {page.relative_to(ROOT)}")

def main() -> None:
    pages = [p for p in ROOT.rglob("*.html")
             if p.name in ("index.html", "404.html")
             and ".workbuddy" not in p.parts
             and "content" not in p.parts
             and "src" not in p.parts]
    print(f"processing {len(pages)} pages under {ROOT}")
    for p in sorted(pages):
        process(p)
    print("done.")

if __name__ == "__main__":
    main()
