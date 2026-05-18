"""Phase A.1 tests: REQ-INGEST-040..043."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_summary_includes_per_predicate_counts():
    """REQ-INGEST-040: extract_preview prints a per-predicate fact-count summary."""
    claims_jsonl = PROJECT_ROOT / "fixtures" / "claims_clean.jsonl"
    predicates_edn = PROJECT_ROOT / "rules" / "predicates.edn"
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "extract_preview.py"),
         "--claims", str(claims_jsonl),
         "--predicates", str(predicates_edn),
         "--no-fail-gate"],
        capture_output=True, text=True, check=False,
    )
    out = result.stdout
    for pred in ("vant-hoff-i", "molarity", "temperature-k", "osmotic-pressure-pa"):
        assert pred in out, f"predicate {pred!r} missing from preview output: {out}"
    json_lines = [ln for ln in out.splitlines() if ln.startswith("JSON:")]
    assert json_lines, f"no machine-readable JSON tail in: {out}"
    payload = json.loads(json_lines[0][len("JSON:"):].strip())
    assert "opaque" in payload and "total" in payload and "by_predicate" in payload


def test_threshold_exit_on_high_opaque(tmp_path):
    """REQ-INGEST-041: exit non-zero when OPAQUE fraction exceeds threshold."""
    bad_preds = tmp_path / "predicates.edn"
    bad_preds.write_text(
        '{:version 1, :predicates {:nothing {:patterns ["zzz-impossible"], '
        ':predicate :nothing, :subject :s, :value-kind :real, :word-to-int {}}}}',
        encoding="utf-8",
    )
    claims = PROJECT_ROOT / "fixtures" / "claims_clean.jsonl"
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "extract_preview.py"),
         "--claims", str(claims),
         "--predicates", str(bad_preds),
         "--threshold", "0.10"],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode != 0, f"expected non-zero exit; stdout: {result.stdout}"
    assert "exceeds threshold" in result.stdout


def test_dry_run_prints_edn_without_touching_filesystem(tmp_path):
    """REQ-INGEST-042: --dry-run prints the EDN to stdout and does not write any file."""
    claims = PROJECT_ROOT / "fixtures" / "claims_clean.jsonl"
    preds  = PROJECT_ROOT / "rules" / "predicates.edn"
    work_dir = PROJECT_ROOT / "work"
    # Snapshot the work/ dir contents and mtimes before the run
    before = {p.name: p.stat().st_mtime for p in work_dir.iterdir()} if work_dir.exists() else {}
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "extract_preview.py"),
         "--claims", str(claims), "--predicates", str(preds),
         "--dry-run", "--no-fail-gate"],
        capture_output=True, text=True, check=False,
    )
    # (a) No filesystem write to work/
    after = {p.name: p.stat().st_mtime for p in work_dir.iterdir()} if work_dir.exists() else {}
    assert before == after, f"dry-run modified work/: before={before} after={after}"
    # (b) The would-be EDN is on stdout — must contain :version and :atoms keys
    assert ":version" in result.stdout, "dry-run did not print EDN :version key"
    assert ":atoms" in result.stdout, "dry-run did not print EDN :atoms vector"
    # And the human summary + JSON tail still appear
    assert "Predicate" in result.stdout
    assert "JSON:" in result.stdout


def test_json_tail_parseable():
    """REQ-INGEST-043: stdout contains a 'JSON: {...}' line at the end."""
    claims = PROJECT_ROOT / "fixtures" / "claims_clean.jsonl"
    preds  = PROJECT_ROOT / "rules" / "predicates.edn"
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "extract_preview.py"),
         "--claims", str(claims), "--predicates", str(preds), "--no-fail-gate"],
        capture_output=True, text=True, check=False,
    )
    json_lines = [ln for ln in result.stdout.splitlines() if ln.startswith("JSON:")]
    assert json_lines, f"no JSON line in stdout: {result.stdout}"
    payload = json.loads(json_lines[0][len("JSON:"):].strip())
    assert isinstance(payload["by_predicate"], dict)
