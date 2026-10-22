#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
l2_source_fetch.py — gather the raw material for one article.

Everything we can reach from the sandbox is fair game here, and everything
saved is primary data we can cite:

  * GitHub API        -> stars, licence, last commit, description (hard facts)
  * Wikipedia API     -> background / factual framing
  * HN Algolia        -> what real developers actually say (third-party opinion)
  * official pricing  -> current numbers straight from the vendor

Output: tools/research/<slug>.json  + a human-readable <slug>.md digest

Run from site root:  python tools/l2_source_fetch.py --slug cursor-ai-open-source-alternatives
"""
from __future__ import annotations

import argparse
import json
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESEARCH = ROOT / "tools" / "research"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

GH_API = "https://api.github.com/repos/"
HN_API = "https://hn.algolia.com/api/v1/search"
WIKI_API = "https://en.wikipedia.org/w/api.php"


def get_json(url: str, timeout: int = 20):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        print(f"    HTTP {e.code}  {url}")
        return None
    except Exception as e:  # noqa: BLE001
        print(f"    FAIL {type(e).__name__}  {url}")
        return None


# --------------------------------------------------------------------------
# GitHub: primary data for open-source alternatives
# --------------------------------------------------------------------------
def github_repo(slug: str) -> dict | None:
    d = get_json(GH_API + slug)
    if not d or "full_name" not in d:
        return None
    return {
        "repo": d.get("full_name"),
        "homepage": d.get("homepage") or "",
        "description": (d.get("description") or "").strip(),
        "stars": d.get("stargazers_count"),
        "forks": d.get("forks_count"),
        "open_issues": d.get("open_issues_count"),
        "language": d.get("language") or "",
        "license": ((d.get("license") or {}).get("spdx_id") or "NONE"),
        "created_at": (d.get("created_at") or "")[:10],
        "pushed_at": (d.get("pushed_at") or "")[:10],
        "topics": ", ".join(d.get("topics") or []),
        "archived": bool(d.get("archived")),
        "url": f"https://github.com/{d.get('full_name')}",
    }


def months_since(date_str: str) -> int | None:
    if not date_str:
        return None
    try:
        then = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        return round((datetime.now(timezone.utc) - then).days / 30.4)
    except ValueError:
        return None


# --------------------------------------------------------------------------
# Wikipedia: neutral background
# --------------------------------------------------------------------------
def wiki_extract(title: str, chars: int = 4000) -> dict | None:
    url = (f"{WIKI_API}?action=query&prop=extracts&explaintext=1"
           f"&redirects=1&format=json&titles={urllib.parse.quote(title)}")
    d = get_json(url)
    if not d:
        return None
    pages = (d.get("query") or {}).get("pages") or {}
    for _, p in pages.items():
        if p.get("extract"):
            return {"title": p.get("title"), "extract": p["extract"][:chars],
                    "url": f"https://en.wikipedia.org/wiki/{urllib.parse.quote(p['title'])}"}
    return None


# --------------------------------------------------------------------------
# Hacker News: genuine third-party commentary
# --------------------------------------------------------------------------
def hn_discussions(query: str, min_points: int = 15, take: int = 10) -> list[dict]:
    url = f"{HN_API}?query={urllib.parse.quote(query)}&hitsPerPage=30"
    d = get_json(url)
    if not d:
        return []
    out = []
    for h in d.get("hits", []):
        if (h.get("points") or 0) < min_points:
            continue
        out.append({
            "query": query,
            "title": h.get("title"),
            "points": h.get("points"),
            "comments": h.get("num_comments"),
            "date": (h.get("created_at") or "")[:10],
            "url": h.get("url") or "",
            "hn_url": f"https://news.ycombinator.com/item?id={h.get('objectID')}",
            "text": (h.get("story_text") or "")[:400],
        })
        if len(out) >= take:
            break
    return out


def hn_multi(queries: list[str], min_points: int) -> list[dict]:
    """Run several queries and merge, deduped by thread id, best first."""
    seen: set[str] = set()
    merged: list[dict] = []
    for q in queries:
        for h in hn_discussions(q, min_points=min_points, take=12):
            key = h["hn_url"]
            if key in seen:
                continue
            seen.add(key)
            merged.append(h)
        time.sleep(0.4)
    merged.sort(key=lambda x: -(x["points"] or 0))
    return merged


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--repos", default="",
                    help="comma-separated owner/repo list")
    ap.add_argument("--wiki", default="", help="Wikipedia title for background")
    ap.add_argument("--hn", default="",
                    help="comma-separated queries for Hacker News discussion")
    ap.add_argument("--hn-points", type=int, default=15,
                    help="minimum HN points to keep a thread")
    args = ap.parse_args()

    if RESEARCH.exists() is False:
        RESEARCH.mkdir(parents=True)

    bundle: dict = {
        "slug": args.slug,
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "github": [],
        "wikipedia": None,
        "hackernews": [],
    }

    # --- GitHub ---
    repos = [r.strip() for r in args.repos.split(",") if r.strip()]
    print(f"[github] {len(repos)} repos")
    for r in repos:
        print(f"  fetching {r}")
        info = github_repo(r)
        if info:
            info["months_since_push"] = months_since(info["pushed_at"])
            bundle["github"].append(info)
            print(f"    {info['stars']:>7} stars | {info['license']:<12} "
                  f"| pushed {info['pushed_at']}")
        time.sleep(0.6)   # stay well inside the unauthenticated rate limit

    # --- Wikipedia ---
    if args.wiki:
        print(f"[wikipedia] {args.wiki}")
        w = wiki_extract(args.wiki)
        if w:
            bundle["wikipedia"] = w
            print(f"    {len(w['extract'])} chars")

    # --- Hacker News (several queries, merged and deduped) ---
    hn_queries = [q.strip() for q in args.hn.split(",") if q.strip()]
    if hn_queries:
        print(f"[hackernews] {len(hn_queries)} queries")
        hits = hn_multi(hn_queries, min_points=args.hn_points)
        bundle["hackernews"] = hits
        for h in hits[:8]:
            print(f"    {h['points']:>4} pts  {h['date']}  {h['title'][:70]}")

    # --- persist ---
    RESEARCH.mkdir(parents=True, exist_ok=True)
    jpath = RESEARCH / f"{args.slug}.json"
    jpath.write_text(json.dumps(bundle, indent=2, ensure_ascii=False),
                     encoding="utf-8")

    mpath = RESEARCH / f"{args.slug}.md"
    lines = [f"# Research digest — {args.slug}",
             f"_fetched {bundle['fetched_at']}_\n"]
    if bundle["github"]:
        lines.append("## Open-source candidates (GitHub primary data)\n")
        lines.append("| repo | stars | licence | last push | topics |")
        lines.append("|---|---:|---|---|---|---|")
        for g in sorted(bundle["github"], key=lambda x: -(x["stars"] or 0)):
            lines.append(f"| {g['repo']} | {g['stars']:,} | {g['license']} "
                         f"| {g['pushed_at']} | {g['topics'][:60]} |")
        lines.append("")
        for g in sorted(bundle["github"], key=lambda x: -(x["stars"] or 0)):
            lines.append(f"**{g['repo']}** — {g['description']}")
            lines.append(f"  {g['url']} · {g['language']} · created {g['created_at']} "
                         f"· {g['open_issues']} open issues")
    if bundle["wikipedia"]:
        lines.append(f"\n## Background — {bundle['wikipedia']['title']}\n")
        lines.append(bundle["wikipedia"]["extract"][:2200])
    if bundle["hackernews"]:
        lines.append("\n## Practitioner commentary (Hacker News)\n")
        for h in bundle["hackernews"]:
            lines.append(f"- **{h['title']}** ({h['points']} pts, "
                         f"{h['comments']} comments, {h['date']})")
            if h["text"]:
                lines.append(f"  > {h['text'][:260]}")
            lines.append(f"  {h['hn_url']}")
    mpath.write_text("\n".join(lines), encoding="utf-8")

    print(f"\nwrote {jpath.relative_to(ROOT)}")
    print(f"wrote {mpath.relative_to(ROOT)}")
    print(f"sources captured: {len(bundle['github'])} repos, "
          f"{len(bundle['hackernews'])} discussions, "
          f"{1 if bundle['wikipedia'] else 0} reference")


if __name__ == "__main__":
    main()
