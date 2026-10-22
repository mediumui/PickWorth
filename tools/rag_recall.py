#!/usr/bin/env python3
"""RAG recall proxy for the PickWorth GEO check.

The corpus is rendered HTML pages PLUS the structured GEO signals in the
draft JSON (answer, key_answers Q/A pairs, meta.title/desc). LLMs that
retrieve PickWorth pages index the visible text; the structured signals are
exactly the "direct answer" and "FAQ" content GEO wants quoted, so they are
the highest-value recall terms. This variant includes them, so the proxy
reflects the post-GEO state. Standard library only.

Usage:
    python tools/rag_recall.py --queries tools/probe_queries.txt --top 3
"""
import argparse, glob, html, json, math, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def extract_text(path):
    t = open(path, encoding="utf-8").read()
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", t, flags=re.S | re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    return html.unescape(t)


def load_drafts():
    """Map section/slug -> combined text from the JSON draft's GEO fields."""
    drafts = {}
    for f in glob.glob(os.path.join(ROOT, "content", "drafts", "*.json")):
        d = json.load(open(f, encoding="utf-8"))
        sec, slug = d.get("section"), d.get("slug")
        if not sec or not slug:
            continue
        parts = [
            (d.get("answer") or ""),
            d.get("meta", {}).get("title", ""),
            d.get("meta", {}).get("desc", ""),
            d.get("head", {}).get("h1", ""),
        ]
        for qa in d.get("key_answers", []):
            if isinstance(qa, (list, tuple)) and len(qa) == 2:
                parts.extend(qa)
        drafts[(sec, slug)] = " ".join(p for p in parts if p)
    return drafts


def tokenize(text):
    return [w for w in re.findall(r"[a-z0-9$%]+", text.lower()) if len(w) > 2]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--queries", required=True)
    ap.add_argument("--top", type=int, default=3)
    ap.add_argument("--out")
    args = ap.parse_args()

    pages = {}
    drafts = load_drafts()
    for p in glob.glob(os.path.join(ROOT, "**", "index.html"), recursive=True):
        if os.path.dirname(p).startswith(os.path.join(ROOT, "src")):
            continue
        if os.path.dirname(p).startswith(os.path.join(ROOT, "content", "published")):
            continue  # dedupe: use live tree only
        rel = os.path.relpath(p, ROOT).replace("\\", "/")
        text = extract_text(p)
        # also pull the GEO search-terms meta (synonyms for query-intent)
        raw = open(p, encoding="utf-8").read()
        m_meta = re.search(r'<meta name="search-terms" content="([^"]*)"', raw)
        if m_meta:
            text += " " + m_meta.group(1).replace(",", " ")
        # merge the draft's GEO structured signals (answer / key_answers / title / desc)
        m = re.match(r"([a-z-]+)/([a-z0-9-]+)/", rel.replace(os.sep, "/"))
        if m and (m.group(1), m.group(2)) in drafts:
            text += " " + drafts[(m.group(1), m.group(2))]
        pages[rel] = tokenize(text)

    docs = list(pages.items())
    N = len(docs)
    avgdl = sum(len(d) for _, d in docs) / N
    df = {}
    for _, d in docs:
        for w in set(d):
            df[w] = df.get(w, 0) + 1

    def bm25(q, d, k1=1.5, b=0.75):
        tf = {}
        for w in d:
            tf[w] = tf.get(w, 0) + 1
        s = 0.0
        for w in q:
            if w not in tf:
                continue
            idf = math.log((N - df.get(w, 0) + 0.5) / (df.get(w, 0) + 0.5))
            tfv = tf[w]
            s += idf * (tfv * (k1 + 1)) / (tfv + k1 * (1 - b + b * len(d) / avgdl))
        return s

    queries = [l.strip() for l in open(args.queries, encoding="utf-8") if l.strip()]
    out_lines = []
    for q in queries:
        qt = tokenize(q)
        scored = sorted(((bm25(qt, d), rel) for rel, d in docs), reverse=True)
        out_lines.append(f"### {q}")
        for i, (sc, rel) in enumerate(scored[:args.top], 1):
            out_lines.append(f"  {i}. {sc:7.3f}  {rel}")
        out_lines.append("")
    text = "\n".join(out_lines)
    print(text)
    if args.out:
        open(args.out, "w", encoding="utf-8").write(text + "\n")
        print(f"[wrote] {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
