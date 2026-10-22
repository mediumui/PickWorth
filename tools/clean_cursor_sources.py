#!/usr/bin/env python3
"""Fix open-source-cursor-alternatives.json sources:
   - drop the 7 TOC-style [anchor,label] junk entries
   - convert the 6 malformed [github_url, "Name</a> — <a href=hn>..."]
     into clean 'Name - github repo - github_url' strings
     (the HN discussion link was tangled inside HTML; keep the repo URL as the
      authoritative citation, drop the stray HN fragment to avoid malformed markup)
"""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
path = os.path.join(ROOT, "content", "drafts", "open-source-cursor-alternatives.json")
d = json.load(open(path, encoding="utf-8"))

clean = []
for s in d.get("sources", []):
    if isinstance(s, list):
        first = s[0]
        if first.startswith("#"):
            continue  # TOC anchor, not a source
        # [github_url, "Name</a> - ..."] -> extract the tool name
        url = first
        text = s[1]
        # pull the tool name = leading word before the first '<'
        import re
        name = re.sub(r"<[^>]+>", "", text).strip()
        # name currently looks like 'Cline</a>...' cleaned -> 'Cline'
        label = name.split('"')[0].strip()
        # produce 'Name - open-source repo - url'
        clean.append(f"{label} - GitHub repository - {url}")
    elif isinstance(s, str) and "http" in s:
        clean.append(s)

d["sources"] = clean
json.dump(d, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("open-source-cursor-alternatives: now", len(clean), "clean sources")
for c in clean:
    print("   ", c)
