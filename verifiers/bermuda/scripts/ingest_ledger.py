"""Bermuda-specific ledger ingester.

Reads examples/bermuda-manual/claims/ledger.jsonl, applies the predicate
map in rules/predicates.edn to fact-class claims, and emits typed atoms
to work/claims.edn. design_decision claims are emitted as :context atoms.

Generated initially by neurosym-forge --book-knowledge-bridge, then
specialized for the Bermuda predicate set.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

# scripts/__init__.py extends this package's __path__ to include forge's
# scripts/ dir, so the imports below resolve to neurosym-forge's modules.
from scripts._edn_reader import Keyword  # noqa: E402
from scripts._io import read_edn_file, write_edn_file  # noqa: E402

_KW_VERSION = Keyword("version")
_KW_ATOMS = Keyword("atoms")
_KW_PREDICATES = Keyword("predicates")
_KW_PATTERNS = Keyword("patterns")
_KW_PREDICATE = Keyword("predicate")
_KW_SUBJECT = Keyword("subject")
_KW_VALUE_KIND = Keyword("value_kind")
_KW_VALUE_KIND_H = Keyword("value-kind")   # codegened hyphenated form
_KW_WORD_TO_INT = Keyword("word_to_int")
_KW_WORD_TO_INT_H = Keyword("word-to-int")  # codegened hyphenated form
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


def _get_spec(spec: dict, underscore_key: Keyword, hyphen_key: Keyword, default: Any = None) -> Any:
    """Dual-key lookup: try underscore form first (v0.2), then hyphenated (codegened)."""
    v = spec.get(underscore_key)
    if v is None:
        v = spec.get(hyphen_key)
    return v if v is not None else default


def _kind_str(v: Any) -> str:
    """Normalise value-kind: Keyword('int') → 'int', 'int' → 'int'."""
    if isinstance(v, Keyword):
        return v.name
    return str(v) if v is not None else ""


def _apply_predicates(text: str, predicates: dict) -> tuple[str, Any, str] | None:
    """Match text against the predicate map. Returns (predicate, value, subject) or None."""
    for _name, spec in predicates.items():
        for pat in spec.get(_KW_PATTERNS, []):
            m = re.search(pat, text, flags=re.IGNORECASE | re.DOTALL)
            if not m:
                continue
            value_kind = _kind_str(_get_spec(spec, _KW_VALUE_KIND, _KW_VALUE_KIND_H))
            if value_kind == "bool":
                value = spec.get(_KW_VALUE, True)
            elif value_kind == "int":
                raw = m.group("n") if "n" in m.groupdict() else m.group(1)
                raw = raw.replace(",", "").strip()
                word_to_int = _get_spec(spec, _KW_WORD_TO_INT, _KW_WORD_TO_INT_H, {})
                value = word_to_int.get(raw.lower(), None)
                if value is None:
                    try:
                        value = int(raw)
                    except ValueError:
                        continue
            elif value_kind == "real":
                raw = m.group("n") if "n" in m.groupdict() else m.group(1)
                raw = raw.replace(",", "").strip()
                try:
                    value = float(raw)
                except ValueError:
                    continue
            elif value_kind == "string":
                value = m.group("binomial").strip()
            elif value_kind == "entity":
                value = m.group("island").replace(".", "").replace(" ", "_")
            else:
                continue
            pred_raw = spec.get(_KW_PREDICATE)
            subj_raw = spec.get(_KW_SUBJECT)
            # REQ-EDN-049: emit Keyword objects, not string-with-colon-prefix.
            pred = pred_raw if isinstance(pred_raw, Keyword) else Keyword(str(pred_raw).lstrip(":"))
            subj = subj_raw if isinstance(subj_raw, Keyword) else Keyword(str(subj_raw).lstrip(":"))
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


def _validate_against_schema(predicates_path: Path, predicates: dict) -> None:
    """REQ-EDN-053: validate predicate names against booklogic-schema.edn.

    The schema is emitted by `nbb -m booklogic` next to predicates.edn. If
    present, every key in `predicates` must match a key in the schema's
    :predicates map. Missing schema -> warning only (older projects).
    """
    schema_path = predicates_path.parent / "booklogic-schema.edn"
    if not schema_path.exists():
        return
    schema = read_edn_file(schema_path)
    known = set(schema.get(Keyword("predicates"), {}).keys())
    unknown = [str(p) for p in predicates if p not in known]
    if unknown:
        import sys
        print(
            f"ingest_ledger: unknown predicate(s) {unknown!r}; not in "
            f"booklogic-schema.edn (expected one of {sorted(map(str, known))!r})",
            file=sys.stderr,
        )
        sys.exit(1)


def compute_atoms(ledger_path: Path, predicates_path: Path) -> list[dict]:
    """Read ledger + predicates and return atoms WITHOUT writing to disk."""
    rows = read_ledger(ledger_path)
    latest = latest_per_id(rows)
    verified = [c for c in latest.values() if _is_verified(c)]
    predicates_data = read_edn_file(predicates_path)
    predicates = predicates_data.get(_KW_PREDICATES, {})
    _validate_against_schema(predicates_path, predicates)
    return [_claim_to_atom(c, predicates) for c in verified]


def ingest(ledger_path: Path,
           predicates_path: Path,
           out_path: Path,
           return_atoms: bool = False) -> list[dict] | int:
    atoms = compute_atoms(ledger_path, predicates_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_edn_file(out_path, {_KW_VERSION: 1, _KW_ATOMS: atoms})
    return atoms if return_atoms else len(atoms)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--predicates", required=True)
    ap.add_argument("--out", default="work/claims.edn")
    args = ap.parse_args(argv)
    n = ingest(Path(args.ledger), Path(args.predicates), Path(args.out))
    print(f"ingested {n} verified atoms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
