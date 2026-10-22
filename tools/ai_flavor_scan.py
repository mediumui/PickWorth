#!/usr/bin/env python3
"""Scan content/drafts/*.json for AI-flavored phrases and report hits."""
import json, re, glob

patterns = [
    ("worth-noting", r"it\s+is\s+worth\s+noting"),
    ("fast-paced", r"in\s+(today'?s\s+)?fast[- ]paced"),
    ("important-note", r"it'?s\s+important\s+to\s+(note|remember|mention)"),
    ("crucial-role", r"plays?\s+a\s+(crucial|vital|key|pivotal)\s+role"),
    ("myriad", r"a\s+myriad\s+of"),
    ("leverage", r"\bleverag(e|es|ed|ing)\b"),
    ("seamless", r"seamless(?:ly)?"),
    ("at-its-core", r"at\s+its\s+core"),
    ("in-essence", r"in\s+essence"),
    ("ultimately", r"\bultimately\b"),
    ("that-makes-it", r"that'?s\s+what\s+(makes|sets|gives)"),
    ("realm-of", r"the\s+(realm|landscape|world|era)\s+of"),
    ("delve", r"\bdelv(e|es|ed|ing)\b"),
    ("dive-deep", r"dive\s+(into|deep|deeper)"),
    ("not-only", r"not\s+only\s+(,|\s)"),
    ("moreover", r"\bmoreover\b"),
    ("furthermore", r"\bfurthermore\b"),
    ("additionally", r"\badditionally\b"),
    ("no-secret", r"it'?s\s+no\s+(secret|surprise|question)"),
    ("remarkable", r"\bremarkable(?:ly)?\b"),
    ("groundbreaking", r"\bgroundbreaking\b"),
    ("cutting-edge", r"cutting[- ]edge"),
    ("revolutionize", r"revoluti(ze|s|sed|zing)"),
    ("transformative", r"\btransformative\b"),
    ("harness", r"\bharn(e|es|essed|essing)\b"),
    ("robust", r"\brobust\b"),
    ("sophisticated", r"\bsophisticated\b"),
    ("effortless", r"effortless(?:ly)?"),
    ("crucial", r"\bcrucial\b"),
    ("vital", r"\bvital\b"),
    ("in-conclusion", r"in\s+(conclusion|summary)"),
    ("it-well-know", r"as\s+(it|well)\s+is\s+known"),
    ("today-s-world", r"today'?s\s+(world|landscape|era)"),
    ("ever-evolving", r"ever[- ]evolving"),
    ("in-today-s", r"in\s+today'?s\s+(fast|dynamic|ever|rapidly)"),
    ("one-cannot", r"one\s+cannot\s+(ignore|overlook|deny)"),
    ("it-clear", r"it\s+is\s+clear\s+that"),
    ("this-matters", r"this\s+matters\s+(because|as|when)"),
    ("in-other-words", r"in\s+other\s+words"),
    ("needless-say", r"needless\s+to\s+say"),
    ("goes-say", r"needless\s+to\s+say|without\s+a\s+shred"),
]

root = glob.glob("content/drafts/*.json")
total_hits = {}
total_count = 0
for f in sorted(root):
    d = json.load(open(f))
    slug = d["slug"]
    text = " ".join(
        [
            d.get("answer", ""),
            json.dumps(d.get("key_answers", []), ensure_ascii=False),
            d.get("body", ""),
            d.get("verdict", ""),
        ]
    )
    hits = []
    for name, pat in patterns:
        matches = re.findall(pat, text, re.IGNORECASE)
        if matches:
            hits.append((name, len(matches)))
    if hits:
        total_hits[slug] = hits
        total_count += len(hits)

print(f"Scanned {len(root)} drafts, found {total_count} AI-flavor hits across {len(total_hits)} files.\n")
for slug, hits in total_hits.items():
    desc = ", ".join(f"{n} x{c}" for n, c in hits)
    print(f"  {slug:42s}  {desc}")
