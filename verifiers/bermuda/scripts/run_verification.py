"""End-to-end Python driver for the Bermuda verifier.

Phases:
  1. ingest_ledger      claims/ledger.jsonl -> work/claims.edn
  2. extract_prose      book/releases/N/chapter-bundles/ -> work/prose-facts.edn
  3. verify             (CLJS+Rust) work/{claims, prose-facts}.edn -> work/verdict.edn
                        Skipped when stub_verifier=True; emits a stub verdict.
  4. verdict_to_qa      work/verdict.edn -> <workspace>/qa/verification-defects.json
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from scripts.extract_prose import extract_release
from scripts.ingest_ledger import ingest
from scripts.verdict_to_qa import translate


def run(workspace: Path, release_version: str, project_root: Path,
        stub_verifier: bool = False,
        stub_verdict: str = "sat",
        stub_core: list[str] | None = None) -> int:
    work = project_root / "work"
    work.mkdir(parents=True, exist_ok=True)

    # Phase 1: ledger
    ledger = workspace / "claims" / "ledger.jsonl"
    claims_edn = work / "claims.edn"
    ingest(ledger, project_root / "rules" / "predicates.edn", claims_edn)

    # Phase 2: prose
    bundles = workspace / "book" / "releases" / release_version / "chapter-bundles"
    prose_edn = work / "prose-facts.edn"
    if bundles.exists():
        extract_release(bundles, prose_edn)
    else:
        prose_edn.write_text(json.dumps({"version": 1, "atoms": []}), encoding="utf-8")

    # Phase 3: verify
    verdict_edn = work / "verdict.edn"
    if stub_verifier:
        verdict_edn.write_text(json.dumps({
            "version": 1,
            "verdict": stub_verdict,
            "core": stub_core or [],
            "explanation": "stub" if stub_verdict == "unsat" else "",
            "verified_count": 0,
        }), encoding="utf-8")
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
