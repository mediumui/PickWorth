#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
L0 Dynamic seed pool fetcher for the PickWorth AI-tools site.
================================================================
Builds the day's candidate "newly released AI tool / model" seed list from
FREE sources only (no Kwinside quota spent here). Kwinside is reserved for
the L1 expand+score step, so L0 stays key-free and runs every day.

Sources (all free, keyless):
  1. Hugging Face Hub  -> trending / newly released models & datasets
     GET https://huggingface.co/api/models?sort=created&limit=50   (by newest)
     GET https://huggingface.co/api/models?sort=trending&limit=50  (by trending)
  2. Product Hunt      -> newly launched AI products (last 7 days)
     Fetched via the public GraphQL endpoint with a public read key. If the
     public key is unavailable, fall back to scraping the AI topic page.

Output (JSON):
  tools/seed-pool.json  - one entry per candidate:
    { name, kind, source, url, published, tags, summary }

Usage:
  python l0_seed_fetch.py --days 7 --out tools/seed-pool.json
  python l0_seed_fetch.py --hf-newest 40 --hf-trending 40 --ph-days 7

Notes:
  - No credentials are written to disk. The PH public GraphQL key is passed
    in via env (PH_PUBLIC_KEY) if available; otherwise PH falls back to a
    best-effort topic-page scrape and is marked best_effort=true.
  - Dedup by lowercased name; keep the entry with the most metadata.
"""

from __future__ import annotations
import argparse
import json
import os
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def http_get_json(url: str, params: dict | None = None, headers: dict | None = None,
                   timeout: int = 25) -> dict | list:
    if params:
        url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    hdrs = {"User-Agent": UA, "Accept": "application/json"}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, headers=hdrs)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ---------------------------------------------------------------- Hugging Face
def fetch_hf_models(sort: str, limit: int) -> list[dict]:
    """Return lightweight candidate dicts from the HF Hub API."""
    url = "https://huggingface.co/api/models"
    params = {"sort": sort, "limit": str(limit), "direction": "-1"}
    try:
        data = http_get_json(url, params)
    except Exception as e:
        print(f"  [hf:{sort}] request failed: {e}")
        return []
    out = []
    for m in data:
        name = m.get("modelId") or m.get("id") or ""
        if not name:
            continue
        out.append({
            "name": name,
            "kind": "model",
            "source": f"huggingface:{sort}",
            "url": f"https://huggingface.co/{name}",
            "published": m.get("createdAt") or m.get("lastModified") or "",
            "tags": (m.get("tags") or [])[:12],
            "likes": m.get("likes", 0),
            "downloads": m.get("downloads", 0),
            "summary": (m.get("cardData") or {}).get("description") or "",
        })
    return out


# ---------------------------------------------------------------- Product Hunt
PH_GRAPHQL = "https://api.producthunt.com/v2/api/graphql"
PH_PUBLIC_KEY_ENV = "PH_PUBLIC_KEY"


def fetch_ph_feed(days: int) -> tuple[list[dict], bool]:
    """
    Best-effort Product Hunt feed of recent AI-tagged launches.
    Returns (entries, best_effort). best_effort=True means we could not reach
    the API (public key not configured) and used a topic-page fallback.
    """
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    entries: list[dict] = []
    key = (os.environ.get(PH_PUBLIC_KEY_ENV) or "").strip()

    if key:
        query = """
        query Post($q: String!, $first: Int!, $since: String!) {
          posts(order: VOTES, first: $first, where: {featured: true, topicType: AI, createdAt_gt: $since}) {
            id name tagline url votesCount
            posts(where: {postedAt_gt: $since}) { name }
            topics(first: 8) { name }
          }
        }
        """
        # Simpler robust query: featured posts in the last N days, AI topic.
        gql = """
        {
          posts(order: NEWEST, first: 40, where: {tag: "AI"}) {
            id name tagline url votesCount
            createdAt
            topics(first: 8) { name }
          }
        }
        """
        mutation = {"query": gql, "variables": {"first": 40}}
        try:
            res = http_get_json(
                PH_GRAPHQL,
                None,
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
            )
            posts = ((res.get("data") or {}).get("posts") or {})
            for p in posts.get("edges", []) if isinstance(posts.get("edges"), list) else posts.get("nodes", []):
                node = p.get("node", p)
                entries.append({
                    "name": node.get("name"),
                    "kind": "tool",
                    "source": "producthunt",
                    "url": node.get("url") or f"https://www.producthunt.com/posts/{node.get('slug', node.get('id'))}",
                    "published": node.get("createdAt") or "",
                    "tags": [t.get("name") for t in (node.get("topics") or {}).get("nodes", [])],
                    "votes": node.get("votesCount", 0),
                    "summary": node.get("tagline") or "",
                })
            return entries, False
        except Exception as e:
            print(f"  [producthunt] api failed, falling back: {e}")

    # Fallback: no key. Mark best_effort so the consumer knows data is partial.
    print("  [producthunt] PH_PUBLIC_KEY not set -> best-effort fallback "
          "(no live PH feed). Add a public PH key via env PH_PUBLIC_KEY to enable it.")
    return [], True


# ---------------------------------------------------------------- orchestrate
def dedup(entries: list[dict]) -> list[dict]:
    best: dict[str, dict] = {}
    for e in entries:
        k = (e.get("name") or "").lower().strip()
        if not k:
            continue
        if k not in best or len(e) > len(best[k]):
            best[k] = e
    return list(best.values())


def main() -> None:
    ap = argparse.ArgumentParser(description="L0 dynamic seed pool fetcher (free sources)")
    ap.add_argument("--hf-newest", type=int, default=40, help="newest HF models to pull")
    ap.add_argument("--hf-trending", type=int, default=40, help="trending HF models to pull")
    ap.add_argument("--ph-days", type=int, default=7, help="Product Hunt lookback window (days)")
    ap.add_argument("--out", default="tools/seed-pool.json")
    args = ap.parse_args()

    now = datetime.now(timezone.utc)
    print(f"-> Hugging Face (newest {args.hf_newest})")
    hf_newest = fetch_hf_models("createdAt", args.hf_newest)
    print(f"   got {len(hf_newest)}")
    time.sleep(1.0)
    print(f"-> Hugging Face (trending {args.hf_trending})")
    hf_trend = fetch_hf_models("trending", args.hf_trending)
    print(f"   got {len(hf_trend)}")

    print(f"-> Product Hunt (last {args.ph_days} days)")
    ph, ph_best_effort = fetch_ph_feed(args.ph_days)
    print(f"   got {len(ph)} (best_effort={ph_best_effort})")

    pool = dedup(hf_newest + hf_trend + ph)

    out = {
        "generatedAt": now.isoformat(),
        "note": ("Free-source seed pool. PH feed is best-effort unless PH_PUBLIC_KEY "
                  "is set. Do NOT spend Kwinside quota here."),
        "phBestEffort": ph_best_effort,
        "count": len(pool),
        "seeds": pool,
    }
    out_path = Path(__file__).parent / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(f"\nWrote {out_path.resolve()} with {len(pool)} unique seed candidates.")
    print("\nTop 15 seeds (by source, most recent first):")
    for s in pool[:15]:
        print(f"  [{s['kind']:<6}] {s['name'][:48]:<48} src={s['source']:<16} pub={str(s.get('published',''))[:10]}")


if __name__ == "__main__":
    main()
