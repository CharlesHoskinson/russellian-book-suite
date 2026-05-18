"""Osmotic-pressure ledger ingester.

Reads a JSONL fixture ledger, applies the predicate map in
rules/predicates.edn to fact-class claims, and emits typed atoms to
work/claims.edn.  Mirrors verifiers/bermuda/scripts/ingest_ledger.py —
same public API (`ingest(ledger_path, predicates_path, out_path)`) so the
smoke tests can import it unchanged.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from scripts._edn_reader import Keyword
from scripts._edn_writer import write_edn  # noqa: F401  (re-exported for callers)
from scripts._io import read_edn_file, write_edn_file

_KW_VERSION = Keyword("version")
_KW_ATOMS = Keyword("atoms")
_KW_PREDICATES = Keyword("predicates")
_KW_PATTERNS = Keyword("patterns")
_KW_PREDICATE = Keyword("predicate")
_KW_SUBJECT = Keyword("subject")
_KW_VALUE_KIND = Keyword("value_kind")
_KW_VALUE_KIND_H = Keyword("value-kind")
_KW_WORD_TO_INT = Keyword("word_to_int")
_KW_WORD_TO_INT_H = Keyword("word-to-int")
_KW_VALUE = Keyword("value")
_KW_ID = Keyword("id")
_KW_DOC = Keyword("doc")
_KW_SOURCE_SPANS = Keyword("source_spans")
_KW_SUPPORTS_CHAPTERS = Keyword("supports_chapters")
_KW_CONFIDENCE = Keyword("confidence")
_KW_KIND = Keyword("kind")
_KW_SORT = Keyword("sort")
_KW_NAME = Keyword("name")
_KW_CONTEXT = Keyword("context")


def read_ledger(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def latest_per_id(rows: list[dict]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for r in rows:
        cid = r.get("claim_id") or r.get("id")
        if cid:
            out[cid] = r
    return out


def _is_verified(c: dict) -> bool:
    return c.get("status") == "verified" or c.get("tbf:status") == "verified"


def _get_spec(spec: dict, underscore_key: Keyword, hyphen_key: Keyword,
              default: Any = None) -> Any:
    v = spec.get(underscore_key)
    if v is None:
        v = spec.get(hyphen_key)
    return v if v is not None else default


def _kind_str(v: Any) -> str:
    if isinstance(v, Keyword):
        return v.name
    return str(v) if v is not None else ""


_JS_NAMED_GROUP = re.compile(r"\(\?<([A-Za-z_][A-Za-z0-9_]*)>")


def _to_python_regex(pat: str) -> str:
    """Translate JS-style `(?<name>...)` named groups to Python `(?P<name>...)`.

    BookLogic lifts.edn authors patterns in JS syntax (the CLJS compiler
    consumes them via JS regex). Python's `re` module uses the older
    Perl-style `(?P<name>...)` form.
    """
    return _JS_NAMED_GROUP.sub(r"(?P<\1>", pat)


def _apply_predicates(text: str, predicates: dict) -> tuple[str, Any, str] | None:
    for _name, spec in predicates.items():
        for pat in spec.get(_KW_PATTERNS, []):
            m = re.search(_to_python_regex(pat), text, flags=re.IGNORECASE | re.DOTALL)
            if not m:
                continue
            value_kind = _kind_str(_get_spec(spec, _KW_VALUE_KIND, _KW_VALUE_KIND_H))
            gd = m.groupdict()
            if value_kind == "bool":
                value = spec.get(_KW_VALUE, True)
            elif value_kind == "int":
                raw = gd.get("n") or gd.get("v") or (m.group(1) if m.lastindex else None)
                if raw is None:
                    continue
                raw = raw.replace(",", "").strip()
                word_to_int = _get_spec(spec, _KW_WORD_TO_INT, _KW_WORD_TO_INT_H, {})
                value = word_to_int.get(raw.lower(), None)
                if value is None:
                    try:
                        value = int(raw)
                    except ValueError:
                        continue
            elif value_kind == "real":
                raw = gd.get("n") or gd.get("v") or (m.group(1) if m.lastindex else None)
                if raw is None:
                    continue
                raw = raw.replace(",", "").strip()
                try:
                    value = float(raw)
                except ValueError:
                    continue
            elif value_kind == "string":
                raw = gd.get("v") or gd.get("n") or (m.group(1) if m.lastindex else None)
                value = raw.strip() if raw else ""
            else:
                continue
            pred_raw = spec.get(_KW_PREDICATE)
            subj_raw = spec.get(_KW_SUBJECT)
            pred = f":{pred_raw.name}" if isinstance(pred_raw, Keyword) else str(pred_raw)
            subj = f":{subj_raw.name}" if isinstance(subj_raw, Keyword) else str(subj_raw)
            return pred, value, subj
    return None


def _claim_to_atom(claim: dict, predicates: dict) -> dict:
    text = claim.get("canonical_text", "")
    base: dict = {
        _KW_ID: claim.get("claim_id", "?"),
        _KW_DOC: text[:200],
        _KW_SOURCE_SPANS: claim.get("source_spans", []),
        _KW_SUPPORTS_CHAPTERS: claim.get("supports_chapters", []),
        _KW_CONFIDENCE: claim.get("confidence", 0.0),
    }
    if claim.get("claim_type") == "design_decision":
        base.update({
            _KW_KIND: Keyword("symbol"),
            _KW_SORT: Keyword("formula"),
            _KW_NAME: Keyword("CONTEXT"),
            _KW_CONTEXT: True,
        })
        return base
    match = _apply_predicates(text, predicates)
    if match is None:
        base.update({
            _KW_KIND: Keyword("symbol"),
            _KW_SORT: Keyword("formula"),
            _KW_NAME: Keyword("OPAQUE"),
        })
        return base
    predicate, value, subject = match
    base.update({
        _KW_KIND: Keyword("expression"),
        _KW_SORT: Keyword("formula"),
        _KW_PREDICATE: predicate,
        _KW_SUBJECT: subject,
        _KW_VALUE: value,
        _KW_CONTEXT: False,
    })
    return base


def ingest(ledger_path: Path,
           predicates_path: Path,
           out_path: Path,
           return_atoms: bool = False) -> list[dict] | int:
    rows = read_ledger(ledger_path)
    latest = latest_per_id(rows)
    verified = [c for c in latest.values() if _is_verified(c)]
    predicates_data = read_edn_file(predicates_path)
    predicates = predicates_data.get(_KW_PREDICATES, {})
    atoms = [_claim_to_atom(c, predicates) for c in verified]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_edn_file(out_path, {_KW_VERSION: 1, _KW_ATOMS: atoms})
    return atoms if return_atoms else len(atoms)
