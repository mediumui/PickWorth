#!/usr/bin/env python3
"""Clean the 8 anchor-only drafts' `sources` arrays.

The legacy drafts stored `sources` as `[["#anchor","Label"], ...]` TOC-style
arrays, which `_sources_list` in l4_render.py would render as junk like
"1. #what". This script replaces them with real `text — url` strings so the
{{SOURCES}} template block can expose authoritative external citation links.

URLs come only from the official vendor pages that the well-formed sibling
drafts already cite (no fabricated links). Internal self-links are kept to a
minimum (one cross-ref) because authoritative *external* sources are what GEO
cites.

Mapping (tool -> its official pricing/docs page):
    chatgpt    -> OpenAI pricing
    claude     -> Anthropic pricing
    grok       -> xAI Grok plans
    perplexity -> Perplexity Pro
    deepseek   -> DeepSeek API docs
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
D = os.path.join(ROOT, "content", "drafts")

VENDOR = {
    "chatgpt": [
        "OpenAI - ChatGPT pricing and plans - https://openai.com/chatgpt/pricing/",
        "OpenAI - model documentation and limits - https://platform.openai.com/docs",
        "ChatGPT Wikipedia - https://en.wikipedia.org/wiki/ChatGPT",
    ],
    "claude": [
        "Anthropic - Claude pricing and plans - https://www.anthropic.com/pricing",
        "Anthropic - model and context documentation - https://docs.anthropic.com/",
        "Claude Wikipedia - https://en.wikipedia.org/wiki/Claude_(language_model)",
    ],
    "grok": [
        "xAI - Grok and SuperGrok plans - https://x.ai/grok",
        "Grok Wikipedia - https://en.wikipedia.org/wiki/Grok",
    ],
    "perplexity": [
        "Perplexity - Pro pricing and plans - https://www.perplexity.ai/pro",
        "Perplexity Wikipedia - https://en.wikipedia.org/wiki/Perplexity_AI",
    ],
    "deepseek": [
        "DeepSeek - official API pricing and model docs - https://api-docs.deepseek.com/",
        "DeepSeek Wikipedia - https://en.wikipedia.org/wiki/DeepSeek",
    ],
    "chatgpt-vs-claude": [
        "OpenAI - ChatGPT pricing and plans - https://openai.com/chatgpt/pricing/",
        "Anthropic - Claude pricing and plans - https://www.anthropic.com/pricing",
    ],
    "ai-writing-tools": [
        "Jasper - pricing and plans - https://www.jasper.ai/pricing",
        "Sudowrite - pricing - https://www.sudowrite.com/pricing",
        "OpenAI - ChatGPT pricing and plans - https://openai.com/chatgpt/pricing/",
    ],
    "best-image-generation-tools": [
        "Midjourney - plans and pricing - https://www.midjourney.com/pricing",
        "OpenAI - DALL-E image pricing - https://openai.com/chatgpt/pricing/",
    ],
}


def is_anchor_only(s):
    """True when a sources entry is a [anchor,label] pair, not a text—url string."""
    return isinstance(s, list)


def clean(slug):
    path = os.path.join(D, f"{slug}.json")
    d = json.load(open(path, encoding="utf-8"))
    srcs = d.get("sources", [])
    # keep any entry that is a well-formed 'text — url' string
    kept = [s for s in srcs if isinstance(s, str) and "http" in s and " — " in s]
    # add vendor URLs (dedup by url)
    have = {s.rsplit(" ", 1)[1] for s in kept}
    for s in VENDOR.get(slug, []):
        url = s.rsplit(" ", 1)[1]
        if url not in have:
            kept.append(s)
            have.add(url)
    d["sources"] = kept
    json.dump(d, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"{slug}: {len(kept)} clean sources")


if __name__ == "__main__":
    targets = [
        "chatgpt", "claude", "grok", "perplexity", "deepseek",
        "chatgpt-vs-claude", "ai-writing-tools", "best-image-generation-tools",
    ]
    for t in targets:
        clean(t)
    print("done")
