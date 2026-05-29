"""Render review prompts and parse review-report markdown.

The actual subagent dispatch is performed by the calling Claude (via the
Task tool). This module produces the prompt and consumes the resulting
markdown, keeping the unit testable in pure Python.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

import jsonschema
import yaml

from .persona_loader import Persona

ASSETS = Path(__file__).resolve().parent.parent / "assets"
PROMPT_TEMPLATE = (ASSETS / "persona-prompt-template.md").read_text(encoding="utf-8")
REPORT_SCHEMA = json.loads((ASSETS / "review-report.schema.json").read_text(encoding="utf-8"))


@dataclass(frozen=True)
class Finding:
    text: str
    line: str = ""


@dataclass(frozen=True)
class ReviewResult:
    persona_id: str
    chapter_id: str
    verdict: str
    critical: list
    important: list
    minor: list
    voice_notes: str
    report_path: Path
    raw_metadata: dict = field(default_factory=dict)


def render_prompt(persona: Persona, draft_path: Path, chapter_meta: dict, output_path: Path) -> str:
    draft_md = Path(draft_path).read_text(encoding="utf-8")
    return (
        PROMPT_TEMPLATE
        .replace("{{persona_body}}", persona.body_md)
        .replace("{{display_name}}", persona.display_name)
        .replace("{{role}}", persona.role)
        .replace("{{persona_id}}", persona.persona_id)
        .replace("{{chapter_id}}", chapter_meta.get("chapter_id", ""))
        .replace("{{chapter_title}}", chapter_meta.get("chapter_title", ""))
        .replace("{{chapter_purpose}}", chapter_meta.get("chapter_purpose", ""))
        .replace("{{audience}}", chapter_meta.get("audience", ""))
        .replace("{{draft_md}}", draft_md)
        .replace("{{output_path}}", str(output_path))
    )


_FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)
_SECTION = re.compile(r"^##\s+(.+)$", re.MULTILINE)


def _parse_findings_section(body: str, header: str) -> list[Finding]:
    headers = [m for m in _SECTION.finditer(body) if header.lower() in m.group(1).lower()]
    if not headers:
        return []
    start = headers[0].end()
    next_section = _SECTION.search(body, pos=start)
    end = next_section.start() if next_section else len(body)
    section_body = body[start:end].strip()
    out: list[Finding] = []
    for line in section_body.splitlines():
        line = line.strip()
        if not line:
            continue
        if re.match(r"^([-*]\s|\d+\.)", line):
            text = re.sub(r"^([-*]|\d+\.)\s*", "", line).strip()
            if text:
                out.append(Finding(text=text))
    return out


def _schema_serializable(meta: dict) -> dict:
    """Coerce YAML-native scalars to JSON-Schema-comparable forms.

    PyYAML decodes an ISO timestamp into a datetime/date object, but the schema
    declares reviewed_at as a date-time *string*; render such values back to
    ISO strings so validation sees what the report actually wrote.
    """
    out = dict(meta)
    for key, value in out.items():
        if isinstance(value, (datetime, date)):
            out[key] = value.isoformat()
    return out


def parse_review_report(path: Path) -> ReviewResult:
    text = Path(path).read_text(encoding="utf-8")
    match = _FRONTMATTER.match(text)
    if not match:
        raise ValueError(f"review report missing frontmatter: {path}")
    meta = yaml.safe_load(match.group(1)) or {}
    body = match.group(2)

    # Persona is the dict key for per-persona verdicts/breakdowns downstream.
    # Fall back to the report filename stem when the frontmatter omits it, so
    # two field-less reports don't collide on the empty-string key.
    persona_id = (str(meta.get("persona") or "").strip()) or Path(path).stem
    meta.setdefault("persona", persona_id)

    # Validate frontmatter against the report schema: reject bad chapter_id,
    # invalid verdict, or missing/negative count fields rather than silently
    # coercing them with defaults.
    try:
        jsonschema.validate(_schema_serializable(meta), REPORT_SCHEMA)
    except jsonschema.ValidationError as exc:
        raise ValueError(f"invalid review report {path}: {exc.message}") from exc

    critical = _parse_findings_section(body, "Critical")
    important = _parse_findings_section(body, "Important")
    minor = _parse_findings_section(body, "Minor")
    voice_headers = [m for m in _SECTION.finditer(body) if "voice" in m.group(1).lower() or "cadence" in m.group(1).lower()]
    voice_notes = ""
    if voice_headers:
        start = voice_headers[0].end()
        next_section = _SECTION.search(body, pos=start)
        end = next_section.start() if next_section else len(body)
        voice_notes = body[start:end].strip()

    return ReviewResult(
        persona_id=persona_id,
        chapter_id=meta.get("chapter_id", ""),
        verdict=meta.get("verdict", "APPROVED"),
        critical=critical,
        important=important,
        minor=minor,
        voice_notes=voice_notes,
        report_path=Path(path),
        raw_metadata=meta,
    )
