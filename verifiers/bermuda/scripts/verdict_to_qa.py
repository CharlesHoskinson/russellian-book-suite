"""Translate the verifier's verdict.edn into book-qa's verification-defects.json.

The output format is consumed by book-qa.lint_artifact.lint_d13. See
docs/specs/2026-05-14-bermuda-verifier-design.md § "book-qa D13 hook".

Reads verdict.edn as real EDN (Keyword-keyed map). Writes
verification-defects.json as JSON (book-qa reads JSON).
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

# scripts/__init__.py extends this package's __path__ to include forge's
# scripts/ dir, so the imports below resolve to neurosym-forge's modules.
from scripts._edn_reader import Keyword  # noqa: E402
from scripts._io import read_edn_file  # noqa: E402

FORGE_BERMUDA_VERSION = "bermuda 0.1.0 / neurosym-forge 0.2.0"

_KW_VERDICT = Keyword("verdict")
_KW_STATUS = Keyword("status")
_KW_CORE = Keyword("core")
_KW_EXPLANATION = Keyword("explanation")
_KW_VERIFIED_COUNT = Keyword("verified-count")
_KW_REASON = Keyword("reason")
_KW_QUERIES = Keyword("queries")
_KW_COZO_DEFECTS = Keyword("cozo-defects")
_KW_NAME = Keyword("name")
_KW_ROWS = Keyword("rows")
_KW_REMEDIES = Keyword("remedies")
_KW_ID = Keyword("id")
_KW_WHEN = Keyword("when")
_KW_PROPOSE = Keyword("propose")
_KW_REQUIRES = Keyword("requires")
_KW_QUERY = Keyword("query")


def _str_verdict(v: object) -> str:
    """Accept Keyword or str verdict value; return plain string."""
    if isinstance(v, Keyword):
        return v.name
    return str(v) if v is not None else "unknown"


def _query_rows(payload: dict, key: Keyword) -> list[dict]:
    """Read a `:queries` / `:cozo-defects` vector off the verdict. Each
    entry is a `{:name "..." :rows N}` map. Returns a JSON-friendly
    list of dicts ordered by name (REQ-DATALOG-042).
    """
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
    (the keyword inside `:when {:query :Q002-low-confidence}`) when the
    clause references a defquery. Returns None for unsat-core /
    structural patterns that don't bind a Datalog query.
    """
    if isinstance(when_clause, dict):
        q = when_clause.get(_KW_QUERY)
        if isinstance(q, Keyword):
            return q.name
        if isinstance(q, str):
            return q.lstrip(":")
    return None


def _bind_remedies(remedies_path: Path, query_rows: list[dict]) -> list[dict]:
    """REQ-DATALOG-043: walk `rules/remedies.edn`; for any `defremedy`
    whose `:when {:query :Q###}` references a `defquery` name that
    appears in `query_rows`, materialise `{:rows N :propose ...}` into
    the remedy's `:propose` action surface. Remedies whose `:when`
    does not reference a query pass through unchanged.
    """
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


def translate(verdict_path: Path, out_path: Path, remedies_path: Path | None = None) -> None:
    if not verdict_path.exists():
        raise FileNotFoundError(verdict_path)
    payload = read_edn_file(verdict_path)
    # Accept :verdict (legacy) or :status (post-Phase-I).
    verdict_raw = payload.get(_KW_VERDICT)
    if verdict_raw is None:
        verdict_raw = payload.get(_KW_STATUS, "unknown")
    verdict_str = _str_verdict(verdict_raw)
    queries = _query_rows(payload, _KW_QUERIES)
    cozo_defects = _query_rows(payload, _KW_COZO_DEFECTS)
    # Default to the canonical `rules/remedies.edn` location next to
    # the project root when the caller doesn't override.
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
        "remedies": remedies,
        "produced_at": dt.datetime.now(dt.UTC).isoformat(),
        "verifier_version": FORGE_BERMUDA_VERSION,
    }
    if verdict_str == "unknown":
        result["reason"] = payload.get(_KW_REASON, "unknown") or "unknown"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8", newline="\n",
    )


_MANUSCRIPT_ANNOTATIONS_SCHEMA_VERSION = 1


def emit_manuscript_annotations(
    verdict: dict,
    source_path: str,
    out_path: Path,
    source_bytes: bytes | None = None,
) -> None:
    """REQ-PUB-040: emit `manuscript-annotations.json` mapping each
    verdict defect's claim_id to a source span + severity + message.

    `verdict` is a dict-shaped verdict (JSON-style; the EDN keyword
    keys must already have been normalised to plain strings). The
    expected keys are:

      - `defects`: list of dicts each carrying at minimum
        `claim_id`, `source_span` (`[start, end]`), `severity`,
        `message`, `defect_confidence`. Optional keys
        `declared_severity`, `defect_id`, `constraint_id`,
        `see_also` (a list of similar claim ids — Phase Q's
        `:semantic-neighbours`) are passed through when present.

    `source_path` is recorded verbatim in the JSON and is what the
    renderer uses to locate the markdown on disk. `source_bytes`, if
    supplied, is hashed with sha256 and stored in `source_sha256`
    so the renderer can detect stale spans (REQ-PUB-043).
    """
    defects = verdict.get("defects", []) or []
    annotations: list[dict] = []
    for d in defects:
        if not isinstance(d, dict):
            continue
        span = d.get("source_span")
        if not (isinstance(span, (list, tuple)) and len(span) == 2):
            continue
        entry: dict = {
            "claim_id": str(d.get("claim_id", "")),
            "source_span": [int(span[0]), int(span[1])],
            "severity": str(d.get("severity", "advisory")),
            "message": str(d.get("message", "")),
            "defect_confidence": float(d.get("defect_confidence", 0.0)),
        }
        for opt_key in ("declared_severity", "defect_id", "constraint_id"):
            if opt_key in d and d[opt_key] is not None:
                entry[opt_key] = str(d[opt_key])
        see_also = d.get("see_also")
        if isinstance(see_also, (list, tuple)) and see_also:
            entry["see_also"] = [str(x) for x in see_also]
        annotations.append(entry)
    payload: dict = {
        "version": _MANUSCRIPT_ANNOTATIONS_SCHEMA_VERSION,
        "source_path": str(source_path),
        "annotations": annotations,
    }
    if source_bytes is not None:
        payload["source_sha256"] = hashlib.sha256(source_bytes).hexdigest()
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
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
