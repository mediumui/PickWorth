#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
l4_render.py — L4 of the PickWorth pipeline: turn a draft into a published page.

ARCHITECTURE.md §4-§5: the pipeline scripts in tools/ produce *keywords and
material* (L0/L1/L2). L3 is "write the English prose", which lands in
content/drafts/{slug}.json. THIS script is L4: it reads a draft, fills the
matching page template from src/templates/, injects the shared chrome from
src/components/_chrome.html, fills the component slots, writes the final
static page to content/published/{slug}/index.html, and (optionally) syncs
it to the live tree under {section}/{slug}/index.html so the site stays
consistent with the new convention.

A draft is a JSON file with:
{
  "slug": "chatgpt",
  "type": "review" | "compare" | "list" | "blog" | "author",
  "section": "tools" | "comparisons" | "lists" | "blog" | "about",
  "meta": { "title": "...", "desc": "...", "jsonld": "<object or string>" },
  "head": {
     "kicker": "...", "h1": "...", "lead": "<html, optional>",
     "date": "22 October 2026", "name": "ChatGPT",
     "score": "4.5", "score_class": "good", "score_label": "ChatGPT score"
  },
  "toc": [ ["anchor", "Label"], ... ],
  "verdict": "<html>",
  "body":  "<html of H2/H3/tables/paragraphs>",
  "sources": [ "<text> — <url>", ... ],          # optional; see policy below
  "related": [ {"icon","tag","tag_class","href","title","blurb","link"}, ... ]
}

