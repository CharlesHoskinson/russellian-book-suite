"""Pass A — deterministic regex extraction of Bermuda numeric/named-entity facts."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

# scripts/__init__.py extends this package's __path__ to include forge's
# scripts/ dir, so the imports below resolve to neurosym-forge's modules.
from scripts._edn_reader import Keyword, read_edn  # noqa: E402
from scripts._io import read_edn_file  # noqa: E402

DEFAULT_PREDICATES_PATH = Path(__file__).resolve().parent.parent / "rules" / "predicates.edn"

# Predicate spec keys (from predicates.edn, Keyword-keyed after EDN parse)
_KW_PREDICATES = Keyword("predicates")
_KW_PATTERNS = Keyword("patterns")
_KW_PREDICATE = Keyword("predicate")
_KW_SUBJECT = Keyword("subject")
_KW_VALUE_KIND = Keyword("value_kind")
_KW_WORD_TO_INT = Keyword("word_to_int")
_KW_VALUE = Keyword("value")

# Atom output keys
_KW_KIND = Keyword("kind")
_KW_SORT = Keyword("sort")
_KW_ID = Keyword("id")
_KW_SOURCE = Keyword("source")
_KW_CONFIDENCE = Keyword("confidence")
_KW_EXTRACTOR = Keyword("extractor")
_KW_PATTERN = Keyword("pattern")


def _load_predicates(path: Path | None = None) -> dict:
    p = path or DEFAULT_PREDICATES_PATH
    data = read_edn_file(p)
    return data.get(_KW_PREDICATES, {})


def extract_pass_a(text: str, source_file: str = "?",
                   predicates: dict | None = None) -> list[dict]:
    """Return one atom dict per regex match.

    Each atom has Keyword keys: :kind :sort :predicate :subject :value
    :id :source :confidence :extractor :pattern
    """
    if predicates is None:
        predicates = _load_predicates()
    out: list[dict] = []
    counter = 0
    for _name, spec in predicates.items():
        for pat in spec.get(_KW_PATTERNS, []):
            for m in re.finditer(pat, text, flags=re.IGNORECASE | re.DOTALL):
                value = _coerce_value(m, spec)
                if value is None:
                    continue
                counter += 1
                line = text.count("\n", 0, m.start()) + 1
                out.append({
                    _KW_KIND: Keyword("expression"),
                    _KW_SORT: Keyword("formula"),
                    _KW_PREDICATE: spec[_KW_PREDICATE],
                    _KW_SUBJECT: spec[_KW_SUBJECT],
                    _KW_VALUE: value,
                    _KW_ID: f"prose-{Path(source_file).stem}-{counter:03d}",
                    _KW_SOURCE: {"file": source_file, "line": line},
                    _KW_CONFIDENCE: 0.9,
                    _KW_EXTRACTOR: "regex",
                    _KW_PATTERN: str(_name),
                })
    return out


def _coerce_value(m: re.Match, spec: dict) -> Any:
    kind = spec.get(_KW_VALUE_KIND)
    if kind == "bool":
        return spec.get(_KW_VALUE, True)
    if kind == "int":
        raw = m.group("n") if "n" in m.groupdict() else (m.group(1) if m.groups() else None)
        if raw is None:
            return None
        word_to_int = spec.get(_KW_WORD_TO_INT, {})
        mapped = word_to_int.get(raw.lower())
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
