"""Tests for ``scripts.forge_cli`` (REQ-AUTHOR-040..046)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

from scripts import forge_cli


SUBCOMMANDS = (
    "add-constraint",
    "suggest-lifts",
    "explain-defect",
    "similar",
    "render",
)


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture()
def fake_project(tmp_path: Path) -> Path:
    """A minimal project tree the CLI can operate on."""
    root = tmp_path / "project"
    (root / "rules" / "booklogic").mkdir(parents=True)
    (root / "work").mkdir(parents=True)
    (root / "rules" / "booklogic" / "constraints.edn").write_text(
        ";; constraints.edn\n{:forms []}\n", encoding="utf-8"
    )
    return root


# ---------------------------------------------------------------------------
# REQ-AUTHOR-040 — group + 5 subcommands exposed
# ---------------------------------------------------------------------------


def test_all_subcommands_exposed(runner: CliRunner) -> None:
    result = runner.invoke(forge_cli.cli, ["--help"])
    assert result.exit_code == 0, result.output
    for sub in SUBCOMMANDS:
        assert sub in result.output


def test_module_invocation_help_lists_subcommands() -> None:
    """Invoking ``python -m scripts.forge_cli --help`` works (entry-point shape)."""
    skill_root = Path(forge_cli.__file__).resolve().parent.parent
    result = subprocess.run(
        [sys.executable, "-m", "scripts.forge_cli", "--help"],
        cwd=str(skill_root),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    for sub in SUBCOMMANDS:
        assert sub in result.stdout


def test_each_subcommand_has_help(runner: CliRunner) -> None:
    """Each subcommand exposes non-trivial --help text."""
    for sub in SUBCOMMANDS:
        result = runner.invoke(forge_cli.cli, [sub, "--help"])
        assert result.exit_code == 0, f"{sub}: {result.output}"
        assert "Usage" in result.output
        assert "--help" in result.output


def test_forge_cli_exposes_main_callable() -> None:
    """The entry point declared in pyproject.toml is callable."""
    assert callable(forge_cli.main)
    assert callable(forge_cli.cli)


def test_pyproject_declares_forge_entry_point() -> None:
    skill_root = Path(forge_cli.__file__).resolve().parent.parent
    pyproject = (skill_root / "pyproject.toml").read_text(encoding="utf-8")
    assert "[project.scripts]" in pyproject
    assert 'forge = "scripts.forge_cli:main"' in pyproject
    assert "click" in pyproject


# ---------------------------------------------------------------------------
# REQ-AUTHOR-041 — add-constraint non-interactive
# ---------------------------------------------------------------------------


def test_add_constraint_appends_and_skips_ci(runner: CliRunner, fake_project: Path) -> None:
    """Non-interactive add with --skip-ci writes the constraint and returns 0."""
    result = runner.invoke(
        forge_cli.cli,
        [
            "add-constraint",
            str(fake_project),
            "--non-interactive",
            "--id", ":C001-test",
            "--backend", ":z3",
            "--scope", ":subject",
            "--assert", "(>= (:trial-n ?s) 10)",
            "--on-unsat-defect", ":D001-low-n",
            "--on-unsat-severity", ":advisory",
            "--skip-ci",
        ],
    )
    assert result.exit_code == 0, result.output
    body = (fake_project / "rules" / "booklogic" / "constraints.edn").read_text(encoding="utf-8")
    assert "(defconstraint :C001-test" in body
    assert ":backend :z3" in body
    assert "(:trial-n ?s)" in body
    assert ":defect :D001-low-n" in body
    assert ":severity :advisory" in body


def test_add_constraint_non_interactive_missing_required(
    runner: CliRunner, fake_project: Path
) -> None:
    """--non-interactive without --id raises a UsageError (no prompt fallback)."""
    result = runner.invoke(
        forge_cli.cli,
        ["add-constraint", str(fake_project), "--non-interactive", "--skip-ci"],
    )
    assert result.exit_code != 0
    assert "--id" in result.output or "id" in result.output


def test_add_constraint_make_ci_failure_rolls_back(
    runner: CliRunner, fake_project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """make-ci non-zero rolls back the appended constraint."""
    original_body = (fake_project / "rules" / "booklogic" / "constraints.edn").read_text(
        encoding="utf-8"
    )

    def fake_run(project_root: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=["make", "ci"], returncode=1, stdout="", stderr="boom: predicate unknown",
        )

    monkeypatch.setattr(forge_cli, "_run_make_ci", fake_run)
    result = runner.invoke(
        forge_cli.cli,
        [
            "add-constraint",
            str(fake_project),
            "--non-interactive",
            "--id", ":C999-bad",
            "--backend", ":z3",
            "--scope", ":subject",
            "--assert", "(:nonexistent ?s)",
            "--on-unsat-defect", ":D999",
            "--on-unsat-severity", ":critical",
        ],
    )
    assert result.exit_code != 0
    after = (fake_project / "rules" / "booklogic" / "constraints.edn").read_text(encoding="utf-8")
    assert after == original_body


# ---------------------------------------------------------------------------
# REQ-AUTHOR-042 — suggest-lifts (Phase P optional)
# ---------------------------------------------------------------------------


def test_suggest_lifts_without_phase_p(runner: CliRunner, fake_project: Path) -> None:
    """When scripts._llm_lift is unavailable, the subcommand exits with a pointer."""
    try:
        import scripts._llm_lift  # type: ignore[import-not-found]  # noqa: F401
        pytest.skip("Phase P module is present — exercise the integration test instead.")
    except ImportError:
        pass

    result = runner.invoke(
        forge_cli.cli,
        ["suggest-lifts", "C001", "--project-root", str(fake_project)],
    )
    assert result.exit_code == 2
    assert "Phase P" in result.output


def test_suggest_lifts_emits_candidates_no_auto_merge(
    runner: CliRunner, fake_project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With a stubbed Phase P module, candidate deflift forms reach stdout."""
    claims_path = fake_project / "work" / "claims.jsonl"
    claims_path.write_text(
        json.dumps({"claim_id": "C001", "canonical_text": "37 patients enrolled"}) + "\n",
        encoding="utf-8",
    )

    import types

    fake_module = types.ModuleType("scripts._llm_lift")

    class _Stub:
        def suggest_lifts(self, _text: str, k: int = 3) -> list[str]:
            return [
                "(deflift L001\n  :from :claim/canonical-text\n  :when \"(?P<v>\\\\d+) patients\")",
            ][:k]

    fake_module.get_provider = lambda: _Stub()  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "scripts._llm_lift", fake_module)

    result = runner.invoke(
        forge_cli.cli,
        ["suggest-lifts", "C001", "--project-root", str(fake_project), "--k", "1"],
    )
    assert result.exit_code == 0, result.output
    assert "deflift" in result.output
    assert "Not auto-merged" in result.output
    lifts = fake_project / "rules" / "booklogic" / "lifts.edn"
    assert not lifts.exists()


