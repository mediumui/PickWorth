#!/usr/bin/env python3
"""Deterministically rewrite open-source-cursor-alternatives.json sources
into clean 'Name - GitHub - url' citation strings (one authoritative repo URL
per tool). Replaces the messy intermediate from clean_cursor_sources.py."""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
path = os.path.join(ROOT, "content", "drafts", "open-source-cursor-alternatives.json")
d = json.load(open(path, encoding="utf-8"))

MAPPING = {
    "https://github.com/cline/cline":
        "Cline - open-source AI coding agent - https://github.com/cline/cline",
    "https://github.com/zed-industries/zed":
        "Zed - high-performance native code editor - https://github.com/zed-industries/zed",
    "https://github.com/Aider-AI/aider":
        "Aider - AI pair programming in your terminal - https://github.com/Aider-AI/aider",
    "https://github.com/continuedev/continue":
        "Continue - open-source AI dev toolkit - https://github.com/continuedev/continue",
    "https://github.com/TabbyML/tabby":
        "Tabby - self-hosted AI coding assistant - https://github.com/TabbyML/tabby",
    "https://github.com/voideditor/void":
        "Void - open-source Cursor alternative - https://github.com/voideditor/void",
}

clean = []
for s in d.get("sources", []):
    if isinstance(s, str):
        url = s.rsplit(" ", 1)[-1].strip()
        if url in MAPPING:
            clean.append(MAPPING[url])
        elif "http" in s:
            clean.append(s)
    # lists were already converted to strings by the previous pass; skip lists
d["sources"] = clean
json.dump(d, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("open-source-cursor-alternatives final clean sources:")
for c in clean:
    print("   ", c)
