#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
probe_suggest.py — verify Google Autosuggest returns usable keyword data.

Cheap/free alternative to Kwinside for long-tail discovery: no API key,
no daily cap, real autocomplete straight from Google.
"""
import json
import ssl
import urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def suggest(q: str) -> list[str]:
    url = ("https://suggestqueries.google.com/complete/search"
           f"?client=firefox&hl=en&gl=us&q={urllib.parse.quote(q)}")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=15, context=CTX) as r:
        raw = r.read().decode("utf-8", "replace")
    return json.loads(raw)[1]


if __name__ == "__main__":
    import urllib.parse
    for seed in ["best ai writing tool", "chatgpt vs claude", "ai tool for"]:
        print(f"\n--- seed: {seed} ---")
        try:
            for i, kw in enumerate(suggest(seed), 1):
                print(f"  {i:2}. {kw}")
        except Exception as e:  # noqa: BLE001
            print("  ERR", e)