# ---------------------------------------------------------------------------
# REQ-AUTHOR-043 — explain-defect
# ---------------------------------------------------------------------------


def _seed_verdict_and_claims(project_root: Path) -> None:
    """Populate work/verdict.json + work/claims.jsonl + a source span file."""
    src = project_root / "manuscript" / "chap-3.md"
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_text(
        "Line 1\nLine 2\nLine 3 — Mizuno 2008 enrolled 37 patients\nLine 4\nLine 5\n",
        encoding="utf-8",
    )

    verdict = {
        "defects": [
            {
                "id": "D042",
                "constraint": "X042-trial-n",
                "severity": "hard",
                "declared_severity": "hard",
                "defect_confidence": 0.92,
                "message": "trial patient counts disagree",
                "unsat_core": ["C042", "C087"],
                "span": {"path": "manuscript/chap-3.md", "line": 3},
            }
        ]
    }
    (project_root / "work" / "verdict.json").write_text(json.dumps(verdict), encoding="utf-8")

    claims_path = project_root / "work" / "claims.jsonl"
    with claims_path.open("w", encoding="utf-8") as fh:
        fh.write(json.dumps({
            "claim_id": "C042", "canonical_text": "Mizuno (2008) enrolled 37 patients",
            "confidence": 0.95,
        }) + "\n")
        fh.write(json.dumps({
            "claim_id": "C087", "canonical_text": "The Mizuno 2008 cohort of 42 patients",
            "confidence": 0.92,
        }) + "\n")


