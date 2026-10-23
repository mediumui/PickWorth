#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
draft_from_page.py — one-off migration helper.

Extracts the head / verdict / body / sources / related content out of an
ALREADY-WRITTEN live page and drops a content/drafts/{slug}.json so the
page can be re-rendered through the new L4 pipeline. This makes the
existing hand-written articles first-class citizens of the template
convention without rewriting their prose.

Usage:
  python tools/draft_from_page.py --page tools/grok/index.html --type review
  python tools/draft_from_page.py --page comparisons/chatgpt-vs-claude/index.html --type compare
  python tools/draft_from_page.py --page lists/best-image-generation-tools/index.html --type list
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DRAFTS = ROOT / "content" / "drafts"

SECTION_BY_TYPE = {"review": "tools", "compare": "comparisons",
                   "list": "lists", "blog": "blog", "author": "about"}


def rel_to_root(page: Path) -> str:
    parts = page.relative_to(ROOT).parts
    depth = len(parts) - 1
    return ("../" * depth) if depth > 0 else ""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--page", required=True)
    ap.add_argument("--type", required=True,
                    choices=["review", "compare", "list", "blog", "author"])
    ap.add_argument("--name", help="breadcrumb name (defaults to folder name)")
    args = ap.parse_args()

    page = ROOT / args.page
    html = page.read_text(encoding="utf-8")
    root = rel_to_root(page)
    slug = page.parent.name

    title = re.search(r"<title>(.*?)\s*\|\s*PickWorth</title>", html).group(1)
    desc = re.search(r'<meta name="description" content="([^"]+)"', html).group(1)
    jsonld = re.search(r'<script type="application/ld\+json">\s*(\{.*?\})\s*</script>',
                       html, re.DOTALL).group(1)
    jsonld = json.loads(jsonld)

    h1 = re.search(r"<h1>(.*?)</h1>", html, re.DOTALL).group(1)
    kicker = re.search(r'<p class="kicker">(.*?)</p>', html, re.DOTALL).group(1)
    lead = re.search(r'<p class="lead">(.*?)</p>', html, re.DOTALL)
    lead = lead.group(1) if lead else ""
    date = re.search(r"<span>(Reviewed|Updated) ([^<]+)</span>", html)
    date_txt = date.group(2) if date else "22 October 2026"

    score = re.search(r'<div class="score [^"]*"><strong>(.*?)</strong>', html)
    score_cls = re.search(r'<div class="score ([^"]+)">', html)
    score_lbl = re.search(r'<div class="score [^"]*"><strong>[^<]+</strong><span>(.*?)</span>', html)

    verdict = re.search(r'<div class="verdict">\s*<h3>.*?</h3>\s*(.*?)\s*</div>', html, re.DOTALL).group(1)

    toc = re.findall(r'<li><a href="#(\w+[^"]*)">(.*?)</a></li>', html)

    # body: from first <h2 id= ... up to (but not including) the "Related" rule
    body_m = re.search(r'(<h2 id="[^"]+">.*?)(?:<div class="rule">Related|</article>)', html, re.DOTALL)
    body = body_m.group(1).strip()

    # strip a trailing sources section out of body if present
    src_split = re.search(r'(<h2 id="sources">.*?</section>)\s*$', body, re.DOTALL)
    if src_split:
        body = body[:src_split.start()].strip()

    sources = re.findall(r'<li>(?:<\d+\.>)?\s*<a href="([^"]+)">(.*?)</a></li>', html)
    if not sources:
        sources = []
        src_block = re.search(r'<section class="sources">\s*<ol>(.*?)</ol>\s*</section>', html, re.DOTALL)
        if src_block:
            for li in re.findall(r"<li>(.*?)</li>", src_block.group(1), re.DOTALL):
                li = li.strip()
                li = re.sub(r"^\d+\.\s*", "", li)
                li = re.sub(r"<a href=\"([^\"]+)\">(.*?)</a>", r"\2 — \1", li)
                li = re.sub(r"<[^>]+>", "", li)
                sources.append(li.strip())

    rel_cards = []
    for card_m in re.finditer(r'<article class="card">.*?</article>', html, re.DOTALL):
        c = card_m.group(0)
        icon = re.search(r'<use href="#(\w+)"></use>', c)
        tclass = re.search(r'<span class="tag(?: (\w+))?">', c)
        tag = re.search(r'<span class="tag[^"]*">(.*?)</span>', c)
        ttl = re.search(r'<h3><a href="[^"]*">(.*?)</a></h3>', c)
        blurb = re.search(r'<p>(.*?)</p>', c)
        link = re.search(r'<a class="more"[^>]*>(.*?)</a>', c)
        href = re.search(r'<h3><a href="([^"]*)">', c)
        rel_cards.append({
            "icon": icon.group(1) if icon else "i-sources",
            "tag": tag.group(1) if tag else "",
            "tag_class": (tclass.group(1) if tclass and tclass.group(1) else ""),
            "href": re.sub(r"^(?:\.\./)+", "", href.group(1)) if href else "",
            "title": ttl.group(1) if ttl else "",
            "blurb": blurb.group(1) if blurb else "",
            "link": link.group(1) if link else "",
        })

    draft = {
        "slug": slug,
        "type": args.type,
        "section": SECTION_BY_TYPE[args.type],
        "meta": {"title": title, "desc": desc, "jsonld": jsonld},
        "head": {
            "kicker": kicker, "h1": h1, "lead": lead, "date": date_txt,
            "name": args.name or slug,
            "score": score.group(1) if score else "4.0",
            "score_class": score_cls.group(1) if score_cls else "good",
            "score_label": score_lbl.group(1) if score_lbl else "Our score",
        },
        "toc": toc,
        "verdict": verdict,
        "body": body,
        "sources": sources,
        "related": rel_cards,
    }

    DRAFTS.mkdir(parents=True, exist_ok=True)
    out = DRAFTS / f"{slug}.json"
    out.write_text(json.dumps(draft, indent=2, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT)}")
    print(f"  head.h1={h1[:40]!r} toc={len(toc)} sources={len(sources)} related={len(rel_cards)}")


if __name__ == "__main__":
    main()
