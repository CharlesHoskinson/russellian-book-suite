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
# value_kind / value-kind: v0.2 used underscored form; codegened form uses hyphen.
_KW_VALUE_KIND = Keyword("value_kind")
_KW_VALUE_KIND_H = Keyword("value-kind")   # codegened hyphenated form
_KW_WORD_TO_INT = Keyword("word_to_int")
_KW_WORD_TO_INT_H = Keyword("word-to-int")  # codegened hyphenated form
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
                # Normalise predicate / subject: both may be Keyword (codegened)
                # or plain string (v0.2). Emit as ":<name>" string for compat.
                pred_raw = spec.get(_KW_PREDICATE)
                pred_str = (
                    f":{pred_raw.name}" if isinstance(pred_raw, Keyword)
                    else str(pred_raw)
                )
                subj_raw = spec.get(_KW_SUBJECT)
                subj_str = (
                    f":{subj_raw.name}" if isinstance(subj_raw, Keyword)
                    else str(subj_raw)
                )
                out.append({
                    _KW_KIND: Keyword("expression"),
                    _KW_SORT: Keyword("formula"),
                    _KW_PREDICATE: pred_str,
                    _KW_SUBJECT: subj_str,
                    _KW_VALUE: value,
                    _KW_ID: f"prose-{Path(source_file).stem}-{counter:03d}",
                    _KW_SOURCE: {"file": source_file, "line": line},
                    _KW_CONFIDENCE: 0.9,
                    _KW_EXTRACTOR: "regex",
                    _KW_PATTERN: str(_name),
                })
    return out


def _get_spec_value(spec: dict, key_underscore: Keyword, key_hyphen: Keyword,
                    default: Any = None) -> Any:
    """Fetch a spec key that may appear in either underscore or hyphen form."""
    v = spec.get(key_underscore)
    if v is None:
        v = spec.get(key_hyphen)
    return v if v is not None else default


def _kind_str(kind: Any) -> str | None:
    """Normalise a value-kind value to a plain string for comparison.

    The v0.2 predicates.edn stored plain strings ('int', 'bool', …).
    The codegened predicates.edn stores Keywords (:int, :bool, …).
    """
    if kind is None:
        return None
    if isinstance(kind, Keyword):
        return kind.name
    return str(kind)


def _coerce_value(m: re.Match, spec: dict) -> Any:
    kind = _kind_str(_get_spec_value(spec, _KW_VALUE_KIND, _KW_VALUE_KIND_H))
    if kind == "bool":
        v = spec.get(_KW_VALUE)
        return v if v is not None else True
    if kind == "int":
        raw = m.group("n") if "n" in m.groupdict() else (m.group(1) if m.groups() else None)
        if raw is None:
            return None
        word_to_int = _get_spec_value(spec, _KW_WORD_TO_INT, _KW_WORD_TO_INT_H, {})
        mapped = word_to_int.get(raw.lower())
        if mapped is not None:
            return mapped
        cleaned = raw.replace(",", "").strip()
        try:
            return int(cleaned)
        except ValueError:
            return None
    if kind == "real":
        raw = m.group("n") if "n" in m.groupdict() else (m.group(1) if m.groups() else None)
        if raw is None:
            return None
        try:
            return float(raw.replace(",", ""))
        except ValueError:
            return None
    if kind == "string":
        return m.group("binomial").strip()
    if kind == "entity":
        return m.group("island").replace(".", "").replace(" ", "_")
    return None
