"""Translate the verifier's verdict.edn into book-qa's verification-defects.json.

The output format is consumed by book-qa.lint_artifact.lint_d13. See
docs/specs/2026-05-14-bermuda-verifier-design.md § "book-qa D13 hook".

Reads verdict.edn as real EDN (Keyword-keyed map). Writes
verification-defects.json as JSON (book-qa reads JSON).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path
from typing import Iterable, Sequence

# scripts/__init__.py extends this package's __path__ to include forge's
# scripts/ dir, so the imports below resolve to neurosym-forge's modules.
from scripts._edn_reader import Keyword  # noqa: E402
from scripts._io import read_edn_file  # noqa: E402

FORGE_BERMUDA_VERSION = "bermuda 0.1.0 / neurosym-forge 0.2.0"

# REQ-CONFIDENCE-041: env var override for the advisory-downgrade threshold.
DEFAULT_CONFIDENCE_THRESHOLD = 0.5
_CONFIDENCE_THRESHOLD_ENV = "VERIFIER_CONFIDENCE_THRESHOLD"

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
_KW_DEFECTS = Keyword("defects")
_KW_SEVERITY = Keyword("severity")
_KW_CHAIN = Keyword("chain")
_KW_CONFIDENCE = Keyword("confidence")


def _kw_to_str(v: object) -> str:
    if isinstance(v, Keyword):
        return v.name
    return str(v) if v is not None else ""


def _resolve_threshold(threshold: float | None) -> float:
    """Pick the active downgrade threshold.

    Precedence: explicit `threshold` arg > `VERIFIER_CONFIDENCE_THRESHOLD`
    env var > `DEFAULT_CONFIDENCE_THRESHOLD` (0.5).
    """
    if threshold is not None:
        return float(threshold)
    env = os.environ.get(_CONFIDENCE_THRESHOLD_ENV)
    if env is not None and env != "":
        try:
            return float(env)
        except ValueError:
            pass
    return DEFAULT_CONFIDENCE_THRESHOLD


def compute_defect_confidence(chain_atoms: Sequence[dict] | Iterable[dict]) -> float:
    """REQ-CONFIDENCE-040: defect confidence = min of unsat-core atom confidences.

    The min is taken over the *distinct* claim ids in the chain (duplicate
    references to the same claim do not alter the result). Each chain entry
    may be a Keyword-keyed dict (as read off an EDN verdict) or a plain
    string-keyed dict (as built by callers in Python).
    """
    seen: dict[str, float] = {}
    for atom in chain_atoms:
        if not isinstance(atom, dict):
            continue
        cid = atom.get(_KW_ID) if _KW_ID in atom else atom.get("id")
        conf = atom.get(_KW_CONFIDENCE) if _KW_CONFIDENCE in atom else atom.get("confidence")
        if conf is None:
            conf = 1.0
        cid_str = str(cid) if cid is not None else f"__anon_{id(atom)}"
        prev = seen.get(cid_str)
        if prev is None or float(conf) < prev:
            seen[cid_str] = float(conf)
    if not seen:
        return 1.0
    return min(seen.values())


def apply_confidence_downgrade(
    defect: dict, threshold: float | None = None,
) -> None:
    """REQ-CONFIDENCE-041: downgrade severity to 'advisory' when every atom
    in the defect's unsat core is strictly below the active threshold.

    Mutates `defect` in place. `declared_severity` preserves the original
    severity.

    - If the defect carries a `chain` of `{id, confidence}` atoms, the
      downgrade fires only when every atom is below threshold (one
      high-confidence anchor preserves the declared severity).
    - Without a chain, the bare `defect_confidence` gates the downgrade.
    """
    t = _resolve_threshold(threshold)
    declared = defect.get("severity", "critical")
    defect.setdefault("declared_severity", declared)
    chain = defect.get("chain")
    if chain:
        all_below = all(float(a.get("confidence", 1.0)) < t for a in chain)
        if all_below:
            defect["severity"] = "advisory"
        return
    dc = defect.get("defect_confidence", 1.0)
    if float(dc) < t:
        defect["severity"] = "advisory"


def compute_verdict_confidence(defects: Sequence[dict] | Iterable[dict]) -> float:
    """REQ-CONFIDENCE-042: verdict confidence = geometric mean of defect
    confidences. Empty defect set => 1.0.
    """
    confidences = [
        float(d.get("defect_confidence", 1.0))
        for d in defects
        if isinstance(d, dict)
    ]
    if not confidences:
        return 1.0
    product = 1.0
    for c in confidences:
        product *= c
    return product ** (1.0 / len(confidences))


def _chain_from_verdict_defect(raw: dict) -> list[dict]:
    """Pull the unsat-core chain off a verdict-shaped defect entry."""
    chain = raw.get(_KW_CHAIN) or raw.get("chain") or []
    if chain:
        return list(chain)
    bare = raw.get(_KW_CORE) or raw.get("core") or []
    return [{"id": cid, "confidence": 1.0} for cid in bare]


def _build_defects(payload: dict) -> list[dict]:
    """Normalise verdict-shaped defects into JSON-friendly dicts, attach
    `defect_confidence`, and apply the advisory-downgrade rule.
    """
    raw_defects = payload.get(_KW_DEFECTS) or payload.get("defects") or []
    out: list[dict] = []
    for raw in raw_defects:
        if not isinstance(raw, dict):
            continue
        chain = _chain_from_verdict_defect(raw)
        dc = compute_defect_confidence(chain)
        entry: dict = {
            "id": str(raw.get(_KW_ID, raw.get("id", ""))),
            "severity": _kw_to_str(raw.get(_KW_SEVERITY, raw.get("severity", "critical"))),
            "defect_confidence": dc,
            "chain": [
                {
                    "id": str(a.get(_KW_ID, a.get("id", ""))),
                    "confidence": float(
                        a.get(_KW_CONFIDENCE, a.get("confidence", 1.0))
                    ),
                }
                for a in chain
                if isinstance(a, dict)
            ],
        }
        apply_confidence_downgrade(entry)
        out.append(entry)
    return out


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
    # REQ-CONFIDENCE-042: surface verdict-level confidence (geometric
    # mean of per-defect confidences; 1.0 if there are no defects).
    all_defects = _build_defects(payload)
    verdict_confidence = compute_verdict_confidence(all_defects)
    result = {
        "verdict": verdict_str,
        "core": list(payload.get(_KW_CORE, [])),
        "explanation": payload.get(_KW_EXPLANATION, "") or "",
        "verified_count": payload.get(_KW_VERIFIED_COUNT, 0),
        "queries": queries,
        "cozo_defects": cozo_defects,
        "verdict_confidence": verdict_confidence,
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
