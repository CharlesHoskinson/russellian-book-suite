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
    "induce",
    "revise",
    "theory",
)


TIER6_FIXTURES = Path(__file__).parent / "fixtures" / "tier6"


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
    # Also override the attribute on the `scripts` package: when
    # `from scripts import _llm_lift` is evaluated and the real
    # submodule was already imported (e.g. by an earlier "without_phase_p"
    # detection test), Python returns the package attribute rather than
    # consulting sys.modules. Patching the attribute makes the stub win.
    import scripts as _scripts_pkg
    monkeypatch.setattr(_scripts_pkg, "_llm_lift", fake_module, raising=False)

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
    # Mirror the sys.modules stub onto the `scripts` package attribute so
    # `from scripts import _semantic_index` in forge_cli picks up the fake
    # even when the real submodule was imported earlier by the
    # "without_phase_q" detection test.
    import scripts as _scripts_pkg
    monkeypatch.setattr(_scripts_pkg, "_semantic_index", fake_module, raising=False)

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


# ---------------------------------------------------------------------------
# REQ-AUTHOR-045 — error UX
# ---------------------------------------------------------------------------


def test_add_constraint_missing_project_root(runner: CliRunner, tmp_path: Path) -> None:
    """Pointing at a directory without rules/booklogic/constraints.edn surfaces a clean error."""
    bare = tmp_path / "no-rules"
    bare.mkdir()
    result = runner.invoke(
        forge_cli.cli,
        [
            "add-constraint",
            str(bare),
            "--non-interactive",
            "--id", ":C1",
            "--backend", ":z3",
            "--scope", ":subject",
            "--assert", "(>= x 1)",
            "--on-unsat-defect", ":D1",
            "--on-unsat-severity", ":critical",
            "--skip-ci",
        ],
    )
    assert result.exit_code != 0
    assert "ERROR" in result.output or "constraints.edn" in result.output


def test_framework_error_renders_user_message_no_traceback(
    runner: CliRunner, tmp_path: Path
) -> None:
    """A framework error surfaces as the four-line interpretive message."""
    bare = tmp_path / "bare"
    bare.mkdir()
    result = runner.invoke(
        forge_cli.cli,
        [
            "add-constraint",
            str(bare),
            "--non-interactive",
            "--id", ":C1",
            "--backend", ":z3",
            "--scope", ":subject",
            "--assert", "(>= x 1)",
            "--on-unsat-defect", ":D1",
            "--on-unsat-severity", ":critical",
            "--skip-ci",
        ],
    )
    assert result.exit_code != 0
    assert "ERROR:" in result.output
    assert "What likely happened" in result.output
    assert "Likely fix" in result.output
    assert "Reference" in result.output
    assert "--debug" in result.output
    assert "Traceback (most recent call last)" not in result.output


def test_debug_flag_re_enables_traceback(runner: CliRunner, tmp_path: Path) -> None:
    bare = tmp_path / "bare"
    bare.mkdir()
    result = runner.invoke(
        forge_cli.cli,
        [
            "--debug",
            "add-constraint",
            str(bare),
            "--non-interactive",
            "--id", ":C1",
            "--backend", ":z3",
            "--scope", ":subject",
            "--assert", "(>= x 1)",
            "--on-unsat-defect", ":D1",
            "--on-unsat-severity", ":critical",
            "--skip-ci",
        ],
    )
    assert result.exit_code != 0
    assert "Traceback" in result.output or result.exc_info is not None


# ---------------------------------------------------------------------------
# Tier 6 — induce (REQ-AUTHOR-050, 051, 054, 055)
# ---------------------------------------------------------------------------


def _seed_inducible_project(tmp_path: Path) -> Path:
    """Seed a project that doesn't yet have an induced theory (pre-induce)."""
    root = tmp_path / "inducible"
    (root / "rules" / "booklogic").mkdir(parents=True)
    (root / "work").mkdir(parents=True)
    return root


