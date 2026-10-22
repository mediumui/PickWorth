#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sync_analytics.py — push the Google Analytics snippet into every page on the site.

The GA code lives in a single source of truth:

    src/components/_analytics.html   (gtag.js, measurement ID G-WV775YD52J)

This script makes that file the source of truth for the analytics block on
ALL pages:

    edit src/components/_analytics.html
    python tools/sync_analytics.py          # every page updated in place

HOW IT WORKS
------------
The script reads the block between the two marker comments in
_analytics.html:

    <!-- analytics:start --> ... <!-- analytics:end -->

On every run it looks for the *existing* analytics block in each page's
<head>. An existing block is found by its two markers; if the block has
drifted (e.g. the GA ID was hand-edited on one page), the whole block —
from `<!-- analytics:start -->` to `<!-- analytics:end -->` — is replaced
with the current one. If a page has no block yet, the block is inserted
immediately before `</head>`.

    Idempotent: two consecutive runs produce byte-identical files.

Which files are touched
-----------------------
Every live HTML page the site actually ships (the same set sync_chrome.py
operates on) PLUS the published tree and the page templates:

  * site root + sections:  index.html, 404.html, {tools,comparisons,
    lists,blog,about,contact}/index.html and the article pages
  * content/published/**/*.html   (the canonical published copies)
  * src/templates/**/*.html       (so a fresh l4_render.py run is already
    correct; l4_render.py injects the block itself via {{ANALYTICS}})

Why a separate tool (and not sync_chrome.py)?
----------------------------------------------
sync_chrome.py treats _chrome.html as the only source of truth for the four
*body* chrome regions (icon sprite, header, footer, mobile tab bar) and
runs `--check` to fail on drift. GA lives in the <head>, which
sync_chrome.py deliberately never touches. Keeping the analytics block in
its own file + its own sync tool means:

  * `sync_chrome.py --check` stays green (its 4 regions are unchanged);
  * the site keeps its "edit one place, every page updates" convention;
  * a GA ID/flag change is one edit + one command, not 30 files.

Usage (from the site root):
    python tools/sync_analytics.py              # sync everything
    python tools/sync_analytics.py --dry-run    # report, write nothing
    python tools/sync_analytics.py --check      # exit 1 if any page is stale
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SNIPPET = ROOT / "src" / "components" / "_analytics.html"

_START = "<!-- analytics:start -->"
_END = "<!-- analytics:end -->"
_HEAD_CLOSE = "</head>"


def analytics_block() -> str:
    """Return the canonical GA block (the text between the markers)."""
    txt = SNIPPET.read_text(encoding="utf-8")
    i = txt.find(_START)
    j = txt.find(_END)
    if i < 0 or j < 0 or j < i:
        raise SystemExit(f"{SNIPPET.name}: missing analytics markers")
    block = txt[i:j + len(_END)]
    if "googletagmanager.com/gtag/js" not in block:
        raise SystemExit(f"{SNIPPET.name}: block has no gtag.js load line")
    return block


def _in_head_only(html: str) -> bool:
    """True if the markers are present and both live inside the <head>.

    The block must sit in the <head> (it loads the gtag loader). If the
    closing marker appears after `</head>` the page is structurally wrong
    and we refuse to touch it.
    """
    s = html.find(_START)
    e = html.find(_END)
    h = html.find(_HEAD_CLOSE)
    return s != -1 and e != -1 and (h == -1 or e < h)


def sync_page(page: Path, block: str, dry_run: bool) -> bool:
    """Replace or insert the GA block on one page. Returns True if changed."""
    html = page.read_text(encoding="utf-8")

    if _in_head_only(html):
        # existing block present (markers) — replace the whole marked region.
        s = html.find(_START)
        e = html.find(_END)
        new = html[:s] + block + html[e + len(_END):]
    elif _HEAD_CLOSE in html:
        # no block yet — insert it just before </head>.
        new = html.replace(_HEAD_CLOSE, block + "\n" + _HEAD_CLOSE, 1)
    else:
        # page has no </head> (not a real document we manage) — skip it.
        return False

    changed = new != html
    if changed and not dry_run:
        page.write_text(new, encoding="utf-8")
    return changed


def collect_pages() -> list[Path]:
    """Every HTML page the site ships that is NOT template-generated.

    This is the same live-tree set sync_chrome.py operates on (index.html
    / 404.html anywhere, excluding build dirs). These are the hand-written
    pages: home, the four section indexes, about, contact, 404 — which
    never go through l4_render.py, so their <head> gets the GA block from
    this script.

    ARTICLE / PUBLISHED PAGES ARE DELIBERATELY EXCLUDED
    -----------------------------------------------------
    content/published/** and the live article pages (tools/{slug},
    blog/{slug}, ...) are regenerated by l4_render.py from
    src/templates/*.html. That pipeline fills the ``{{ANALYTICS}}`` slot
    from the same _analytics.html source, so a freshly rendered page is
    already correct — and re-syncing it here would inject the block at a
    different <head> position than the renderer does, creating permanent
    --check drift. Templates stay slot-only (the renderer injects at
    render time; the two write the same bytes).

    Idempotent: two consecutive runs produce byte-identical files.
    """
    # Hand-written pages only: the site root index/404 plus the section
    # index pages that are maintained by hand and never go through
    # l4_render.py. Article pages (tools/{slug}, blog/{slug}, ...) are
    # regenerated by the renderer and are excluded here (see above).
    hand = [
        "index.html", "404.html",
        "about/index.html", "contact/index.html",
        "tools/index.html", "comparisons/index.html",
        "lists/index.html", "blog/index.html",
    ]
    pages = set()
    for rel in hand:
        p = ROOT / rel
        if p.exists():
            pages.add(p)
    return sorted(pages)


def main() -> None:
    ap = argparse.ArgumentParser(description="Sync the Google Analytics snippet into every page")
    ap.add_argument("--dry-run", action="store_true",
                    help="report what would change, write nothing")
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if any page is out of sync (CI / pre-commit)")
    args = ap.parse_args()

    block = analytics_block()
    pages = collect_pages()
    if not pages:
        print("no pages found", file=sys.stderr)
        sys.exit(1)

    changed = inserted = 0
    skipped: list[str] = []
    for p in pages:
        rel = p.relative_to(ROOT).as_posix()
        before = p.read_text(encoding="utf-8")
        had = _in_head_only(before)
        did_change = sync_page(p, block, args.dry_run)
        if not did_change:
            continue
        changed += 1
        inserted += 0 if had else 1
        verb = "would sync" if args.dry_run else "synced"
        kind = "updated" if had else "inserted"
        print(f"  [{verb}] {rel} ({kind})")

    print(f"\n{changed} page(s) "
          f"{'out of sync' if args.dry_run or args.check else 'written'} "
          f"({inserted} first-insert), {len(pages)} checked.")

    if args.check and changed:
        sys.exit(1)


if __name__ == "__main__":
    main()
