"""Parse syntopical/schools/<slug>.edn into typed dataclasses.

A school is a hand-curated voice: a set of source documents plus
explicit asserts/rejects that override atom-inferred stance during
position computation.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from pathlib import Path


class SchoolError(ValueError):
    """Raised when a schools/*.edn file is malformed."""


@dataclass(frozen=True)
class School:
    slug: str
    name: str
    charter: str
    members: list[str] = field(default_factory=list)
    canonical_asserts: list[str] = field(default_factory=list)
    canonical_rejects: list[str] = field(default_factory=list)


_SUPPORTED_VERSIONS = {1}


def _strip_edn_comments(text: str) -> str:
    return re.sub(r";.*", "", text)


def _read_edn_map(text: str) -> dict[str, object]:
    """Tiny EDN-map reader sufficient for our schema.

    Supports: keyword keys, string/keyword/int values, vectors of strings
    or keywords. Rejects anything more complex with SchoolError.
    """
    s = _strip_edn_comments(text).strip()
    if not s.startswith("{") or not s.endswith("}"):
        raise SchoolError("expected top-level EDN map")
    inner = s[1:-1].strip()
    out: dict[str, object] = {}
    i = 0
    while i < len(inner):
        if inner[i].isspace():
            i += 1
            continue
        if inner[i] != ":":
            raise SchoolError(f"expected keyword key at offset {i}")
        m = re.match(r":([A-Za-z][A-Za-z0-9\-_/]*)", inner[i:])
        if not m:
            raise SchoolError(f"malformed keyword at offset {i}")
        key = m.group(1)
        i += m.end()
        while i < len(inner) and inner[i].isspace():
            i += 1
        val, consumed = _read_value(inner[i:])
        out[key] = val
        i += consumed
    return out


def _read_value(s: str) -> tuple[object, int]:
    if s.startswith('"'):
        end = s.index('"', 1)
        while s[end - 1] == "\\":
            end = s.index('"', end + 1)
        return s[1:end], end + 1
    if s.startswith(":"):
        m = re.match(r":([A-Za-z][A-Za-z0-9\-_/]*)", s)
        if not m:
            raise SchoolError("malformed keyword value")
        return f":{m.group(1)}", m.end()
    if s.startswith("["):
        depth = 0
        for j, ch in enumerate(s):
            if ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    items_text = s[1:j].strip()
                    items: list[object] = []
                    k = 0
                    while k < len(items_text):
                        if items_text[k].isspace():
                            k += 1
                            continue
                        v, c = _read_value(items_text[k:])
                        items.append(v)
                        k += c
                    return items, j + 1
        raise SchoolError("unterminated vector")
    if s.startswith("true"):
        return True, 4
    if s.startswith("false"):
        return False, 5
    m = re.match(r"-?\d+", s)
    if m:
        return int(m.group(0)), m.end()
    raise SchoolError(f"unsupported value: {s[:20]!r}")


def load_school(path: Path) -> School:
    """Load one schools/*.edn file."""
    raw = path.read_text(encoding="utf-8")
    data = _read_edn_map(raw)

    if data.get("version") not in _SUPPORTED_VERSIONS:
        raise SchoolError(
            f"{path.name}: unsupported version {data.get('version')!r}; "
            f"this tool understands {sorted(_SUPPORTED_VERSIONS)}"
        )
    for required in ("school", "name", "charter"):
        if required not in data:
            raise SchoolError(f"{path.name}: missing required key :{required}")
    slug = data["school"]
    if isinstance(slug, str) and slug.startswith(":"):
        slug = slug[1:]
    return School(
        slug=str(slug),
        name=str(data["name"]),
        charter=str(data["charter"]),
        members=list(data.get("members", [])),
        canonical_asserts=list(data.get("canonical-asserts", [])),
        canonical_rejects=list(data.get("canonical-rejects", [])),
    )


def load_schools_dir(schools_dir: Path) -> list[School]:
    """Load every schools/*.edn under schools_dir. Missing dir -> []."""
    if not schools_dir.is_dir():
        return []
    return [load_school(p) for p in sorted(schools_dir.glob("*.edn"))]
