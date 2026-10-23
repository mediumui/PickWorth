#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify_refs.py - check every relative href/src in every page resolves to a real file."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
pages = [p for p in ROOT.rglob("*.html")
         if p.name in ("index.html", "404.html")
         and "content" not in p.parts and "src" not in p.parts
         and ".workbuddy" not in p.parts]
bad = 0
for p in sorted(pages):
    html = p.read_text(encoding="utf-8")
    refs = re.findall(r'(?:href|src)="([^"#]+?)(?:#[^"]*)?"', html)
    for r in refs:
        if r.startswith("mailto:") or r.startswith("http"):
            continue
        # site-root absolute refs ("/assets/...") resolve against the site root,
        # not the page's parent dir; CF Pages serves assets.directory (./) as
        # the web root, so "/x" -> ROOT/"x".
        base = ROOT if r.startswith("/") else p.parent
        target = (base / r.lstrip("/")).resolve()
        if not target.exists():
            print("MISSING:", p.relative_to(ROOT), "->", r)
            bad += 1
print(f"checked {len(pages)} pages;", "ALL REFS OK" if bad == 0 else f"{bad} broken refs")
sys.exit(1 if bad else 0)