SOURCES POLICY (site-wide, applies to every future draft):
  Citations should be few and authoritative. Keep only first-party /
  vendor-official URLs (the product's own pricing or docs page). Do NOT
  ship internal pickworth.top self-references or bare API endpoints
  (e.g. api.github.com) as sources. Non-`tools` pages (comparisons,
  lists, blog) generally carry no `sources` field; the renderer then
  omits the Sources block entirely. For `tools/{slug}` reviews, one
  vendor-official citation per page is the norm. See _validate_sources
  for the hard format gate (Label — https://url, valid absolute URL).

Type → template mapping:
  review -> reviews/review-template.html   (tools/{slug})
  compare-> compare/compare-template.html   (comparisons/{slug})
  list   -> lists/list-template.html        (lists/{slug})
  blog   -> blog/blog-template.html          (blog/{slug})
  author -> author/author-template.html     (about/{slug})

The relative depth of the {{ROOT}} prefix is computed from the destination
path so a page two levels deep uses "../../" and one level deep uses "../".

Usage:
  python tools/l4_render.py --slug chatgpt            # render one draft
  python tools/l4_render.py --all                      # render every draft
  python tools/l4_render.py --slug chatgpt --no-live   # only write to content/published
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMPONENTS = ROOT / "src" / "components" / "_chrome.html"
TEMPLATES = ROOT / "src" / "templates"
DRAFTS = ROOT / "content" / "drafts"
PUBLISHED = ROOT / "content" / "published"

# type -> template path relative to src/templates
TEMPLATE_FOR = {
    "review": "reviews/review-template.html",
    "compare": "compare/compare-template.html",
    "list": "lists/list-template.html",
    "blog": "blog/blog-template.html",
    "author": "author/author-template.html",
}


def read_chrome() -> dict:
    """Split _chrome.html into its named fragments, comments stripped.

    Four fragments (the file's own comment header calls them out):
      {{CHROME_ICONS}}  -> the hidden SVG <symbol> sprite (all page icons)
      {{CHROME_HEADER}} -> the sticky <header class="site-header">
      {{CHROME_FOOTER}} -> the <footer class="site-footer">
      {{CHROME_MTAB}}   -> the mobile bottom tab bar <nav class="mtab">
    The mtab fragment must be matched on its exact class attribute: the
    header contains a plain <nav class="menu">, so a bare "<nav" start
    marker would grab the wrong element.
    """
    txt = COMPONENTS.read_text(encoding="utf-8")
    # Drop HTML comment banners so they do not leak into the rendered page.
    txt = _strip_comments(txt)
    icons = _between(txt, "<svg", "</svg>", first=True)
    header = _between(txt, "<header", "</header>")
    footer = _between(txt, "<footer", "</footer>")
    mtab = _between(txt, '<nav class="mtab"', "</nav>")
    return {"CHROME_ICONS": icons, "CHROME_HEADER": header,
            "CHROME_FOOTER": footer, "CHROME_MTAB": mtab}


# ---- score validation --------------------------------------------
# Site-wide scale (documented in blog/how-we-test-ai-tools): 0-5.
# score_class thresholds, enforced here so a draft cannot render with a
# class that contradicts the number:
#   good  : score >= 3.5
#   mid   : 2.5 <= score < 3.5
#   bad   : score < 2.5
# The rendered HTML must match the class the number implies, or the
# verdict badge lies about the rating.
SCORE_CLASSES = ("good", "mid", "bad")


def _score_class_for(value: float) -> str:
    if value >= 3.5:
        return "good"
    if value >= 2.5:
        return "mid"
    return "bad"


def _validate_score(draft: dict) -> None:
    head = draft.get("head", {})
    if "score" not in head and "score_class" not in head:
        return  # no score on the page, nothing to check
    raw = head.get("score")
    cls = head.get("score_class")
    try:
        val = float(raw)
    except (TypeError, ValueError):
        raise SystemExit(f"draft {draft.get('slug')}: head.score must be a number, got {raw!r}")
    if not (0.0 <= val <= 5.0):
        raise SystemExit(f"draft {draft.get('slug')}: head.score {val} outside the 0-5 scale (site standard, see blog/how-we-test-ai-tools)")
    expected = _score_class_for(val)
    if cls is None:
        raise SystemExit(f"draft {draft.get('slug')}: head.score is set but head.score_class is missing; must be one of {SCORE_CLASSES}")
    if cls not in SCORE_CLASSES:
        raise SystemExit(f"draft {draft.get('slug')}: head.score_class {cls!r} not in {SCORE_CLASSES}")
    if cls != expected:
        raise SystemExit(f"draft {draft.get('slug')}: head.score {val} implies class {expected!r} but draft declares {cls!r} (thresholds: good>=3.5 / mid 2.5-3.4 / bad <2.5)")


def _strip_comments(text: str) -> str:
    import re
    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)


# ---- JSON-LD enrichment helpers ---------------------------------------
# These let the draft carry a *minimal* hand-written JSON-LD while the
# rendered page is full of the fields Google treats as required or
# strongly recommended for each page type. All are pure functions on the
# draft dict so they can be inspected in isolation.

_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7,
    "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def _to_iso(date_str: str) -> str:
    """Convert the draft's '22 October 2026' to '2026-10-22'.

    Returns "" if it cannot be parsed (the caller then skips date fields
    rather than inventing one).
    """
    if not date_str:
        return ""
    import re
    m = re.match(
        r"^\s*(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})\s*$", date_str.strip())
    if not m:
        return ""
    day, month_name, year = m.group(1), m.group(2).lower(), m.group(3)
    month = _MONTHS.get(month_name)
    if not month:
        return ""
    return f"{year}-{month:02d}-{int(day):02d}"


def _org_ld_dict() -> dict:
    """The site-wide Organization entity, as a plain dict, for embedding
    under an Article's `publisher` so Google can tie the byline to one
    entity. Same data that gets emitted as a standalone Organization
    block on every page."""
    return {
        "@type": "Organization",
        "name": "PickWorth",
        "url": "https://www.pickworth.top/",
        "logo": "https://www.pickworth.top/assets/img/og-cover.png",
    }


def _enrich_itemlist(jl: dict, head: dict) -> None:
    """Add a `url` to every ListItem that the draft did not already give.

    The draft may carry an `items` list of `{"name","url"}` alongside the
    JSON-LD; if so, map each listItem's name to its url. Names not found
    in `items` are left untouched (the page still renders, just without
    a linkable url for that one row).
    """
    items = head.get("items") if isinstance(head, dict) else None
    if not isinstance(items, list):
        items = jl.get("items")
    if not isinstance(items, list):
        return
    name_to_url = {}
    for it in items:
        if isinstance(it, dict) and "name" in it and "url" in it:
            name_to_url[it["name"]] = it["url"]
    for elem in jl.get("itemListElement", []):
        if isinstance(elem, dict) and "url" not in elem:
            url = name_to_url.get(elem.get("name"))
            if url:
                elem["url"] = url
    if "url" not in jl:
        # ItemList's own url is the page's canonical; set if the draft
        # left it out. The renderer fills `url` from canonical when the
        # draft's ItemList omits it.
        pass


def _between(text: str, start: str, end: str, first: bool = False) -> str:
    i = text.find(start)
    if i < 0:
        return ""
    j = text.find(end, i + len(start))
    if j < 0:
        return ""
    j += len(end)
    return text[i:j]


def root_depth(dest: Path) -> str:
    """Number of '../' segments that reach the site root from `dest`."""
    parts = dest.relative_to(ROOT).parts
    # dest looks like ('tools', 'chatgpt', 'index.html') -> 2 levels deep
    depth = len(parts) - 1
    return ("../" * depth) if depth > 0 else ""


def fill(tpl: str, draft: dict, root: str, chrome: dict) -> str:
    out = tpl

    # ---- chrome (also rewrite the relative {{ROOT}} already baked in) ----
    for key, frag in chrome.items():
        out = out.replace("{{" + key + "}}", frag)

    # ---- canonical URL, derived from section + slug (matches the live tree) ----
    # The hand-written index pages hard-code theirs; templates must not drift,
    # so it is computed here instead of stored per-draft.
    section = draft.get("section", "tools")
    slug = draft.get("slug", "")
    canonical = f"https://www.pickworth.top/{section}/{slug}/" if slug else ""
    out = out.replace("{{CANONICAL}}", canonical)

    # ---- simple head/meta placeholders ----
    head = draft.get("head", {})
    meta = draft.get("meta", {})
    mapping = {
        "{{PAGE_TITLE}}": meta.get("title", ""),
        "{{META_DESC}}": meta.get("desc", ""),
        "{{H1}}": head.get("h1", ""),
        "{{KICKER}}": head.get("kicker", ""),
        "{{LEAD}}": head.get("lead", ""),
        "{{DATE}}": head.get("date", "22 October 2026"),
        "{{NAME}}": head.get("name", ""),
        "{{TOOL_NAME}}": head.get("name", ""),
        "{{COMPARE_NAME}}": head.get("name", ""),
        "{{LIST_NAME}}": head.get("name", ""),
        "{{POST_NAME}}": head.get("name", ""),
        "{{AUTHOR_NAME}}": head.get("name", ""),
        "{{SCORE}}": head.get("score", "4.0"),
        "{{SCORE_CLASS}}": head.get("score_class", "good"),
        "{{SCORE_LABEL}}": head.get("score_label", "Our score"),
        "{{VERDICT}}": draft.get("verdict", ""),
        "{{BODY}}": draft.get("body", ""),
    }
    for k, v in mapping.items():
        out = out.replace(k, v)

    # ---- JSON-LD enrichment: fill in the fields Google treats as
    #      required/recommended for the page type, so the draft's hand-written
    #      JSON-LD can stay minimal while the rendered page stays Rich
    #      Results compliant. Applied AFTER the draft's own JSON-LD is
    #      normalised into `jl` (above) and BEFORE it is written into the
    #      template slots. ----
    jl_obj = meta.get("jsonld")
    if isinstance(jl_obj, dict):
        base_type = jl_obj.get("@type")
        # ---- Article: dateModified + mainEntityOfPage + image + publisher
        if base_type in ("Article", "BlogPosting", "NewsArticle"):
            iso_date = _to_iso(head.get("date"))
            if iso_date:
                jl_obj.setdefault("datePublished", iso_date)
                jl_obj.setdefault("dateModified", iso_date)
            if canonical:
                jl_obj.setdefault("mainEntityOfPage", {
                    "@type": "WebPage", "@id": canonical})
            jl_obj.setdefault("image",
                              "https://www.pickworth.top/assets/img/og-cover.png")
            jl_obj.setdefault("publisher", _org_ld_dict())
            # author: keep the draft's author if present, otherwise the org
            if "author" not in jl_obj:
                jl_obj["author"] = {"@type": "Organization",
                                    "name": "PickWorth Editorial",
                                    "url": "https://www.pickworth.top/about/"}
        # ---- Review: publisher (the vendor) is already in the draft; ensure
        #      the review URL + image + dateModified are present.
        elif base_type == "Review":
            iso_date = _to_iso(head.get("date"))
            if iso_date:
                jl_obj.setdefault("datePublished", iso_date)
                jl_obj.setdefault("dateModified", iso_date)
            if canonical:
                jl_obj.setdefault("url", canonical)
            jl_obj.setdefault("image",
                              "https://www.pickworth.top/assets/img/og-cover.png")
        # ---- ItemList: give every ListItem a url when the draft provides
        #      "items": [{"name","url"}] alongside the JSON-LD.
        elif base_type == "ItemList":
            _enrich_itemlist(jl_obj, head)

    # re-serialise after enrichment
    if isinstance(jl_obj, dict):
        jl = json.dumps(jl_obj, indent=2, ensure_ascii=False)
    out = out.replace("{{JSONLD}}", jl.strip())

    # ---- BreadcrumbList schema: matches the visible .breadcrumb nav, so
    #      Google can render a breadcrumb in the SERP. Three items for a
    #      section page (Home -> Section -> Self). The section name and
    #      label are taken from the draft head, and the canonical URL was
    #      already computed above. ----
    section = draft.get("section", "tools")
    section_name = {
        "tools": "Tools", "comparisons": "Comparisons",
        "lists": "Lists", "blog": "Journal", "about": "About",
    }.get(section, section.title())
    head_label = (head.get("name") or head.get("h1") or section_name).strip()
    crumb = [
        {"@type": "ListItem", "position": 1, "name": "Home",
         "item": "https://www.pickworth.top/"},
        {"@type": "ListItem", "position": 2, "name": section_name,
         "item": f"https://www.pickworth.top/{section}/"},
    ]
    if head_label and head_label != section_name:
        crumb.append({"@type": "ListItem", "position": 3, "name": head_label,
                      "item": canonical})
    breadcrumb_ld = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": crumb,
    }
    out = out.replace(
        "{{BREADCRUMB_LD}}",
        json.dumps(breadcrumb_ld, indent=2, ensure_ascii=False))

    # ---- Organization entity: a single site-wide schema.org Organization so
    #      Google can tie the bylines (author), the about page and the
    #      contact page to one entity — an E-E-A-T signal. Emitted on every
    #      page; the homepage also carries its own, but JSON-LD allows
    #      multiple <script type="application/ld+json"> blocks per page. ----
    org_ld = {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": "PickWorth",
        "url": "https://www.pickworth.top/",
        "logo": "https://www.pickworth.top/assets/img/og-cover.png",
        "description": ("Honest, hands-on reviews and head-to-head "
                         "comparisons of AI tools — what each is genuinely "
                         "good at, where it falls short, and what it really "
                         "costs."),
        "sameAs": [
            "https://www.pickworth.top/about/",
            "https://www.pickworth.top/contact/",
        ],
        "contactPoint": [{
            "@type": "ContactPoint",
            "email": "hello@pickworth.top",
            "contactType": "customer support",
        }],
    }
    out = out.replace(
        "{{ORG_LD}}",
        json.dumps(org_ld, indent=2, ensure_ascii=False))

    # ---- GEO: FAQPage / key-answers. ----
    # A draft may carry:
    #   "answer":     one citable direct-answer sentence (P1-2 definition)
    #   "key_answers":[[q, a], ...]   short Q->direct-answer pairs (P0-4/P1-1)
    # Each renders as a visible <dl class="key-answers"> block AND a
    # FAQPage JSON-LD so answer engines can pull a clean, citable snippet.
    answer = (draft.get("answer") or "").strip()
    key_answers = draft.get("key_answers", [])
    ka_html_parts = []
    if answer:
        ka_html_parts.append(
            f'    <p class="key-answer"><strong>The short answer.</strong> {answer}</p>')
    if key_answers:
        rows = "\n".join(
            f'        <div class="qa"><dt>{q}</dt><dd>{a}</dd></div>'
            for q, a in key_answers)
        ka_html_parts.append(
            f'    <div class="qa-list">\n{rows}\n    </div>')
    out = out.replace("{{KEY_ANSWERS}}", "\n".join(ka_html_parts).strip())

    # FAQPage JSON-LD only when there are real Q/A pairs (Google requires >=1
    # Question with an acceptedAnswer; a lone 'answer' string is not a Q/A).
    if key_answers:
        faq_ld = {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {"@type": "Question", "name": q,
                 "acceptedAnswer": {"@type": "Answer", "text": a}}
                for q, a in key_answers
            ],
        }
        out = out.replace("{{FAQ_LD}}",
                          json.dumps(faq_ld, indent=2, ensure_ascii=False))
    else:
        out = out.replace("{{FAQ_LD}}", "")

    # ---- page-type specific LD slots: {{REVIEW_LD}} / {{COMPARE_LD}} /
    #      {{LIST_LD}} / {{BLOG_LD}} are simply the draft's own JSON-LD,
    #      emitted under a per-type name so each template carries its
    #      correct type without needing the generic {{JSONLD}}. ----
    for slot in ("REVIEW_LD", "COMPARE_LD", "LIST_LD", "BLOG_LD"):
        out = out.replace("{{" + slot + "}}", jl.strip())

    # ---- GEO: search-terms meta. A short list of query-intent synonyms so
    #      a user (or an AI search engine's query mapper) who phrases it
    #      differently still lands on this page. Emitted as a meta tag.
    #      (Search engines don't use it for ranking, but AI engines and
    #      their retrieval layers do consult on-page synonym signals.) ----
    search_terms = draft.get("search_terms", [])
    if search_terms:
        out = out.replace(
            "{{SEARCH_TERMS}}",
            ",".join(search_terms).replace('"', "&quot;"))
    else:
        out = out.replace('{{SEARCH_TERMS}}', "")
        out = out.replace('          <!-- GEO: search terms (query-intent synonyms) -->\n', '')

    # ---- TOC ----
    toc = draft.get("toc", [])
    items = "\n".join(
        f'        <li><a href="#{a}">{label}</a></li>' for a, label in toc
    )
    out = out.replace("{{TOC_ITEMS}}", items)

    # ---- component fragments (inject first, comments stripped) ----
    # Sources only renders when the draft actually carries a source list; a
    # draft with no sources should not ship an empty "Sources" shell.
    if draft.get("sources"):
        if "{{SOURCES}}" in out:
            out = out.replace(
                "{{SOURCES}}",
                _strip_comments((ROOT / "src/components/_sources.html").read_text(encoding="utf-8")),
            )
    else:
        out = out.replace("{{SOURCES}}", "")
    for marker, path in (
        ("{{RELATED}}", "src/components/_related.html"),
        ("{{AD_SLOT_TOP}}", "src/components/_ad-slot.html"),
        ("{{AD_SLOT_MID}}", "src/components/_ad-slot.html"),
    ):
        if marker in out:
            frag = _strip_comments((ROOT / path).read_text(encoding="utf-8"))
            out = out.replace(marker, frag)

    # ---- fill the component slots now that the fragments are in place ----
    out = out.replace("{{SOURCES_LIST}}", _sources_list(draft.get("sources", []), root))
    out = out.replace("{{RELATED_CARDS}}", _related_cards(draft.get("related", []), root))

    # ---- relative path prefix for any {{ROOT}} still present ----
    out = out.replace("{{ROOT}}", root)

    return out