def test_explain_defect_renders_chain_and_interpretation(
    runner: CliRunner, fake_project: Path
) -> None:
    _seed_verdict_and_claims(fake_project)
    result = runner.invoke(
        forge_cli.cli,
        ["explain-defect", "D042", "--project-root", str(fake_project)],
    )
    assert result.exit_code == 0, result.output
    assert "D042" in result.output
    assert "X042-trial-n" in result.output
    assert "C042" in result.output and "C087" in result.output
    assert "0.95" in result.output
    assert ">> 3:" in result.output
    assert "Interpretation" in result.output


def test_explain_defect_missing_verdict(runner: CliRunner, fake_project: Path) -> None:
    result = runner.invoke(
        forge_cli.cli,
        ["explain-defect", "D999", "--project-root", str(fake_project)],
    )
    assert result.exit_code != 0
    # The error surface is tightened by the REQ-AUTHOR-045 decorator below;
    # at this point we only require a non-zero exit and either a clean
    # rendered ERROR block (decorator wired) or a FileNotFoundError raised
    # to the runner's `exception` capture.
    surfaced = "verdict.edn" in result.output or "ERROR" in result.output
    assert surfaced or isinstance(result.exception, FileNotFoundError)


# ---------------------------------------------------------------------------
# REQ-AUTHOR-044 — similar (Phase Q optional) + render (Phase T optional)
# ---------------------------------------------------------------------------


def test_similar_without_phase_q(runner: CliRunner, fake_project: Path) -> None:
    try:
        import scripts._semantic_index  # type: ignore[import-not-found]  # noqa: F401
        pytest.skip("Phase Q module is present — exercise the integration test instead.")
    except ImportError:
        pass

    result = runner.invoke(
        forge_cli.cli,
        ["similar", "C001", "--project-root", str(fake_project)],
    )
    assert result.exit_code == 2
    assert "Phase Q" in result.output


def test_similar_prints_top_k_table(
    runner: CliRunner, fake_project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import types

    fake_module = types.ModuleType("scripts._semantic_index")

    class _FakeIndex:
        @classmethod
        def load(cls, _root: Path) -> "_FakeIndex":
            return cls()

        def similar_claims(self, _claim_id: str, k: int = 5) -> list[dict[str, object]]:
            return [
                {"claim_id": f"C{i:03d}", "score": 0.99 - 0.1 * i,
                 "subject": "trial", "snippet": "snippet text"} for i in range(k)
            ]

    fake_module.SemanticIndex = _FakeIndex  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "scripts._semantic_index", fake_module)

    result = runner.invoke(
        forge_cli.cli,
        ["similar", "C001", "--project-root", str(fake_project), "--k", "3"],
    )
    assert result.exit_code == 0, result.output
    assert "claim_id" in result.output
    assert "score" in result.output
    rows = [line for line in result.output.splitlines() if line.startswith("C0")]
    assert len(rows) == 3


def test_render_without_phase_t(runner: CliRunner, fake_project: Path) -> None:
    script_path = Path(forge_cli.__file__).resolve().parent / "render_annotations.py"
    if script_path.exists():
        pytest.skip("Phase T script is present — exercise the integration test instead.")
    result = runner.invoke(
        forge_cli.cli,
        ["render", "--project-root", str(fake_project)],
    )
    assert result.exit_code == 2
    assert "Phase T" in result.output
