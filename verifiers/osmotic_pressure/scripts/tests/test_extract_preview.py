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


def test_dry_run_does_not_write_persistent_file(tmp_path):
    """REQ-INGEST-042: --dry-run does not leave an intermediate atoms file on disk."""
    claims = PROJECT_ROOT / "fixtures" / "claims_clean.jsonl"
    preds  = PROJECT_ROOT / "rules" / "predicates.edn"
    # Note where the preview script writes its scratch file
    scratch = PROJECT_ROOT / "work" / "_extract_preview_atoms.edn"
    pre_existed = scratch.exists()
    pre_mtime = scratch.stat().st_mtime if pre_existed else None
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "extract_preview.py"),
         "--claims", str(claims), "--predicates", str(preds),
         "--dry-run", "--no-fail-gate"],
        capture_output=True, text=True, check=False,
    )
    # After dry-run, scratch must either not exist, or be unchanged from before
    if scratch.exists():
        assert pre_existed and scratch.stat().st_mtime == pre_mtime, \
            "dry-run wrote a persistent scratch atoms file"


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
