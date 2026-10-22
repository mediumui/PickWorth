#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
inline_assets.py — make every page work under BOTH file:// and http://.

1. Inlines the icon sprite (assets/img/icons.svg) into each page as a
   hidden <svg><defs>…</defs></svg> block right after <body>, then rewrites
   <use href="/assets/img/icons.svg#i-x"> to local "#i-x" references.
   (file:// blocks external SVG <use>, so inlining is the only reliable way.)
2. Rewrites absolute asset paths (/assets/...) to depth-correct relative ones.
3. Rewrites internal page links (/tools/, /about/, "/" ...) to relative
   "dir/index.html" forms so double-clicking a page in Explorer works.

Run from the site root:  python tools/inline_assets.py
Idempotent: safe to re-run after editing pages.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ICONS = ROOT / "assets" / "img" / "icons.svg"

def load_symbols() -> str:
    src = ICONS.read_text(encoding="utf-8")
    syms = re.findall(r"<symbol\b.*?</symbol>", src, re.S)
    if not syms:
        sys.exit("no <symbol> found in icons.svg")
    return "".join(syms)

SPRITE = ('<svg xmlns="http://www.w3.org/2000/svg" '
          'style="display:none" aria-hidden="true">{symbols}</svg>')

def depth_of(p: Path) -> int:
    return len(p.relative_to(ROOT).parts) - 1  # 0 for root, 1 for one dir down

def process(page: Path, symbols: str) -> None:
    html = page.read_text(encoding="utf-8")
    orig = html
    d = depth_of(page)
    prefix = "../" * d

    # 1) ensure inline sprite exists just after <body>
    if 'style="display:none" aria-hidden="true">' not in html:
        sprite = SPRITE.format(symbols=symbols)
        html = re.sub(r"(<body[^>]*>)", r"\1\n" + sprite, html, count=1)

    # 2) local <use> refs
    html = re.sub(
        r'(?:href|xlink:href)="/assets/img/icons\.svg#(i-[a-z]+)"',
        r'href="#\1"', html)

    # 3) relative asset paths
    html = html.replace('href="/assets/', f'href="{prefix}assets/')
    html = html.replace('src="/assets/',  f'src="{prefix}assets/')

    # 4) internal links -> relative with index.html
    html = html.replace('href="/"', f'href="{prefix}index.html"')
    for sec in ("tools", "comparisons", "about", "contact", "lists", "blog"):
        html = html.replace(f'href="/{sec}/"', f'href="{prefix}{sec}/index.html"')
        # deep links like /tools/chatgpt/
        html = re.sub(rf'href="/{sec}/([a-z0-9-]+)/?"',
                      rf'href="{prefix}{sec}/\1/index.html"', html)

    if html != orig:
        page.write_text(html, encoding="utf-8")
        print(f"  updated {page.relative_to(ROOT)}")
    else:
        print(f"  ok      {page.relative_to(ROOT)}")

def main() -> None:
    symbols = load_symbols()
    # Both root-level landing pages (index.html) and the 404 page need the
    # same treatment, so match either rather than only "index.html".
    pages = [p for p in ROOT.rglob("*.html")
             if p.name in ("index.html", "404.html")
             and ".workbuddy" not in p.parts and "content" not in p.parts
             and "src" not in p.parts]
    print(f"processing {len(pages)} pages under {ROOT}")
    for p in sorted(pages):
        process(p, symbols)
    print("done.")

if __name__ == "__main__":
    main()
