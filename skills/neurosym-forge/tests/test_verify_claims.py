from __future__ import annotations

import subprocess
import sys
from pathlib import Path



def test_prints_commands_for_project(tmp_path: Path, skill_root: Path) -> None:
    project = tmp_path / "v" / "demo"
    project.mkdir(parents=True)
    (project / "package.json").write_text("{}", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-m", "scripts.verify_claims",
         "--project", str(project), "--input", "work/claims.edn"],
        capture_output=True, text=True, cwd=str(skill_root),
    )
    assert result.returncode == 0
    assert "npm run build" in result.stdout
    assert "node cljs-orchestrator/dist/main.js verify" in result.stdout


def test_refuses_when_no_package_json(tmp_path: Path, skill_root: Path) -> None:
    project = tmp_path / "noproject"
    project.mkdir()
    result = subprocess.run(
        [sys.executable, "-m", "scripts.verify_claims",
         "--project", str(project), "--input", "work/claims.edn"],
        capture_output=True, text=True, cwd=str(skill_root),
    )
    assert result.returncode != 0
    assert "package.json" in result.stderr