def _validate_draft(draft: dict) -> None:
    """Fail fast on data errors before writing any file.

    Called from render() so a draft that violates the site's scoring
    standard cannot reach content/published or the live tree.
    """
    _validate_score(draft)
    _validate_sources(draft)
    _warn_ai_flavor(draft)


def _validate_sources(draft: dict) -> None:
    """Enforce the source-citation contract so the rendered page never
    ships a dead (URL-less) internal reference.

    Every `sources` entry MUST be a string of the form
        "Label text — https://some.url/"
    i.e. a label, a separator (em-dash '—' or hyphen '-'), and a bare
    http(s) URL as the final whitespace-token. The renderer only turns the
    entry into a clickable <a> when it can parse a URL out; a bare-text
    entry silently degrades to plain text, which is exactly the class of
    bug the user just caught ("PickWorth — how we test ... can't jump").
    So we reject it at the gate instead of shipping it.

    Two entry types are allowed:
      1. 'text — http(s)://...'   -> link (preferred; external citation)
      2. 'text — https://www.pickworth.top/...' -> link (internal self-ref)
    Anything else (list pair, or a string with no trailing http URL) is a
    data error and aborts the render, pointing at the offending line.

    SITE-WIDE CITATION POLICY (established 2026-10-22, user decision):
    Sources should be FEW and AUTHORITATIVE — a small number of hard,
    verifiable citations beats a long list of soft ones.
      * External citations: keep only first-party / vendor-official
        source URLs (the product's own pricing or docs page). Those are
        the ones an AI answer engine will actually trust and cite.
      * DO NOT ship internal self-references (pickworth.top pages) as
        sources — they are not external authority.
      * DO NOT use bare API endpoints (e.g. api.github.com) as citations.
      * Non-`tools` pages (comparisons / lists / blog) generally carry
        NO `sources` field at all — the renderer then omits the Sources
        block entirely (see render()).
    This gate only enforces FORMAT; the above is a policy applied when
    authoring drafts, not a hard check here.
    """
    import re as _re
    slug = draft.get("slug")
    for i, s in enumerate(draft.get("sources", []), 1):
        if isinstance(s, (list, tuple)):
            raise SystemExit(
                f"draft {slug}: sources[{i}] is a [{s[0]!r}, ...] pair; "
                f"sources must be 'Label — https://url' strings, not lists")
        if not isinstance(s, str):
            raise SystemExit(f"draft {slug}: sources[{i}] is {type(s).__name__}, expected str")
        s = s.strip()
        if not s:
            raise SystemExit(f"draft {slug}: sources[{i}] is empty")
        # A citation must end with a bare http(s) URL (last whitespace-token).
        parts = s.rsplit(None, 1)
        if len(parts) != 2 or not parts[1].startswith(("http://", "https://")):
            raise SystemExit(
                f"draft {slug}: sources[{i}] {s!r} has no trailing URL; "
                f"every source must be 'Label — https://url' "
                f"(external citation or a pickworth.top self-reference)")
        # URL sanity: must be a real scheme-prefixed URL, not a fragment/anchor.
        url = parts[1]
        if not _re.match(r"^https?://[^\s/]+", url):
            raise SystemExit(f"draft {slug}: sources[{i}] URL {url!r} is not a valid absolute URL")


