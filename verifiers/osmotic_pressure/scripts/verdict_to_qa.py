"""Translate the osmotic_pressure verifier's verdict.edn into a
book-qa-friendly verification-defects.json. Mirrors bermuda's
verdict_to_qa.py so the same shape consumes both verifiers'
verdicts (REQ-DATALOG-042, REQ-DATALOG-043).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

from scripts._edn_reader import Keyword  # noqa: E402
from scripts._io import read_edn_file  # noqa: E402

FORGE_OSMOTIC_VERSION = "osmotic_pressure 0.1.0 / neurosym-forge 0.2.0"

_KW_VERDICT = Keyword("verdict")
_KW_STATUS = Keyword("status")
_KW_CORE = Keyword("core")
_KW_EXPLANATION = Keyword("explanation")
_KW_VERIFIED_COUNT = Keyword("verified-count")
_KW_REASON = Keyword("reason")
_KW_QUERIES = Keyword("queries")
_KW_COZO_DEFECTS = Keyword("cozo-defects")
_KW_CORPUS_DEFECTS = Keyword("corpus-defects")
_KW_CONSTRAINT_ID = Keyword("constraint-id")
_KW_SUBJECTS = Keyword("subjects")
_KW_NAME = Keyword("name")
_KW_ROWS = Keyword("rows")
_KW_REMEDIES = Keyword("remedies")
_KW_ID = Keyword("id")
_KW_WHEN = Keyword("when")
_KW_PROPOSE = Keyword("propose")
_KW_REQUIRES = Keyword("requires")
_KW_QUERY = Keyword("query")


def _str_verdict(v: object) -> str:
    if isinstance(v, Keyword):
        return v.name
    return str(v) if v is not None else "unknown"


def _query_rows(payload: dict, key: Keyword) -> list[dict]:
    raw = payload.get(key, []) or []
    out: list[dict] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        name = entry.get(_KW_NAME, "")
        rows = entry.get(_KW_ROWS, 0)
        out.append({"name": str(name), "rows": int(rows)})
    out.sort(key=lambda e: e["name"])
    return out


def _remedy_query_name(when_clause: object) -> str | None:
    """Inspect a `defremedy :when` clause and return the bound query name
    (the keyword inside `:when {:query :Q###}`) when the clause
    references a defquery (REQ-DATALOG-043).
    """
    if isinstance(when_clause, dict):
        q = when_clause.get(_KW_QUERY)
        if isinstance(q, Keyword):
            return q.name
        if isinstance(q, str):
            return q.lstrip(":")
    return None


def _bind_remedies(remedies_path: Path, query_rows: list[dict]) -> list[dict]:
    if not remedies_path.exists():
        return []
    payload = read_edn_file(remedies_path)
    raw_remedies = payload.get(_KW_REMEDIES, []) or []
    by_query = {qr["name"]: qr["rows"] for qr in query_rows}
    out: list[dict] = []
    for r in raw_remedies:
        if not isinstance(r, dict):
            continue
        rid = r.get(_KW_ID, "")
        when = r.get(_KW_WHEN)
        propose = r.get(_KW_PROPOSE)
        requires = r.get(_KW_REQUIRES)
        query_name = _remedy_query_name(when)
        entry = {
            "id": str(rid),
            "when": repr(when) if when is not None else "",
            "propose": repr(propose) if propose is not None else "",
            "requires": requires.name if isinstance(requires, Keyword) else (
                str(requires) if requires is not None else ""
            ),
        }
        if query_name is not None:
            entry["query"] = query_name
            entry["rows"] = int(by_query.get(query_name, 0))
            entry["query_bound"] = True
        else:
            entry["query_bound"] = False
        out.append(entry)
    return out


def _corpus_defect_rows(payload: dict) -> list[dict]:
    """REQ-CORPUS-053: read the verdict's :corpus-defects vector and
    surface each entry as `{constraint_id, subjects[], explanation}`.
    """
    raw = payload.get(_KW_CORPUS_DEFECTS, []) or []
    out: list[dict] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        cid = entry.get(_KW_CONSTRAINT_ID, "")
        subjects = entry.get(_KW_SUBJECTS, []) or []
        explanation = entry.get(_KW_EXPLANATION, "") or ""
        out.append({
            "constraint_id": str(cid),
            "subjects":      [str(s) for s in subjects],
            "explanation":   str(explanation),
        })
    out.sort(key=lambda e: e["constraint_id"])
    return out


def translate(verdict_path: Path, out_path: Path, remedies_path: Path | None = None) -> None:
    if not verdict_path.exists():
        raise FileNotFoundError(verdict_path)
    payload = read_edn_file(verdict_path)
    verdict_raw = payload.get(_KW_VERDICT)
    if verdict_raw is None:
        verdict_raw = payload.get(_KW_STATUS, "unknown")
    verdict_str = _str_verdict(verdict_raw)
    queries = _query_rows(payload, _KW_QUERIES)
    cozo_defects = _query_rows(payload, _KW_COZO_DEFECTS)
    corpus_defects = _corpus_defect_rows(payload)
    if remedies_path is None:
        remedies_path = verdict_path.resolve().parent.parent / "rules" / "remedies.edn"
    remedies = _bind_remedies(remedies_path, queries)
    result = {
        "verdict": verdict_str,
        "core": list(payload.get(_KW_CORE, [])),
        "explanation": payload.get(_KW_EXPLANATION, "") or "",
        "verified_count": payload.get(_KW_VERIFIED_COUNT, 0),
        "queries": queries,
        "cozo_defects": cozo_defects,
        "corpus_defects": corpus_defects,
        "remedies": remedies,
        "produced_at": dt.datetime.now(dt.UTC).isoformat(),
        "verifier_version": FORGE_OSMOTIC_VERSION,
    }
    if verdict_str == "unknown":
        result["reason"] = payload.get(_KW_REASON, "unknown") or "unknown"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8", newline="\n",
    )


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verdict", required=True)
    ap.add_argument("--out", required=True,
                    help="path to <workspace>/qa/verification-defects.json")
    ap.add_argument("--remedies", required=False, default=None,
                    help="optional path to rules/remedies.edn for "
                         "defremedy :when query-binding (REQ-DATALOG-043)")
    args = ap.parse_args(argv)
    remedies_path = Path(args.remedies) if args.remedies else None
    translate(Path(args.verdict), Path(args.out), remedies_path)
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
