"""End-to-end Python driver for the Bermuda verifier.

Phases:
  1. ingest             Prefer <workspace>/analysis/ingest-trace.edn (the
                        symbolic event stream from book-knowledge); fall back
                        to claims/ledger.jsonl for legacy workspaces.
                        Output: work/claims.edn
  2. extract_prose      book/releases/N/chapter-bundles/ -> work/prose-facts.edn
  3. verify             (CLJS+Rust) work/{claims, prose-facts}.edn -> work/verdict.edn
                        Skipped when stub_verifier=True; emits a stub verdict.
  4. verdict_to_qa      work/verdict.edn -> <workspace>/qa/verification-defects.json

REQ-TRACE-001, REQ-TRACE-002, REQ-TRACE-004: trace-aware Phase-1 dispatch.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

# scripts/__init__.py extends this package's __path__ to include forge's
# scripts/ dir, so the imports below resolve to neurosym-forge's modules.
from scripts._edn_reader import Keyword  # noqa: E402
from scripts._io import write_edn_file  # noqa: E402

from scripts.extract_prose import extract_release
from scripts.ingest_ledger import ingest
from scripts.trace_to_ledger import (
    project_trace_to_ledger_rows,
    read_trace,
)
from scripts.verdict_to_qa import translate

_KW_VERSION = Keyword("version")
_KW_VERDICT = Keyword("verdict")
_KW_CORE = Keyword("core")
_KW_EXPLANATION = Keyword("explanation")
_KW_VERIFIED_COUNT = Keyword("verified-count")
_KW_ATOMS = Keyword("atoms")


def _materialise_trace_as_ledger(workspace: Path, work: Path) -> Path | None:
    """If <workspace>/analysis/ingest-trace.edn exists, project it to a
    synthetic JSONL ledger inside `work/` and return that path. Otherwise
    return None so the caller can fall back to the legacy ledger.jsonl."""
    trace_path = workspace / "analysis" / "ingest-trace.edn"
    if not trace_path.exists():
        return None
    trace = read_trace(trace_path)
    rows = project_trace_to_ledger_rows(trace)
    synth = work / "ledger-from-trace.jsonl"
    with synth.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")
    return synth


def run(workspace: Path, release_version: str, project_root: Path,
        stub_verifier: bool = False,
        stub_verdict: str = "sat",
        stub_core: list[str] | None = None) -> int:
    work = project_root / "work"
    work.mkdir(parents=True, exist_ok=True)

    # Phase 1: ingest — prefer the symbolic trace, fall back to legacy ledger.
    synth_ledger = _materialise_trace_as_ledger(workspace, work)
    if synth_ledger is not None:
        ledger = synth_ledger
    else:
        ledger = workspace / "claims" / "ledger.jsonl"
    claims_edn = work / "claims.edn"
    ingest(ledger, project_root / "rules" / "predicates.edn", claims_edn)

    # Phase 2: prose
    bundles = workspace / "book" / "releases" / release_version / "chapter-bundles"
    prose_edn = work / "prose-facts.edn"
    if bundles.exists():
        extract_release(bundles, prose_edn)
    else:
        write_edn_file(prose_edn, {_KW_VERSION: 1, _KW_ATOMS: []})

    # Phase 3: verify
    verdict_edn = work / "verdict.edn"
    if stub_verifier:
        write_edn_file(verdict_edn, {
            _KW_VERSION: 1,
            _KW_VERDICT: Keyword(stub_verdict),
            _KW_CORE: stub_core or [],
            _KW_EXPLANATION: "stub" if stub_verdict == "unsat" else "",
            _KW_VERIFIED_COUNT: 0,
        })
    else:
        main_js = project_root / "cljs-orchestrator" / "dist" / "main.js"
        if not main_js.exists():
            print(f"verifier not built ({main_js}); run npm run build first",
                  file=sys.stderr)
            return 2
        subprocess.run(
            ["node", str(main_js), "verify", str(claims_edn), str(verdict_edn)],
            check=True, cwd=str(project_root),
        )

    # Phase 4: verdict -> qa
    qa_dir = workspace / "qa"
    qa_dir.mkdir(parents=True, exist_ok=True)
    translate(verdict_edn, qa_dir / "verification-defects.json")
    print(f"verification complete: verdict={stub_verdict if stub_verifier else 'real'}")
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--release", required=True)
    ap.add_argument("--stub", action="store_true",
                    help="Stub the Rust verifier (for CI / when toolchain missing)")
    ap.add_argument("--stub-verdict", default="sat", choices=["sat", "unsat", "unknown"])
    args = ap.parse_args(argv)
    project_root = Path(__file__).resolve().parent.parent
    rc = run(
        workspace=Path(args.workspace),
        release_version=args.release,
        project_root=project_root,
        stub_verifier=args.stub,
        stub_verdict=args.stub_verdict,
    )
    return rc


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