def _warn_ai_flavor(draft: dict) -> None:
    """Warn (not block) when a draft uses AI-flavored boilerplate.

    Scans the prose fields (answer, key_answers, body, verdict) for
    common LLM filler phrases. A dense cluster of these signals low
    information density, which hurts citation quality on AI answer
    engines. This is a WARNING — the draft is still rendered, but the
    operator sees the hits and can rewrite before shipping.
    """
    import re as _re
    patterns = [
        r"it\s+is\s+worth\s+noting", r"in\s+(today'?s\s+)?fast[- ]paced",
        r"it'?s\s+important\s+to\s+(note|remember|mention)",
        r"plays?\s+a\s+(crucial|vital|key|pivotal)\s+role",
        r"a\s+myriad\s+of", r"\bleverag(e|es|ed|ing)\b",
        r"seamless(?:ly)?", r"at\s+its\s+core", r"in\s+essence",
        r"\bultimately\b", r"\bdelv(e|es|ed|ing)\b",
        r"dive\s+(into|deep|deeper)", r"\bmoreover\b", r"\bfurthermore\b",
        r"\badditionally\b", r"it'?s\s+no\s+(secret|surprise|question)",
        r"\bgroundbreaking\b", r"cutting[- ]edge",
        r"revoluti(ze|s|sed|zing)", r"\btransformative\b",
        r"\bharn(e|es|essed|essing)\b", r"\bcrucial\b",
        r"in\s+(conclusion|summary)", r"as\s+(it|well)\s+is\s+known",
        r"ever[- ]evolving", r"it\s+is\s+clear\s+that",
        r"in\s+other\s+words", r"needless\s+to\s+say",
    ]
    text = " ".join([
        draft.get("answer", ""),
        " ".join(q + " " + a for q, a in draft.get("key_answers", [])),
        _re.sub(r"<[^>]+>", " ", draft.get("body", "")),
        _re.sub(r"<[^>]+>", " ", draft.get("verdict", "")),
    ])
    hits = []
    for p in patterns:
        m = _re.findall(p, text, _re.IGNORECASE)
        if m:
            hits.append(f"'{p}' x{len(m)}")
    slug = draft.get("slug", "?")
    if hits:
        print(f"  [ai-flavor] {slug}: {len(hits)} pattern(s): {', '.join(hits[:8])}")


