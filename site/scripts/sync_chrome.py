#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sync_chrome.py — push src/components/_chrome.html into every page on the site.

WHY THIS EXISTS
---------------
The site chrome (icon sprite, site header, footer, mobile bottom tabs) used to
be copy-pasted into every HTML file, so one wording change in the footer meant
editing 28 files by hand. Article pages were already safe — l4_render.py
injects the chrome from _chrome.html at render time — but the hand-written
pages (home, the four section indexes, about, contact, 404) still carried
their own private copies, and those drifted.

This script makes _chrome.html the single source of truth for ALL pages:

    edit src/components/_chrome.html
    python tools/sync_chrome.py        # every page updated in place

HOW IT WORKS
------------
Each page carries marker comments around its four chrome regions:

    <!-- chrome:header -->
    <header class="site-header">...</header>
    <!-- /chrome:header -->

On every run the script replaces whatever sits between a marker pair with the
current fragment from _chrome.html, rewriting that fragment's {{ROOT}} to the
correct relative depth for the page it is writing to. Pages that have no
markers yet get them added automatically on first run (one-time migration), so
there is nothing to set up by hand.

Idempotent: two consecutive runs produce byte-identical files. Nothing outside
the four chrome regions is ever touched — page-specific body content, JSON-LD
and <head> meta are left exactly as they are.

RELATION TO l4_render.py
------------------------
l4_render.py also injects the chrome, at draft-render time, so a freshly
rendered article page is already correct. This script covers the case where
ONLY the chrome changed: no need to re-render drafts to propagate a footer
edit. Running both is safe — they write the same bytes.

Usage (from the site root):
    python tools/sync_chrome.py              # sync everything
    python tools/sync_chrome.py --dry-run    # report, write nothing
    python tools/sync_chrome.py --check      # exit 1 if any page is stale
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHROME_SRC = ROOT / "src" / "components" / "_chrome.html"

# region name -> (block opening tag, block closing tag)
# The opening tags are deliberately specific: a page contains several <nav>
# and <svg> elements, and matching on a bare tag name would grab the wrong one.
REGIONS: list[tuple[str, str, str]] = [
    ("icons",
     '<svg xmlns="http://www.w3.org/2000/svg" style="display:none"', "</svg>"),
    ("header", '<header class="site-header">', "</header>"),
    ("footer", '<footer class="site-footer">', "</footer>"),
    ("mtab", '<nav class="mtab"', "</nav>"),
]
REGION_NAMES = [r[0] for r in REGIONS]

# <!-- chrome:NAME --> ... <!-- /chrome:NAME -->  (whitespace tolerant)
MARK_RE = re.compile(
    r"[ \t]*<!--\s*chrome:(%s)\s*-->.*?<!--\s*/\s*chrome:\1\s*-->[ \t]*\n?"
    % "|".join(REGION_NAMES),
    re.DOTALL,
)


def strip_comments(text: str) -> str:
    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)


def chrome_fragments() -> dict[str, str]:
    """Split _chrome.html into its four fragments (same cut l4_render.py makes)."""
    txt = strip_comments(CHROME_SRC.read_text(encoding="utf-8"))
    frags: dict[str, str] = {}
    for name, start, end in REGIONS:
        i = txt.find(start)
        if i < 0:
            raise SystemExit(
                f"{CHROME_SRC.name}: region {name!r} not found "
                f"(looked for {start!r})")
        j = txt.find(end, i + len(start))
        if j < 0:
            raise SystemExit(
                f"{CHROME_SRC.name}: region {name!r} never closed with {end!r}")
        frags[name] = txt[i:j + len(end)].strip()
    missing = [n for n in REGION_NAMES if not frags.get(n)]
    if missing:
        raise SystemExit(f"{CHROME_SRC.name}: empty regions: {missing}")
    return frags


def page_depth(page: Path) -> int:
    """How many '../' segments reach the site root from this page."""
    return len(page.relative_to(ROOT).parts) - 1


def add_markers(html: str) -> tuple[str, list[str]]:
    """Wrap any existing chrome blocks in markers. Returns (html, added names)."""
    added: list[str] = []
    for name, start, end in REGIONS:
        if f"<!-- chrome:{name} -->" in html:
            continue
        i = html.find(start)
        if i < 0:
            continue                     # page genuinely lacks this block
        j = html.find(end, i + len(start))
        if j < 0:
            continue
        j += len(end)
        html = (html[:i] + f"<!-- chrome:{name} -->\n" + html[i:j]
                + f"\n<!-- /chrome:{name} -->\n" + html[j:])
        added.append(name)
    return html, added


def sync_page(page: Path, frags: dict[str, str], dry_run: bool
              ) -> tuple[bool, list[str], list[str]]:
    """Sync one page. Returns (changed, migrated_regions, missing_regions)."""
    html = page.read_text(encoding="utf-8")
    root = "../" * page_depth(page)

    if not MARK_RE.search(html):
        html, migrated = add_markers(html)
    else:
        migrated = []

    def repl(m: re.Match) -> str:
        name = m.group(1)
        frag = frags[name].replace("{{ROOT}}", root)
        return f"<!-- chrome:{name} -->\n{frag}\n<!-- /chrome:{name} -->\n"

    new = MARK_RE.sub(repl, html)

    # a region present in _chrome.html but absent from this page is reported,
    # never silently inserted — the insertion point would be a guess.
    missing = [n for n in REGION_NAMES if f"<!-- chrome:{n} -->" not in new]

    # A first-run migration MUST persist even when the fragment content is
    # byte-identical to what the page already had: otherwise the markers are
    # added in memory, `changed` stays False, nothing is written, and every
    # later run reports the same migration again.
    changed = bool(migrated) or new != html
    if changed and not dry_run:
        page.write_text(new, encoding="utf-8")
    return changed, migrated, missing


def collect_pages() -> list[Path]:
    return sorted(
        p for p in ROOT.rglob("*.html")
        if p.name in ("index.html", "404.html")
        and "content" not in p.parts and "src" not in p.parts
        and ".workbuddy" not in p.parts
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--dry-run", action="store_true",
                    help="report what would change, write nothing")
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if any page is out of sync (CI / pre-commit)")
    args = ap.parse_args()

    frags = chrome_fragments()
    pages = collect_pages()
    if not pages:
        print("no pages found", file=sys.stderr)
        sys.exit(1)

    changed = migrated_pages = 0
    warnings: list[str] = []
    for p in pages:
        did_change, migrated, missing = sync_page(p, frags, args.dry_run)
        rel = p.relative_to(ROOT).as_posix()
        if migrated:
            migrated_pages += 1
            print(f"  [markers added] {rel}: {', '.join(migrated)}")
        if missing:
            warnings.append(f"{rel}: missing region(s) {missing}")
        if did_change:
            changed += 1
            verb = "would sync" if args.dry_run else "synced"
            print(f"  [{verb}] {rel}")

    print(f"\n{migrated_pages} page(s) migrated, {changed} page(s) "
          f"{'out of sync' if args.dry_run or args.check else 'written'}, "
          f"{len(pages)} checked.")
    for w in warnings:
        print(f"  WARNING: {w}", file=sys.stderr)

    if args.check and changed:
        sys.exit(1)


if __name__ == "__main__":
    main()
