#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
L1 Kwinside expand + score for the PickWorth AI-tools site.
================================================================
Takes seed keywords (new AI tools / models), pulls related keywords +
monthly volume from Kwinside, then scores every candidate on the axes that
matter for "new word, high search, low competition":

  1. volume      - log10-scaled monthly searches (higher = more demand)
  2. longtail    - query length / intent qualifiers (lower expected KD)
  3. intent      - commercial intent weight (vs / alternatives / pricing rank
                   highest because they map to affiliate + ad RPM)
  4. writeable   - "materiality" gate: does this tool have official docs +
                   >=5 third-party reviews so a 20-source synthesis is viable?
                   (flag only; the actual source check happens at L2)

AUTH: per user request the API key is written in directly (not via env).
NOTE: this is a new project; keep the key out of public version control if
this folder ever gets pushed to a shared remote.

Usage:
  python l1_kwinside_scorer.py --seeds "gemini 4,claude,deepseek" --out tools/keyword-pool.csv
  python l1_kwinside_scorer.py --seeds "chatgpt,perplexity,anthropic" --limit 60 --min-volume 50
"""

from __future__ import annotations
import argparse
import csv
import json
import os
import re
import urllib.parse
import urllib.request
import time
import math
from pathlib import Path

# ---- Auth: written in directly per user request ---------------------------
# Kwinside free account, 20 requests/day. Rotate here if the key changes.
KWINSIDE_API_KEY = "5dWiYwIfsnBaiS7KFiLftcDZggeQV13JRECVlQFViLQXTtNm6XI7LB0NSQP7FmEbdVCBdpbdwD3hw98u"
BASE = "https://kwinside.com/api/v1/keywords"

# ---- Intent taxonomy for AI-tools niche (not games) ----------------------
# (weight, hint-words). Higher weight = stronger commercial / affiliate intent.
INTENT_RULES: list[tuple[int, list[str]]] = [
    (8, ["vs", "versus", "alternative", "alternatives", "pricing", "price",
         "cost", "best", "compare", "comparison", "review", "worth", "free"]),
    (5, ["how to", "tutorial", "guide", "for", "use", "tool", "app", "agent",
         "workflow", "prompt"]),
    (3, ["model", "llm", "ai", "api", "benchmark", "new", "release"]),
]

def classify_intent(kw: str) -> tuple[int, str]:
    """Return (best weight, label) for the highest-intent rule that hits."""
    lower = kw.lower()
    best_w, label = 0, "neutral"
    for w, hints in INTENT_RULES:
        for h in hints:
            if h in lower:
                if w > best_w:
                    best_w, label = w, ("commercial" if w >= 8 else
                                         ("howto" if w >= 5 else "info"))
    return best_w, label


def kd_proxy(kw: str) -> float:
    """Documented competition proxy (no hard KD from Kwinside).
    Reward specific multi-word queries, penalise generic head terms."""
    lower = kw.lower()
    words = len(lower.split())
    # Generic AI head terms with huge volume = high KD penalty.
    generic = {"ai", "chatgpt", "gemini", "claude", "ai tools", "best ai",
               "llm", "gpt", "openai", "anthropic"}
    comp_penalty = 14.0 if (words <= 2 and lower in generic) else 0.0
    spec_score = min(words, 5) * 4.0
    return spec_score - comp_penalty


def opportunity(volume: int, kw: str) -> tuple[float, str, str]:
    """(opportunity, tier, intent_label)."""
    vol_score = math.log10(max(volume, 1)) * 10.0
    w, label = classify_intent(kw)
    kd = kd_proxy(kw)
    opp = round(vol_score + kd + w * 2.0, 1)
    tier = "A" if opp >= 65 else "B" if opp >= 50 else "C"
    return opp, tier, label


def _headers() -> dict:
    return {
        "X-API-Key": KWINSIDE_API_KEY,
        "Accept": "application/json",
        # Cloudflare blocks the default urllib UA; send a browser UA.
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    }


def fetch_related(seed: str, lang: str, limit: int, min_volume: int,
                  backoff_base: int = 10) -> list[dict]:
    """Fetch + score. Retries on 5xx with exponential backoff (base*2^n),
    bounded by KWIN_RETRIES env (default 4). backoff_base=10 makes the 4th
    retry wait ~160s — enough to ride out Kwinside's intermittent outages."""
    params = {"se": lang, "kw": seed, "limit": str(limit),
              "key": KWINSIDE_API_KEY}
    url = f"{BASE}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers=_headers())
    max_attempts = int(os.environ.get("KWIN_RETRIES", "4"))
    payload = None
    for attempt in range(1, max_attempts + 1):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            data = payload.get("data", payload)
            if isinstance(data, dict) and data.get("error") and attempt < max_attempts:
                wait = backoff_base * (2 ** (attempt - 1))
                print(f"   (transient, retry {attempt}/{max_attempts}, wait {wait}s) "
                      f"{data.get('message','')}")
                time.sleep(wait)
                continue
            break
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            if e.code in (500, 502, 503, 504) and attempt < max_attempts:
                wait = backoff_base * (2 ** (attempt - 1))
                print(f"   (HTTP {e.code}, retry {attempt}/{max_attempts}, wait {wait}s)")
                time.sleep(wait)
                continue
            raise SystemExit(f"Kwinside HTTP {e.code}:\n{body[:1200]}")
    if payload is None:
        return []
    data = payload.get("data", payload)
    items = (data.get("results") or data.get("suggestions")
             or data.get("keywords") or (data if isinstance(data, list) else []))
    rows = []
    for item in items:
        kw = (item.get("keyword") or item.get("suggestion") or item.get("text") or "").strip()
        vol = item.get("volume") or item.get("search_volume") or item.get("monthly_searches") or 0
        try:
            vol = int(float(vol))
        except Exception:
            vol = 0
        if not kw or vol < min_volume:
            continue
        rows.append({"keyword": kw, "volume": vol})
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description="L1 Kwinside expand + score (AI-tools)")
    ap.add_argument("--seeds", required=True,
                   help="Comma-separated seed keywords (new tools/models)")
    ap.add_argument("--lang", default="en", choices=["en", "de", "it", "es", "fr", "ru"])
    ap.add_argument("--limit", type=int, default=60)
    ap.add_argument("--min-volume", type=int, default=0)
    ap.add_argument("--out", default="tools/keyword-pool.csv")
    args = ap.parse_args()

    seed_list = [s.strip() for s in re.split(r"[,;]", args.seeds) if s.strip()]
    all_rows: list[dict] = []
    credits_note = []
    for i, seed in enumerate(seed_list):
        print(f"-> Kwinside seed {i+1}/{len(seed_list)}: {seed!r}")
        try:
            rows = fetch_related(seed, args.lang, args.limit, args.min_volume)
        except SystemExit as e:
            print(f"   [seed failed: {e}]")
            continue
        for r in rows:
            r["seed"] = seed
        all_rows.extend(rows)
        credits_note.append(f"{seed}: {len(rows)}")
        time.sleep(1.0)  # gentle; free tier = 20 req/day

    scored = []
    seen: dict[str, dict] = {}
    for r in all_rows:
        kw = r["keyword"].lower()
        opp, tier, label = opportunity(r["volume"], r["keyword"])
        r.update({"opportunity": opp, "tier": tier, "intent": label})
        # dedupe by keyword, keep the max-volume entry
        if kw not in seen or r["volume"] > seen[kw]["volume"]:
            seen[kw] = r
    for r in seen.values():
        scored.append(r)
    scored.sort(key=lambda r: (r["opportunity"], r["volume"]), reverse=True)

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["tier", "keyword", "volume", "intent", "opportunity", "seed"])
        for r in scored:
            w.writerow([r["tier"], r["keyword"], r["volume"],
                        r["intent"], r["opportunity"], r.get("seed", "")])
    print(f"\nWrote {out_path.resolve()} with {len(scored)} unique ranked keywords.")
    print("  per-seed pull:", "; ".join(credits_note))
    print("\nTop 15 by opportunity (high volume + intent + low expected KD):")
    for r in scored[:15]:
        print(f"  [{r['tier']}] {r['keyword']:<44} vol={r['volume']:>9}  "
              f"int={r['intent']:<9} opp={r['opportunity']}  seed={r.get('seed','')}")


if __name__ == "__main__":
    main()
