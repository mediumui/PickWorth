#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
probe_sources.py — find which research sources actually deliver usable text.

Third-party review sites mostly bot-block us, so this probes a wider spread
(official docs, open APIs, aggregators) and reports how many characters of
real text each one yields.
"""
import ssl
import urllib.error
import urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

TARGETS = [
    ("hn-algolia",     "https://hn.algolia.com/api/v1/search?query=Claude%20vs%20ChatGPT&hitsPerPage=20"),
    ("reddit-search",  "https://www.reddit.com/search.json?q=chatgpt%20vs%20claude&limit=10"),
    ("openlibrary",    "https://openlibrary.org/search.json?q=ai&limit=3"),
    ("anthropic-pricing", "https://www.anthropic.com/pricing"),
    ("anthropic-docs", "https://docs.anthropic.com/en/docs/welcome"),
    ("platform-openai", "https://platform.openai.com/docs/pricing"),
    ("github-api",     "https://api.github.com/search/repositories?q=llm&per_page=3"),
    ("rss-techcrunch", "https://techcrunch.com/feed/"),
    ("rss-arstechnica","https://arstechnica.com/feed/"),
    ("wikipedia-api",  "https://en.wikipedia.org/w/api.php?action=query&prop=extracts&explaintext=1&format=json&titles=ChatGPT"),
    ("semanticscholar","https://api.semanticscholar.org/graph/v1/paper/search?query=large+language+model&limit=3"),
    ("crossref",       "https://api.crossref.org/works?query=llm&rows=2"),
]


def probe(name: str, url: str, timeout: int = 15) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
            body = r.read()
            sample = body[:400].decode("utf-8", "replace").replace("\n", " ")
            print(f"  PASS {name.ljust(20)} {r.status}  {len(body):>8} bytes")
            print(f"       {sample[:180]}")
    except urllib.error.HTTPError as e:
        print(f"       {name.ljust(20)} HTTP {e.code}")
    except Exception as e:  # noqa: BLE001
        print(f"       {name.ljust(20)} FAIL {type(e).__name__}: {str(e)[:50]}")


if __name__ == "__main__":
    for n, u in TARGETS:
        probe(n, u)
