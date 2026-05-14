"""Pass A — deterministic regex extraction of Bermuda numeric/named-entity facts."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

DEFAULT_PREDICATES_PATH = Path(__file__).resolve().parent.parent / "rules" / "predicates.edn"


def _load_predicates(path: Path | None = None) -> dict[str, dict]:
    p = path or DEFAULT_PREDICATES_PATH
    return json.loads(p.read_text(encoding="utf-8")).get("predicates", {})


def extract_pass_a(text: str, source_file: str = "?",
                   predicates: dict[str, dict] | None = None) -> list[dict]:
    """Return one atom dict per regex match.

    Each atom: {kind, sort, predicate, subject, value, id, source, confidence}.
    """
    if predicates is None:
        predicates = _load_predicates()
    out: list[dict] = []
    counter = 0
    for name, spec in predicates.items():
        for pat in spec.get("patterns", []):
            for m in re.finditer(pat, text, flags=re.IGNORECASE | re.DOTALL):
                value = _coerce_value(m, spec)
                if value is None:
                    continue
                counter += 1
                line = text.count("\n", 0, m.start()) + 1
                out.append({
                    "kind": "expression",
                    "sort": ":formula",
                    "predicate": spec["predicate"],
                    "subject": spec["subject"],
                    "value": value,
                    "id": f"prose-{Path(source_file).stem}-{counter:03d}",
                    "source": {"file": source_file, "line": line},
                    "confidence": 0.9,
                    "extractor": "regex",
                    "pattern": name,
                })
    return out


def _coerce_value(m: re.Match, spec: dict) -> Any:
    kind = spec.get("value_kind")
    if kind == "bool":
        return spec.get("value", True)
    if kind == "int":
        raw = m.group("n") if "n" in m.groupdict() else (m.group(1) if m.groups() else None)
        if raw is None:
            return None
        mapped = spec.get("word_to_int", {}).get(raw.lower())
        if mapped is not None:
            return mapped
        try:
            return int(raw)
        except ValueError:
            return None
    if kind == "string":
        return m.group("binomial").strip()
    if kind == "entity":
        return m.group("island").replace(".", "").replace(" ", "_")
    return None
