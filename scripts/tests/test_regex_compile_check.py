"""Test: the gate catches sprint-5 bug #7 (JS-style named group)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "regex-compile-check.py"


def _write_lifts(p: Path, regex: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        '{:forms\n'
        f' [(deflift L001 :from :claim/canonical-text :when "{regex}" :emit (fact))]}}\n',
        encoding="utf-8",
    )


def test_rejects_js_named_groups(tmp_path: Path) -> None:
    bad = tmp_path / "lifts.edn"
    _write_lifts(bad, "(?<v>[0-9]+)")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(bad)],
        capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert "?<" in result.stderr or "named group" in result.stderr.lower()


def test_accepts_python_named_groups(tmp_path: Path) -> None:
    good = tmp_path / "lifts.edn"
    _write_lifts(good, "(?P<v>[0-9]+)")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(good)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