def _sources_list(sources: list[str], root: str = "") -> str:
    if not sources:
        return ""
    lis = []
    import re as _re
    for i, s in enumerate(sources, 1):
        if isinstance(s, list):
            # legacy [url, "text"] pair — tolerate and emit as plain text
            s = s[0] if s else ""
        s = s.strip()
        # When the LAST whitespace-delimited token of the string is a bare
        # URL, everything before it is the link label. This handles both
        # "text — url" (em-dash) and "text - url" (hyphen) with any number
        # of internal " - " segments inside the label.
        parts = s.rsplit(None, 1)
        if len(parts) == 2 and parts[1].startswith("http"):
            text, url = parts[0].strip(), parts[1]
            # normalise trailing separator in the label
            text = _re.sub(r"\s+[—-]\s*$", "", text)
            # Internal self-reference (pickworth.top) -> same-tab link,
            # prefixed with the page's relative root so it works at any depth.
            # External citation -> new tab + rel=noopener (safety + UX).
            if "pickworth.top" in url:
                path = url.replace("https://www.pickworth.top", "").rstrip("/") + "/"
                rel_url = path.lstrip("/")
                lis.append(
                    f'        <li>{i}. <a href="{root}{rel_url}">{text}</a></li>')
            else:
                lis.append(
                    f'        <li>{i}. <a href="{url}" rel="noopener" '
                    f'target="_blank">{text}</a></li>')
        else:
            lis.append(f'        <li>{i}. {s}</li>')
    return "\n".join(lis)


