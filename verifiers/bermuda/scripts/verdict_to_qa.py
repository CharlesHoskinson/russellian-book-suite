"""Translate the verifier's verdict.edn into book-qa's verification-defects.json.

The output format is consumed by book-qa.lint_artifact.lint_d13. See
docs/specs/2026-05-14-bermuda-verifier-design.md § "book-qa D13 hook".
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

FORGE_BERMUDA_VERSION = "bermuda 0.1.0 / neurosym-forge 0.2.0"


def translate(verdict_path: Path, out_path: Path) -> None:
    if not verdict_path.exists():
        raise FileNotFoundError(verdict_path)
    payload = json.loads(verdict_path.read_text(encoding="utf-8"))
    result = {
        "verdict": payload.get("verdict", "unknown"),
        "core": list(payload.get("core", [])),
        "explanation": payload.get("explanation", ""),
        "verified_count": payload.get("verified_count", 0),
        "produced_at": dt.datetime.now(dt.UTC).isoformat(),
        "verifier_version": FORGE_BERMUDA_VERSION,
    }
    if payload.get("verdict") == "unknown":
        result["reason"] = payload.get("reason", "unknown")
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
