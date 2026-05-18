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


def translate(verdict_path: Path, out_path: Path) -> None:
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
    result = {
        "verdict": verdict_str,
        "core": list(payload.get(_KW_CORE, [])),
        "explanation": payload.get(_KW_EXPLANATION, "") or "",
        "verified_count": payload.get(_KW_VERIFIED_COUNT, 0),
        "queries": queries,
        "cozo_defects": cozo_defects,
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
    args = ap.parse_args(argv)
    translate(Path(args.verdict), Path(args.out))
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