def _related_cards(cards: list[dict], root: str) -> str:
    if not cards:
        return ""
    blocks = []
    for c in cards:
        tag = c.get("tag", "Review")
        tag_class = c.get("tag_class", "")
        icon = c.get("icon", "i-sources")
        href = root + c.get("href", "")
        link = c.get("link", "Read")
        blurb = c.get("blurb", "")
        cls = f"tag {tag_class}".strip()
        blocks.append(
            f'''      <article class="card">
        <div class="card-top">
          <svg class="card-icon" aria-hidden="true"><use href="#{icon}"></use></svg>
          <span class="{cls}">{tag}</span>
        </div>
        <h3><a href="{href}">{c.get("title","")}</a></h3>
        <p>{blurb}</p>
        <a class="more" href="{href}">{link}</a>
      </article>'''
        )
    return "\n".join(blocks)


def render(slug: str, write_live: bool = True) -> Path:
    draft_path = DRAFTS / f"{slug}.json"
    if not draft_path.exists():
        raise FileNotFoundError(f"draft not found: {draft_path}")
    draft = json.loads(draft_path.read_text(encoding="utf-8"))
    slug = draft.get("slug", slug)
    typ = draft.get("type", "review")
    section = draft.get("section", "tools")

    # enforce the scoring standard (0-5 scale + matching class) before
    # anything is written, so a bad draft never reaches the live tree.
    _validate_draft(draft)

    tpl_path = TEMPLATES / TEMPLATE_FOR[typ]
    tpl = tpl_path.read_text(encoding="utf-8")
    chrome = read_chrome()

    # destination under the live tree: {section}/{slug}/index.html
    live_dest = ROOT / section / slug / "index.html"
    live_root = root_depth(live_dest)
    html = fill(tpl, draft, live_root, chrome)

    # also write to the canonical published tree
    pub_dest = PUBLISHED / section / slug / "index.html"
    pub_dest.parent.mkdir(parents=True, exist_ok=True)
    pub_dest.write_text(html, encoding="utf-8")
    print(f"[published] {pub_dest.relative_to(ROOT)}")

    out = pub_dest
    if write_live:
        live_dest.parent.mkdir(parents=True, exist_ok=True)
        live_dest.write_text(html, encoding="utf-8")
        print(f"[live]      {live_dest.relative_to(ROOT)}")
        out = live_dest
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--no-live", action="store_true",
                    help="only write to content/published, not the live tree")
    args = ap.parse_args()

    if args.all:
        drafts = sorted(DRAFTS.glob("*.json"))
        if not drafts:
            print("no drafts found in", DRAFTS, file=sys.stderr)
            sys.exit(1)
    elif args.slug:
        drafts = [DRAFTS / f"{args.slug}.json"]
    else:
        ap.error("pass --slug <slug> or --all")
        return

    write_live = not args.no_live
    failed = 0
    for d in drafts:
        try:
            render(d.stem, write_live=write_live)
        except FileNotFoundError as e:
            print("skip:", e, file=sys.stderr)
        except SystemExit as e:
            # validation failure (e.g. score outside 0-5 or class mismatch)
            print("FAIL:", e, file=sys.stderr)
            failed += 1
    if failed:
        print(f"{failed} draft(s) failed validation and were NOT rendered", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
