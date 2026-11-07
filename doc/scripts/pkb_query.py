#!/usr/bin/env python3
"""
PKB on-demand retrieval — the runtime mechanism for progressive disclosure.

Feeding a whole PKB into an LLM defeats the point of building one. Progressive
disclosure that lives only as a written rule ("please read on demand") is
fragile: an agent can ignore it and `read doc/**` in one shot. This script
makes progressive disclosure a *mechanism* instead of a *discipline* by giving
callers a narrow, bounded interface:

  1. `--list`  -> the DIRECTORY layer only: page id, title, one-line summary,
                  and token estimate. Cheap, always safe to load first.
  2. `<query>` -> the INDEX layer: rank pages by relevance to a topic and
                  return the top matches' headings, so the caller can decide
                  which page to open.
  3. `--page <id>` (optionally `--section <heading>`) -> the DETAIL layer:
                  return the full page, or just one section of it, on demand.

The contract is: callers should reach for `pkb_query.py` instead of reading the
PKB tree directly, and a `--budget` cap refuses to return more than N estimated
tokens in a single call, so "dump the whole thing" is not reachable through
this tool.

Deterministic, zero-LLM, safe to run in CI or as a local helper.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

# Rough heuristic: ~4 chars per token for mixed English/CJK Markdown. Good
# enough for a budget guard; not meant to match a real tokenizer.
CHARS_PER_TOKEN = 4

STOPWORDS = {
    "the", "a", "an", "of", "to", "and", "or", "in", "on", "for", "is", "are",
    "how", "what", "which", "where", "when", "do", "does", "with", "this",
    "that", "it", "如何", "怎么", "什么", "哪个", "哪些", "的", "了", "和",
}


@dataclass
class Page:
    page_id: str
    path: str
    title: str
    summary: str
    text: str
    headings: List[str] = field(default_factory=list)

    @property
    def token_estimate(self) -> int:
        return max(1, len(self.text) // CHARS_PER_TOKEN)


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // CHARS_PER_TOKEN)


def _first_heading(text: str, fallback: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("#"):
            return line.lstrip("#").strip() or fallback
    return fallback


def _all_headings(text: str) -> List[str]:
    headings: List[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            title = stripped.lstrip("#").strip()
            if title:
                headings.append(title)
    return headings


def _summary(text: str) -> str:
    """First non-empty, non-heading, non-comment line, trimmed."""
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or s.startswith("<!--") or s.startswith("```"):
            continue
        return (s[:157] + "...") if len(s) > 160 else s
    return ""


def load_pages(doc_dir: str) -> List[Page]:
    pages: List[Page] = []
    for name in sorted(os.listdir(doc_dir)):
        if not name.endswith(".md"):
            continue
        if name in {"index.md", "CHANGELOG.md"}:
            continue
        path = os.path.join(doc_dir, name)
        try:
            with open(path, "r", encoding="utf-8") as handle:
                text = handle.read()
        except OSError:
            continue
        page_id = name[:-3]
        pages.append(
            Page(
                page_id=page_id,
                path=path,
                title=_first_heading(text, page_id),
                summary=_summary(text),
                text=text,
                headings=_all_headings(text),
            )
        )
    return pages


def _tokenize(query: str) -> List[str]:
    raw = re.split(r"[^0-9A-Za-z\u4e00-\u9fff]+", query.lower())
    return [t for t in raw if t and t not in STOPWORDS]


def score_page(page: Page, terms: List[str]) -> int:
    if not terms:
        return 0
    haystack_title = (page.title + " " + " ".join(page.headings)).lower()
    haystack_body = page.text.lower()
    score = 0
    for term in terms:
        # Title/heading hits weigh more than body hits.
        score += haystack_title.count(term) * 5
        score += haystack_body.count(term)
    return score


def cmd_list(pages: List[Page]) -> str:
    lines = [
        "# PKB directory (page id | title | ~tokens)",
        "# Load this first. Then query a topic, then open one page on demand.",
        "",
    ]
    total = 0
    for page in pages:
        total += page.token_estimate
        summary = f" — {page.summary}" if page.summary else ""
        lines.append(f"- {page.page_id} | {page.title} | ~{page.token_estimate}t{summary}")
    lines.append("")
    lines.append(f"# {len(pages)} pages, ~{total} tokens total if fully loaded.")
    lines.append("# Do NOT load them all; query for the topic you need.")
    return "\n".join(lines)


def cmd_query(pages: List[Page], query: str, top: int) -> str:
    terms = _tokenize(query)
    scored: List[Tuple[int, Page]] = [
        (score_page(page, terms), page) for page in pages
    ]
    scored = [pair for pair in scored if pair[0] > 0]
    scored.sort(key=lambda pair: pair[0], reverse=True)
    if not scored:
        return (
            f'# No page matched "{query}".\n'
            "# Fall back to `--list` and pick a page, or refine the query."
        )
    lines = [f'# Top {min(top, len(scored))} pages for "{query}"', ""]
    for rank, (points, page) in enumerate(scored[:top], start=1):
        lines.append(f"## {rank}. {page.page_id} — {page.title} (score {points}, ~{page.token_estimate}t)")
        if page.summary:
            lines.append(page.summary)
        if page.headings:
            lines.append("Sections: " + " · ".join(page.headings[:12]))
        lines.append(f"Open with: --page {page.page_id}")
        lines.append("")
    return "\n".join(lines).rstrip()


def _extract_section(text: str, wanted: str) -> Optional[str]:
    lines = text.splitlines()
    wanted_norm = wanted.strip().lower()
    start = None
    start_level = 0
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            title = stripped.lstrip("#").strip().lower()
            if start is None and wanted_norm in title:
                start = idx
                start_level = level
            elif start is not None and level <= start_level:
                return "\n".join(lines[start:idx]).strip()
    if start is not None:
        return "\n".join(lines[start:]).strip()
    return None


def cmd_page(
    pages: List[Page], page_id: str, section: Optional[str], budget: int
) -> str:
    match = next((p for p in pages if p.page_id == page_id), None)
    if match is None:
        available = ", ".join(p.page_id for p in pages)
        return f"# Page not found: {page_id}\n# Available: {available}"

    if section:
        body = _extract_section(match.text, section)
        if body is None:
            heads = " · ".join(match.headings) or "(none)"
            return (
                f'# Section "{section}" not found in {page_id}.\n'
                f"# Sections: {heads}"
            )
    else:
        body = match.text

    tokens = estimate_tokens(body)
    if tokens > budget:
        return (
            f"# Refusing to return {tokens} tokens (budget {budget}).\n"
            f"# This is the progressive-disclosure guard: narrow the request.\n"
            f"# Use --section <heading> to open one section of {page_id}.\n"
            f"# Sections: {' · '.join(match.headings) or '(none)'}"
        )
    header = f"# {page_id} — {match.title} (~{tokens}t)\n"
    return header + body


def main() -> None:
    parser = argparse.ArgumentParser(
        description="On-demand PKB retrieval (progressive disclosure as a mechanism)"
    )
    parser.add_argument("query", nargs="?", help="Topic to rank pages against")
    parser.add_argument("--doc-dir", default="doc", help="PKB doc directory")
    parser.add_argument("--list", action="store_true", help="Directory layer: list pages only")
    parser.add_argument("--page", help="Detail layer: return one page by id")
    parser.add_argument("--section", help="Return only one section (heading) of --page")
    parser.add_argument("--top", type=int, default=3, help="Max pages to rank for a query")
    parser.add_argument(
        "--budget",
        type=int,
        default=6000,
        help="Max estimated tokens returned by a single --page call; guards against full dumps",
    )
    args = parser.parse_args()

    doc_dir = os.path.abspath(args.doc_dir)
    if not os.path.isdir(doc_dir):
        raise SystemExit(f"Doc directory not found: {doc_dir}")

    pages = load_pages(doc_dir)
    if not pages:
        raise SystemExit(f"No PKB pages (*.md) found under {doc_dir}")

    if args.list:
        print(cmd_list(pages))
        return
    if args.page:
        print(cmd_page(pages, args.page, args.section, args.budget))
        return
    if args.query:
        print(cmd_query(pages, args.query, args.top))
        return

    parser.error("provide a <query>, or --list, or --page <id>")


if __name__ == "__main__":
    main()
