#!/usr/bin/env python3
"""Generate llms.txt (+ llms-full.txt) from content/drafts/*.json.

Single source of truth = the JSON drafts, so llms.txt always matches the
rendered pages. Standard-library only; no build step, Cloudflare ready.

Usage:
    python tools/gen_llms_txt.py [--full]

Output:
    llms.txt       - one-line-per-page index (the canonical llms.txt)
    llms-full.txt  - full page text/answers for the content pages (optional, --full)

Placement: drop both files at the site ROOT (D:/WorkBuddy/pickworthhq).
Serving: Cloudflare Pages serves any file at / as-is; AI crawlers fetch
https://pickworth.top/llms.txt directly. No robots change needed
(llms.txt is an open convention; leave robots.txt allowing /).
"""
import json, glob, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://pickworth.top"

SECTION_TITLE = {
    "tools": "Tool Reviews",
    "comparisons": "Head-to-Head Comparisons",
    "lists": "Best-Of Lists",
    "blog": "Journal & Analysis",
}


def clean(s: str) -> str:
    """Collapse whitespace, strip em-dashes/quotes that break markdown."""
    s = re.sub(r"\s+", " ", (s or "")).strip()
    s = s.replace("\u2014", " ").replace("\u2019", "'").replace("\u201c", '"').replace("\u201d", '"')
    s = re.sub(r"\s+", " ", s).strip()
    return s


def strip_tags(html: str) -> str:
    return re.sub(r"<[^>]+>", " ", html or "").strip()


def load_rows():
    rows = []
    for f in sorted(glob.glob(os.path.join(ROOT, "content", "drafts", "*.json"))):
        d = json.load(open(f, encoding="utf-8"))
        sec, slug, typ = d.get("section"), d.get("slug"), d.get("type")
        if not sec or not slug:
            continue
        h, m = d.get("head", {}), d.get("meta", {})
        url = f"{BASE}/{sec}/{slug}/"
        desc = m.get("desc") or clean(strip_tags(h.get("lead", "")))
        title = m.get("title") or h.get("h1") or slug
        rows.append({"sec": sec, "typ": typ, "slug": slug, "url": url,
                     "title": clean(title), "desc": clean(desc),
                     "date": h.get("date", ""), "draft": d, "f": f})
    return rows


def build_llms(rows):
    out = [
        "# PickWorth",
        "",
        "> PickWorth is an independent review site that hands-on tests AI tools "
        "(ChatGPT, Claude, DeepSeek, Grok, Perplexity and more).",
        "> Honest, price-verified verdicts, head-to-head comparisons, and best-of "
        "lists, written by a single editorial team.",
        "> No ads in reviews, no paid placement. Method: "
        "https://pickworth.top/blog/how-we-test-ai-tools/",
        "",
        "## Core Pages",
        f"- [Home]({BASE}/): Know which AI tools are actually worth paying for.",
        f"- [Tool Reviews]({BASE}/tools/): Reviews of ChatGPT, Claude, DeepSeek, Grok, and Perplexity with verified prices and our 0-5 score.",
        f"- [Comparisons]({BASE}/comparisons/): Head-to-head matchups scored per dimension, with the cost question answered.",
        f"- [Best-Of Lists]({BASE}/lists/): Buyer's guides that pick the right tool by your actual job, not the loudest marketing.",
        f"- [Journal]({BASE}/blog/): Essays on how we test, why prices move, and when open source matters.",
        f"- [About]({BASE}/about/): Editorial standards, who funds the site, and why funding never touches the verdicts.",
        f"- [Contact]({BASE}/contact/): Report an error or request a comparison.",
    ]
    for sec in ("tools", "comparisons", "lists", "blog"):
        out.append("")
        out.append(f"## {SECTION_TITLE[sec]}")
        for r in rows:
            if r["sec"] != sec:
                continue
            out.append(f"- [{r['title']}]: {r['url']} - {r['desc']}")
    return "\n".join(out) + "\n"


def build_full(rows):
    """llms-full.txt: each content page's title + answer + key facts, markdown.
    This is the version LLMs fetch when they want more than a one-liner."""
    out = [
        "# PickWorth - Full Content",
        "",
        "> Full-text, machine-readable version of every PickWorth review, "
        "comparison, list and essay. Use llms.txt for the index; this file "
        "carries the actual answers.",
        "",
    ]
    for sec in ("tools", "comparisons", "lists", "blog"):
        out.append(f"## {SECTION_TITLE[sec]}")
        out.append("")
        for r in rows:
            if r["sec"] != sec:
                continue
            d, h = r["draft"], r["draft"].get("head", {})
            out.append(f"### {r['title']}")
            out.append(f"URL: {r['url']}")
            out.append(f"Updated: {h.get('date', 'n/a')}")
            # direct-answer block if present
            if d.get("answer"):
                out.append(f"Answer: {clean(d['answer'])}")
            # verdict / lead as the citable claim
            claim = d.get("verdict") or h.get("lead", "")
            claim = clean(strip_tags(claim))
            if claim:
                out.append(f"Citation: {claim}")
            # numeric facts extracted from verdict/lead (GEO: statistical signals)
            nums = re.findall(
                r"\$\d+(?:\.\d+)?(?:\s*/\s*(?:month|mo|yr|year))?"
                r"|\d+(?:\.\d+)?\s*(?:x|faster|cheaper|times|GB|tokens|words|chars)"
                r"|context window of \d+\s*\w+",
                (d.get("verdict", "") + " " + h.get("lead", "")), re.I,
            )
            if nums:
                out.append("Key numbers: " + "; ".join(dict.fromkeys(n.strip() for n in nums)))
            out.append("")
        out.append("")
    return "\n".join(out)


def main():
    rows = load_rows()
    write = build_llms(rows)
    open(os.path.join(ROOT, "llms.txt"), "w", encoding="utf-8").write(write)
    print(f"llms.txt: {len(rows)} content pages + core pages")
    if "--full" in sys.argv:
        full = build_full(rows)
        open(os.path.join(ROOT, "llms-full.txt"), "w", encoding="utf-8").write(full)
        print(f"llms-full.txt: written ({len(full.splitlines())} lines)")


if __name__ == "__main__":
    main()