def _fake_nbb_success(monkeypatch: pytest.MonkeyPatch, project: Path) -> None:
    """Patch _run_nbb_induce to write the fixture sidecar and return 0."""

    def _fake(_root: Path, _folds: int, _budget: float | None) -> subprocess.CompletedProcess[str]:
        booklogic = project / "rules" / "booklogic"
        booklogic.mkdir(parents=True, exist_ok=True)
        (booklogic / "induced-theory.edn").write_text(
            (TIER6_FIXTURES / "induced-theory.edn").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        (booklogic / "induced-theory.prov.edn").write_text(
            (TIER6_FIXTURES / "induced-theory.prov.edn").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(
            args=["nbb"], returncode=0, stdout="orchestrator ok\n", stderr="",
        )

    monkeypatch.setattr(forge_cli, "_run_nbb_induce", _fake)


def test_induce_subcommand_exposed(runner: CliRunner) -> None:
    """REQ-AUTHOR-050: forge --help lists the induce subcommand."""
    result = runner.invoke(forge_cli.cli, ["--help"])
    assert result.exit_code == 0, result.output
    assert "induce" in result.output

    sub_help = runner.invoke(forge_cli.cli, ["induce", "--help"])
    assert sub_help.exit_code == 0
    assert "Usage" in sub_help.output


def test_induce_happy_path(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """REQ-AUTHOR-051, 055: forge induce writes both artifacts + prints summary."""
    project = _seed_inducible_project(tmp_path)
    (project / "work" / "_semantic_index.bin").write_bytes(b"\x00")
    _fake_nbb_success(monkeypatch, project)

    result = runner.invoke(forge_cli.cli, ["induce", str(project)])
    assert result.exit_code == 0, result.output

    assert (project / "rules" / "booklogic" / "induced-theory.edn").exists()
    assert (project / "rules" / "booklogic" / "induced-theory.prov.edn").exists()

    assert "Induction complete:" in result.output
    assert "3 rule(s)" in result.output
    assert "Top-3 highest-entrenchment rules:" in result.output
    assert "herd-immunity-threshold" in result.output
    assert "Total cost:" in result.output


def test_induce_default_folds_is_five(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """REQ-AUTHOR-051: --folds defaults to 5; --help confirms it."""
    project = _seed_inducible_project(tmp_path)
    (project / "work" / "_semantic_index.bin").write_bytes(b"\x00")

    seen_folds: list[int] = []

    def _capture(_root: Path, folds: int, _budget: float | None) -> subprocess.CompletedProcess[str]:
        seen_folds.append(folds)
        (project / "rules" / "booklogic" / "induced-theory.edn").write_text(
            (TIER6_FIXTURES / "induced-theory.edn").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        (project / "rules" / "booklogic" / "induced-theory.prov.edn").write_text(
            (TIER6_FIXTURES / "induced-theory.prov.edn").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(args=["nbb"], returncode=0, stdout="", stderr="")

    monkeypatch.setattr(forge_cli, "_run_nbb_induce", _capture)

    result = runner.invoke(forge_cli.cli, ["induce", str(project)])
    assert result.exit_code == 0, result.output
    assert seen_folds == [5]

    sub_help = runner.invoke(forge_cli.cli, ["induce", "--help"])
    assert "default 5" in sub_help.output or "default: 5" in sub_help.output.lower()


def test_induce_warns_when_semantic_index_absent(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """REQ-AUTHOR-054: missing _semantic_index emits a warning but still runs."""
    project = _seed_inducible_project(tmp_path)
    _fake_nbb_success(monkeypatch, project)

    result = runner.invoke(forge_cli.cli, ["induce", str(project)])
    assert result.exit_code == 0, result.output
    assert "warning: semantic index not found" in result.output
    assert "pure-symbolic induction" in result.output


def test_induce_pipeline_error_renders_user_message(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """REQ-AUTHOR-055: nbb non-zero exit → InductionPipelineError → ERROR block."""
    monkeypatch.delenv("FORGE_DEBUG", raising=False)
    project = _seed_inducible_project(tmp_path)
    (project / "work" / "_semantic_index.bin").write_bytes(b"\x00")

    def _fail(_root: Path, _folds: int, _budget: float | None) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=["nbb"], returncode=2, stdout="", stderr="grammar enforcer rejected 0/0\n",
        )

    monkeypatch.setattr(forge_cli, "_run_nbb_induce", _fail)
    result = runner.invoke(forge_cli.cli, ["induce", str(project)])
    assert result.exit_code != 0
    assert "ERROR:" in result.output
    assert "induction" in result.output.lower() or "nbb" in result.output


# ---------------------------------------------------------------------------
# Tier 6 — revise (REQ-AUTHOR-050, 052, 055)
# ---------------------------------------------------------------------------


def _seed_tier6_project(tmp_path: Path, with_sidecar: bool = True) -> Path:
    """Seed a tier6-shaped project tree from fixtures/tier6/."""
    root = tmp_path / "tier6-project"
    booklogic = root / "rules" / "booklogic"
    booklogic.mkdir(parents=True)
    (root / "work").mkdir(parents=True)
    (booklogic / "induced-theory.edn").write_text(
        (TIER6_FIXTURES / "induced-theory.edn").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    if with_sidecar:
        (booklogic / "induced-theory.prov.edn").write_text(
            (TIER6_FIXTURES / "induced-theory.prov.edn").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
    return root


class _FakeRevisionReport:
    """Stand-in for Phase Z's RevisionReport dataclass."""

    def __init__(
        self,
        rules_affected: int = 2,
        status_counts: dict[str, int] | None = None,
        transitions: list[tuple[str, str, str]] | None = None,
        full_quarantine_warning: bool = False,
    ) -> None:
        self.rules_affected = rules_affected
        self.status_counts = status_counts or {
            ":active": 1, ":tentative": 1, ":quarantined": 1,
        }
        self.transitions = transitions or [
            (":induced/herd-immunity-threshold", ":active", ":tentative"),
            (":induced/vaccine-efficacy-r0", ":tentative", ":quarantined"),
        ]
        self.full_quarantine_warning = full_quarantine_warning


def _stub_agm_module(
    monkeypatch: pytest.MonkeyPatch,
    report_factory,
) -> None:
    """Install a stub scripts._agm_revision module returning report_factory()."""
    import types

    fake = types.ModuleType("scripts._agm_revision")

    def revise_theory(
        induced_path: Path,
        prov_path: Path,
        retracted_docs: list[str],
        contradicting_atoms: list[str],
    ) -> _FakeRevisionReport:
        return report_factory(retracted_docs, contradicting_atoms)

    fake.revise_theory = revise_theory  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "scripts._agm_revision", fake)
    import scripts as _scripts_pkg
    monkeypatch.setattr(_scripts_pkg, "_agm_revision", fake, raising=False)


def test_revise_subcommand_exposed(runner: CliRunner) -> None:
    """REQ-AUTHOR-050: forge revise --help renders non-trivial help."""
    result = runner.invoke(forge_cli.cli, ["revise", "--help"])
    assert result.exit_code == 0
    assert "Usage" in result.output
    assert "retracted-paper" in result.output
    assert "contradicting-atom" in result.output


def test_revise_happy_path(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """REQ-AUTHOR-052, 055: forge revise prints the RevisionReport."""
    project = _seed_tier6_project(tmp_path)
    _stub_agm_module(monkeypatch, lambda r, c: _FakeRevisionReport())

    result = runner.invoke(
        forge_cli.cli,
        ["revise", str(project), "--retracted-paper", "pmid:12345"],
    )
    assert result.exit_code == 0, result.output
    assert "Revision summary:" in result.output
    assert "Rules affected:" in result.output
    assert "Status transitions:" in result.output
    assert "herd-immunity-threshold" in result.output


def test_revise_requires_at_least_one_input(
    runner: CliRunner, tmp_path: Path
) -> None:
    """REQ-AUTHOR-052, 055: neither flag → RevisionInputError rendered."""
    project = _seed_tier6_project(tmp_path)
    result = runner.invoke(forge_cli.cli, ["revise", str(project)])
    assert result.exit_code != 0
    surfaced = (
        "ERROR:" in result.output
        or "retracted-paper" in result.output
        or "contradicting-atom" in result.output
    )
    assert surfaced, result.output


def test_revise_full_quarantine_warning_banner(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """REQ-AUTHOR-052: RevisionReport.full_quarantine_warning surfaces as a banner."""
    project = _seed_tier6_project(tmp_path)
    _stub_agm_module(
        monkeypatch,
        lambda r, c: _FakeRevisionReport(full_quarantine_warning=True),
    )

    result = runner.invoke(
        forge_cli.cli,
        ["revise", str(project), "--retracted-paper", "pmid:12345"],
    )
    assert result.exit_code == 0, result.output
    assert "WARNING" in result.output
    assert "full quarantine" in result.output.lower()


# ---------------------------------------------------------------------------
# Tier 6 — theory (REQ-AUTHOR-050, 053, 055)
# ---------------------------------------------------------------------------


def test_theory_subcommand_exposed(runner: CliRunner) -> None:
    """REQ-AUTHOR-050: forge theory --help renders non-trivial help."""
    result = runner.invoke(forge_cli.cli, ["theory", "--help"])
    assert result.exit_code == 0
    assert "Usage" in result.output
    assert "--rule" in result.output


def test_theory_aggregate_and_deep_dive(
    runner: CliRunner, tmp_path: Path
) -> None:
    """REQ-AUTHOR-053, 055: forge theory prints aggregate; --rule deep-dives."""
    project = _seed_tier6_project(tmp_path)

    agg = runner.invoke(forge_cli.cli, ["theory", str(project)])
    assert agg.exit_code == 0, agg.output
    assert "Theory summary:" in agg.output
    assert "Rules:" in agg.output
    assert ":active 1" in agg.output
    assert ":tentative 1" in agg.output
    assert ":quarantined 1" in agg.output
    assert "Average entrenchment:" in agg.output
    assert "Top-5 most-cited source documents:" in agg.output
    assert "pmid:12345" in agg.output

    deep = runner.invoke(
        forge_cli.cli,
        ["theory", str(project), "--rule", ":induced/herd-immunity-threshold"],
    )
    assert deep.exit_code == 0, deep.output
    assert "Rule :induced/herd-immunity-threshold" in deep.output
    assert "Entrenchment:" in deep.output
    assert "0.830" in deep.output
    assert "Proposed by:" in deep.output
    assert "Validated by:" in deep.output
    assert "Repair calls:" in deep.output
    assert "c-203" in deep.output


def test_theory_renders_rules_with_missing_sidecar(
    runner: CliRunner, tmp_path: Path
) -> None:
    """REQ-AUTHOR-053, 055: missing sidecar → ERROR block + rule list still rendered."""
    project = _seed_tier6_project(tmp_path, with_sidecar=False)
    result = runner.invoke(forge_cli.cli, ["theory", str(project)])
    assert result.exit_code == 0, result.output
    assert "ERROR:" in result.output
    assert "sidecar" in result.output.lower() or "prov.edn" in result.output
    assert ":induced/herd-immunity-threshold" in result.output
    assert ":induced/vaccine-efficacy-r0" in result.output
    assert ":induced/trial-cohort-size" in result.output


def teardown_module(_module: object) -> None:  # pragma: no cover — env hygiene
    import os
    os.environ.pop("FORGE_DEBUG", None)
