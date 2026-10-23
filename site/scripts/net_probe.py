#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
net_probe.py — check which research sources the sandbox can actually reach.

Article generation depends on fetching real sources, so before writing anything
we need to know what is reachable. Prints a pass/fail table per host.

Run from anywhere:  python tools/net_probe.py
"""
import json
import os
import ssl
import urllib.error
import urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

TARGETS = [
    # free keyword sources (Kwinside fallback)
    ("google-suggest", "https://suggestqueries.google.com/complete/search?client=firefox&q=best+ai+writing+tool"),
    ("bing-suggest",   "https://www.bing.com/AS/Suggestions?pqy=best+ai+writing+tool&cp=1&qry=best+ai+writing+tool"),
    ("duckduckgo-api", "https://api.duckduckgo.com/?q=chatgpt&format=json&no_html=1"),
    # official sources
    ("openai-home",    "https://openai.com/index/chatgpt-pricing/"),
    ("anthropic-home", "https://www.anthropic.com/pricing"),
    # third-party review sources
    ("pcmag",          "https://www.pcmag.com/reviews/chatgpt"),
    ("techradar",      "https://www.techradar.com/reviews/chatgpt"),
    ("zdnet",          "https://www.zdnet.com/article/chatgpt-review/"),
    ("tomsguide",      "https://www.tomsguide.com/reviews/chatgpt"),
    # general reachability
    ("wikipedia",      "https://en.wikipedia.org/wiki/Artificial_intelligence"),
]

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def probe(name: str, url: str, timeout: int = 12) -> tuple[str, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
            body = r.read()
            return f"{r.status} OK", f"{len(body)} bytes"
    except urllib.error.HTTPError as e:
        return f"HTTP {e.code}", ""
    except Exception as e:                                  # noqa: BLE001
        return "FAIL", type(e).__name__ + ": " + str(e)[:60]


def main() -> None:
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy") or "(none)"
    print(f"proxy={proxy}\n")
    width = max(len(n) for n, _ in TARGETS)
    ok_hosts: list[str] = []
    for name, url in TARGETS:
        status, extra = probe(name, url)
        flag = "PASS" if status.startswith("2") else "    "
        if flag == "PASS":
            ok_hosts.append(name)
        print(f"  {flag} {name.ljust(width)}  {status.ljust(10)} {extra}")
    print(f"\nreachable: {len(ok_hosts)}/{len(TARGETS)} -> {', '.join(ok_hosts) or 'none'}")


if __name__ == "__main__":
    main()
