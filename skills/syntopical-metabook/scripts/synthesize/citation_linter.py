"""Verify every prose paragraph under syntopical/ carries at least one citation.

A citation is either:
- `[claim-id]` of form `[cl-...]` or `[claim-...]`
- `[[wiki-slug]]`
- `rule-<name>` (booklogic rewrite witness)
"""
from __future__ import annotations
import re
from dataclasses import dataclass
from pathlib import Path

CLAIM_RE = re.compile(r"\[(?:cl|claim)-[\w-]+\]")
WIKI_RE = re.compile(r"\[\[[\w/-]+\]\]")
RULE_RE = re.compile(r"\brule-[\w-]+")
HEADING_RE = re.compile(r"^\s{0,3}#")
TABLE_RE = re.compile(r"^\s*\|")


@dataclass
class CitationIssue:
    line: int
    text: str
    reason: str = "paragraph has no citation"


def _paragraphs(text: str):
    """Yield (start_line, paragraph_text) tuples. Skip headings, tables, blockquotes."""
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        if not lines[i].strip() or HEADING_RE.match(lines[i]) or TABLE_RE.match(lines[i]):
            i += 1
            continue
        start = i + 1
        para = []
        while i < len(lines) and lines[i].strip() and not HEADING_RE.match(lines[i]) \
              and not TABLE_RE.match(lines[i]):
            para.append(lines[i])
            i += 1
        yield start, "\n".join(para)


def _has_citation(text: str) -> bool:
    return bool(CLAIM_RE.search(text) or WIKI_RE.search(text) or RULE_RE.search(text))


def lint_paragraph(text: str) -> list[CitationIssue]:
    issues: list[CitationIssue] = []
    for line, para in _paragraphs(text):
        if not _has_citation(para):
            issues.append(CitationIssue(line=line, text=para))
    return issues


def lint_file(path: Path) -> list[CitationIssue]:
    return lint_paragraph(path.read_text(encoding="utf-8"))


def lint_directory(root: Path) -> dict[Path, list[CitationIssue]]:
    out: dict[Path, list[CitationIssue]] = {}
    for p in sorted(root.rglob("*.md")):
        issues = lint_file(p)
        if issues:
            out[p] = issues
    return out
