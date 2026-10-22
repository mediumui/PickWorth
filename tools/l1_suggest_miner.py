#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
l1_suggest_miner.py — long-tail keyword discovery via Google Autosuggest.

Free alternative to Kwinside: no API key, no daily cap, and the phrases are
real queries people type. Kwinside stayed up here for search volume, because
autocomplete gives order but not numbers.

Strategy
  1. seeds x modifiers produce base phrases
  2. alphabet soup expands each phrase ("chatgpt pricing a".."z")
  3. every suggestion is scored by buyer intent and long-tail specificity

Output: tools/keyword-pool.csv  (tier,keyword,tokens,intent,score,source)

Run from site root:  python tools/l1_suggest_miner.py --seeds "..."
"""
from __future__ import annotations

import argparse
import csv
import json
import ssl
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = "tools/keyword-pool.csv"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

SUGGEST = "https://suggestqueries.google.com/complete/search"

# ---- intent weights -------------------------------------------------------
# Buyer/comparison intent converts best for a review site, so it scores highest.
INTENT_RULES: list[tuple[int, tuple[str, ...]]] = [
    (9, ("vs ", " versus ", "alternative", "compare", "better than")),
    (8, ("pricing", "price", "cost", "worth it", "worth the money", "subscription")),
    (7, ("best", "review", "top ", "is it good")),
    (5, ("how to", "tutorial", "guide", "for beginners")),
    (4, ("free", "api", "model", "limit")),
]
DEFAULT_INTENT = 2


def suggest(q: str, retries: int = 3) -> list[str]:
    """Return Google autocomplete phrases for q."""
    url = f"{SUGGEST}?client=firefox&hl=en&gl=us&q={urllib.parse.quote(q)}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=15, context=CTX) as r:
                return json.loads(r.read().decode("utf-8", "replace"))[1]
        except Exception:  # noqa: BLE001  (transient upstream, back off)
            if attempt == retries:
                return []
            time.sleep(1.5 * attempt)
    return []


def intent_weight(kw: str) -> tuple[int, str]:
    low = f" {kw.lower()} "
    for weight, needles in INTENT_RULES:
        for n in needles:
            if n in low:
                return weight, n.strip()
    return DEFAULT_INTENT, "-"


def score(kw: str, intent: int, seed_bonus: bool) -> float:
    """Longer queries = more specific = easier to rank. Intent dominates."""
    tokens = len(kw.split())
    length_score = min(tokens, 6) * 1.5          # cap runaway super-long phrases
    spec_score = 3.0 if tokens >= 4 else 0.0     # genuine long tail
    bonus = 2.0 if seed_bonus else 0.0
    return round(intent * 3 + length_score + spec_score + bonus, 2)


def tier(score_val: float) -> str:
    if score_val >= 45:
        return "A"
    if score_val >= 36:
        return "B"
    return "C"


def expand(seeds: list[str], modifiers: list[str], alphabet: bool,
           pause: float) -> dict[str, tuple[str, bool]]:
    """Collect {keyword: (via, is_direct_seed)} using multiple expansion passes."""
    found: dict[str, tuple[str, bool]] = {}

    def add(kw: str, via: str, direct: bool = False) -> None:
        kw = " ".join(kw.split()).lower()
        if kw and kw not in found:
            found[kw] = (via, direct)

    for seed in seeds:
        s = seed.strip().lower()
        if not s:
            continue
        # pass 1: raw seed
        for kw in suggest(s):
            add(kw, "seed", direct=True)
        time.sleep(pause)
        # pass 2: seed + modifiers
        for mod in modifiers:
            phrase = f"{s} {mod}".strip()
            for kw in suggest(phrase):
                add(kw, f"+{mod}")
            time.sleep(pause)
        # pass 3: alphabet soup on the stripping seed (biggest haul)
        if alphabet:
            for ch in "abcdefghijklmnopqrstuvwxyz":
                for kw in suggest(f"{s} {ch}"):
                    add(kw, "alphabet")
                time.sleep(pause)
    return found


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", required=True,
                    help="comma-separated seed terms")
    ap.add_argument("--modifiers",
                    default="vs,alternative,best,pricing,review,for,cost,worth",
                    help="comma-separated suffixes appended to each seed")
    ap.add_argument("--no-alphabet", action="store_true",
                    help="skip the a-z expansion pass (fewer requests)")
    ap.add_argument("--pause", type=float, default=0.15,
                    help="seconds between requests (be polite)")
    ap.add_argument("--top", type=int, default=60)
    ap.add_argument("--out", default=DEFAULT_OUT)
    args = ap.parse_args()

    seeds = [s for s in args.seeds.split(",") if s.strip()]
    modifiers = [m.strip() for m in args.modifiers.split(",") if m.strip()]
    print(f"mining {len(seeds)} seeds x {len(modifiers)} modifiers"
          f"{'' if args.no_alphabet else ' + alphabet soup'} …")

    found = expand(seeds, modifiers, not args.no_alphabet, args.pause)
    print(f"  collected {len(found)} raw suggestions")

    rows = []
    for kw, (via, direct) in found.items():
        intent, matched = intent_weight(kw)
        sc = score(kw, intent, direct)
        rows.append({
            "keyword": kw,
            "tokens": len(kw.split()),
            "intent": intent,
            "matched": matched,
            "score": sc,
            "tier": tier(sc),
            "via": via,
        })

    rows.sort(key=lambda r: (-r["score"], r["keyword"]))

    out = ROOT / args.out if not Path(args.out).is_absolute() else Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["tier", "keyword", "tokens",
                                          "intent", "matched", "score", "via"])
        w.writeheader()
        for r in rows[:args.top]:
            w.writerow({k: r[k] for k in w.fieldnames})

    print(f"  wrote {out.relative_to(ROOT)}  ({min(args.top, len(rows))} rows)")
    print("\n  top candidates:")
    for r in rows[:12]:
        print(f"   [{r['tier']}] {r['score']:>6}  {r['keyword']}")


if __name__ == "__main__":
    main()
