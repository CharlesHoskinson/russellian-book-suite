"""Tests for design-intelligence KG projection (REQ-KG-048/053)."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from scripts.cozo_store import CozoStore
from scripts.project_design_kg import (
    extract_ci_jobs,
    extract_ci_workflows,
    extract_design_kg_snapshot,
    extract_design_decisions,
    extract_operator_commands,
    extract_openspec_requirements,
    extract_openspec_scenarios,
    extract_test_cases,
    extract_traceability_links,
    project_design_docs,
    project_design_requirements,
    project_traceability_links,
    project_tests_and_ci,
)

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "assets" / "kg-schema.edn"
FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "design-kg"


def test_extracts_openspec_requirement_with_source_provenance() -> None:
    rows = extract_openspec_requirements(FIXTURE_ROOT)

    assert rows == [
        {
            "id": "openspec:sample-capability:REQ-KG-901",
            "requirement_id": "REQ-KG-901",
            "capability": "sample-capability",
            "status": "fixture",
            "text": (
                "The fixture SHALL expose a deterministic design graph input "
                "that links a requirement, design decision, test case, CI job, "
                "and graphify code node. The fixture implementation source is "
                "`src/fixture.py`."
            ),
            "source_path": "openspec/specs/sample-capability/spec.md",
            "source_line": 5,
        }
    ]


def test_extracts_openspec_scenario_with_source_provenance() -> None:
    rows = extract_openspec_scenarios(FIXTURE_ROOT)

    assert rows == [
        {
            "id": (
                "openspec-scenario:sample-capability:REQ-KG-901:14:"
                "fixture-requirement-is-covered-by-a-test"
            ),
            "requirement_id": "REQ-KG-901",
            "capability": "sample-capability",
            "text": (
                "fixture requirement is covered by a test WHEN the design-KG "
                "extractor reads this fixture THEN it emits a "
                "`design-requirement` row for `REQ-KG-901` AND "
                "`tests/test_fixture_pipeline.py::"
                "test_REQ_KG_901_fixture_requirement` covers it"
            ),
            "source_path": "openspec/specs/sample-capability/spec.md",
            "source_line": 14,
        }
    ]


def test_project_design_requirements_is_read_only_and_idempotent() -> None:
    spec_path = FIXTURE_ROOT / "openspec/specs/sample-capability/spec.md"
    before = spec_path.read_text(encoding="utf-8")

    store = CozoStore.in_memory(schema_path=SCHEMA_PATH)
    project_design_requirements(FIXTURE_ROOT, store)
    project_design_requirements(FIXTURE_ROOT, store)

    rows = store.query(
        "?[id, requirement_id, capability, status, source_path, source_line] := "
        "*design_requirement{id, requirement_id, capability, status, source_path, source_line}"
    )
    scenarios = store.query(
        "?[id, requirement_id, capability, source_path, source_line] := "
        "*design_scenario{id, requirement_id, capability, source_path, source_line}"
    )
    assert rows == [
        [
            "openspec:sample-capability:REQ-KG-901",
            "REQ-KG-901",
            "sample-capability",
            "fixture",
            "openspec/specs/sample-capability/spec.md",
            5,
        ]
    ]
    assert scenarios == [
        [
            "openspec-scenario:sample-capability:REQ-KG-901:14:"
            "fixture-requirement-is-covered-by-a-test",
            "REQ-KG-901",
            "sample-capability",
            "openspec/specs/sample-capability/spec.md",
            14,
        ]
    ]
    assert spec_path.read_text(encoding="utf-8") == before


def test_extracts_requirement_headings_with_em_dash(tmp_path: Path) -> None:
    spec_dir = tmp_path / "openspec" / "specs" / "dash-capability"
    spec_dir.mkdir(parents=True)
    spec_path = spec_dir / "spec.md"
    spec_path.write_text(
        "\n".join(
            [
                "# Capability: dash-capability",
                "",
                "### Requirement: REQ-KG-902 \u2014 Dash style (Ubiquitous)",
                "",
                "The fixture SHALL support legacy heading punctuation.",
            ]
        ),
        encoding="utf-8",
    )

    rows = extract_openspec_requirements(tmp_path)
    assert rows == [
        {
            "id": "openspec:dash-capability:REQ-KG-902",
            "requirement_id": "REQ-KG-902",
            "capability": "dash-capability",
            "status": "accepted",
            "text": "The fixture SHALL support legacy heading punctuation.",
            "source_path": "openspec/specs/dash-capability/spec.md",
            "source_line": 3,
        }
    ]


def test_repo_root_extraction_uses_git_snapshot_not_untracked_files(
    tmp_path: Path,
) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    tracked_dir = tmp_path / "openspec" / "specs" / "tracked"
    tracked_dir.mkdir(parents=True)
    (tracked_dir / "spec.md").write_text(
        "\n".join(
            [
                "# Capability: tracked",
                "",
                "### Requirement: REQ-KG-910 - Tracked only (Ubiquitous)",
                "",
                "The repo-root extractor SHALL read the Git snapshot.",
            ]
        ),
        encoding="utf-8",
    )
    untracked_dir = tmp_path / "openspec" / "specs" / "untracked"
    untracked_dir.mkdir(parents=True)
    (untracked_dir / "spec.md").write_text(
        "\n".join(
            [
                "# Capability: untracked",
                "",
                "### Requirement: REQ-KG-911 - Untracked ignored (Ubiquitous)",
                "",
                "The repo-root extractor SHALL ignore untracked scratch files.",
            ]
        ),
        encoding="utf-8",
    )
    subprocess.run(
        ["git", "add", "openspec/specs/tracked/spec.md"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    rows = extract_openspec_requirements(tmp_path)

    assert [row["requirement_id"] for row in rows] == ["REQ-KG-910"]


def test_extracts_design_doc_decisions_with_source_provenance() -> None:
    rows = extract_design_decisions(FIXTURE_ROOT)

    assert rows == [
        {
            "id": (
                "design-doc:docs/design.md:3:decision:"
                "keep-design-extraction-deterministic"
            ),
            "kind": "decision",
            "status": "accepted",
            "text": (
                "keep design extraction deterministic. The design-intelligence "
                "KG extracts authored requirements, decisions, tests, CI jobs, "
                "and graphify code nodes from a fixed tree without mutating any "
                "input file. The implementation source is `src/fixture.py`."
            ),
            "rationale": (
                "deterministic extraction lets the graph participate in golden "
                "tests and makes agent answers reviewable."
            ),
            "source_path": "docs/design.md",
            "source_line": 3,
        },
        {
            "id": (
                "design-doc:docs/design.md:14:non-goal:"
                "infer-canonical-links-from-weak-text-similarity"
            ),
            "kind": "non-goal",
            "status": "documented",
            "text": (
                "infer canonical links from weak text similarity. Weak lexical "
                "or semantic matches may be stored as evidence, but this fixture "
                "expects canonical links only from exact identifiers, paths, or "
                "reviewed evidence."
            ),
            "rationale": "",
            "source_path": "docs/design.md",
            "source_line": 14,
        },
        {
            "id": (
                "design-doc:docs/design.md:19:risk:"
                "stale-design-docs-drift-from-tests"
            ),
            "kind": "risk",
            "status": "documented",
            "text": (
                "stale design docs drift from tests. Mitigation: fixture tests "
                "compare canonical rows from the extractor."
            ),
            "rationale": "",
            "source_path": "docs/design.md",
            "source_line": 19,
        },
        {
            "id": (
                "design-doc:docs/design.md:23:alternative:"
                "infer-decisions-from-commit-history"
            ),
            "kind": "alternative",
            "status": "documented",
            "text": (
                "infer decisions from commit history. Rejected: authored docs "
                "carry better review provenance than commit messages."
            ),
            "rationale": "",
            "source_path": "docs/design.md",
            "source_line": 23,
        },
    ]


def test_extracts_legacy_cp1252_design_doc(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    design_path = docs / "design.md"
    design_path.write_bytes(
        b"# Legacy design\n\n"
        b"## Decision: caf\xe9 fallback\n\n"
        b"Status: accepted\n\n"
        b"Keep legacy docs readable.\n"
    )

    rows = extract_design_decisions(tmp_path)
    assert rows == [
        {
            "id": "design-doc:docs/design.md:3:decision:caf-fallback",
            "kind": "decision",
            "status": "accepted",
            "text": "caf\u00e9 fallback. Keep legacy docs readable.",
            "rationale": "",
            "source_path": "docs/design.md",
            "source_line": 3,
        }
    ]


def test_extracts_plural_design_sections_from_bullets(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    design_path = docs / "design.md"
    design_path.write_text(
        "\n".join(
            [
                "# Design",
                "",
                "## Non-goals",
                "- Do not infer weak links automatically.",
                "",
                "## Risks",
                "- Docs may drift from tests.",
                "",
                "## Alternatives",
                "- Keep manual spreadsheets.",
                "",
                "## Decisions",
                "- Use the KG as the design substrate.",
            ]
        ),
        encoding="utf-8",
    )

    rows = extract_design_decisions(tmp_path)
    assert rows == [
        {
            "id": (
                "design-doc:docs/design.md:4:non-goal:"
                "do-not-infer-weak-links-automatically"
            ),
            "kind": "non-goal",
            "status": "documented",
            "text": "Do not infer weak links automatically.",
            "rationale": "",
            "source_path": "docs/design.md",
            "source_line": 4,
        },
        {
            "id": "design-doc:docs/design.md:7:risk:docs-may-drift-from-tests",
            "kind": "risk",
            "status": "documented",
            "text": "Docs may drift from tests.",
            "rationale": "",
            "source_path": "docs/design.md",
            "source_line": 7,
        },
        {
            "id": (
                "design-doc:docs/design.md:10:alternative:"
                "keep-manual-spreadsheets"
            ),
            "kind": "alternative",
            "status": "documented",
            "text": "Keep manual spreadsheets.",
            "rationale": "",
            "source_path": "docs/design.md",
            "source_line": 10,
        },
        {
            "id": (
                "design-doc:docs/design.md:13:decision:"
                "use-the-kg-as-the-design-substrate"
            ),
            "kind": "decision",
            "status": "documented",
            "text": "Use the KG as the design substrate.",
            "rationale": "",
            "source_path": "docs/design.md",
            "source_line": 13,
        },
    ]


def test_extracts_operator_commands_from_design_docs() -> None:
    rows = extract_operator_commands(FIXTURE_ROOT)

    assert rows == [
        {
            "id": "operator-command:docs/design.md:30",
            "command": (
                "python -m graphify "
                "skills/book-knowledge/tests/fixtures/design-kg/src "
                "--output graphify-out"
            ),
            "shell": "powershell",
            "purpose": "regenerate fixture graph",
            "source_path": "docs/design.md",
            "source_line": 30,
        }
    ]


def test_project_design_docs_is_read_only_and_idempotent() -> None:
    design_path = FIXTURE_ROOT / "docs/design.md"
    before = design_path.read_text(encoding="utf-8")

    store = CozoStore.in_memory(schema_path=SCHEMA_PATH)
    project_design_docs(FIXTURE_ROOT, store)
    project_design_docs(FIXTURE_ROOT, store)

    decisions = sorted(
        store.query(
            "?[id, kind, status, source_path, source_line] := "
            "*design_decision{id, kind, status, source_path, source_line}"
        ),
        key=lambda row: row[4],
    )
    commands = store.query(
        "?[id, command, shell, purpose, source_path, source_line] := "
        "*operator_command{id, command, shell, purpose, source_path, source_line}"
    )

    assert decisions == [
        [
            "design-doc:docs/design.md:3:decision:"
            "keep-design-extraction-deterministic",
            "decision",
            "accepted",
            "docs/design.md",
            3,
        ],
        [
            "design-doc:docs/design.md:14:non-goal:"
            "infer-canonical-links-from-weak-text-similarity",
            "non-goal",
            "documented",
            "docs/design.md",
            14,
        ],
        [
            "design-doc:docs/design.md:19:risk:"
            "stale-design-docs-drift-from-tests",
            "risk",
            "documented",
            "docs/design.md",
            19,
        ],
        [
            "design-doc:docs/design.md:23:alternative:"
            "infer-decisions-from-commit-history",
            "alternative",
            "documented",
            "docs/design.md",
            23,
        ],
    ]
    assert commands == [
        [
            "operator-command:docs/design.md:30",
            (
                "python -m graphify "
                "skills/book-knowledge/tests/fixtures/design-kg/src "
                "--output graphify-out"
            ),
            "powershell",
            "regenerate fixture graph",
            "docs/design.md",
            30,
        ]
    ]
    assert design_path.read_text(encoding="utf-8") == before


def test_extracts_pytest_cases_with_source_provenance() -> None:
    rows = extract_test_cases(FIXTURE_ROOT)

    assert rows == [
        {
            "id": (
                "test-case:pytest:tests/test_fixture_pipeline.py::"
                "test_REQ_KG_901_fixture_requirement"
            ),
            "name": "test_REQ_KG_901_fixture_requirement",
            "framework": "pytest",
            "target": "REQ-KG-901",
            "source_path": "tests/test_fixture_pipeline.py",
            "source_line": 9,
        }
    ]


def test_extracts_ci_workflows_and_jobs_with_source_provenance() -> None:
    workflows = extract_ci_workflows(FIXTURE_ROOT)
    jobs = extract_ci_jobs(FIXTURE_ROOT)

    assert workflows == [
        {
            "id": "ci-workflow:.github/workflows/ci.yml",
            "name": "fixture-ci",
            "trigger": "pull_request,push",
            "source_path": ".github/workflows/ci.yml",
            "source_line": 1,
        }
    ]
    assert jobs == [
        {
            "id": "ci-job:.github/workflows/ci.yml:design-kg-required",
            "workflow_id": "ci-workflow:.github/workflows/ci.yml",
            "name": "design-kg-required",
            "required": True,
            "selector": "",
            "command": "python -m pytest tests/test_fixture_pipeline.py -q",
            "source_path": ".github/workflows/ci.yml",
            "source_line": 12,
        }
    ]


def test_extracts_ci_matrix_and_needs_selector(tmp_path: Path) -> None:
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    workflow_path = workflow_dir / "ci.yml"
    workflow_path.write_text(
        "\n".join(
            [
                "name: ci",
                "on: [pull_request]",
                "jobs:",
                "  compute:",
                "    runs-on: ubuntu-24.04",
                "    steps:",
                "      - run: python -m ci.compute_matrix --profile pr",
                "  python-skill-matrix:",
                "    name: python-skill (${{ matrix.skill }})",
                "    needs: [compute]",
                "    runs-on: ${{ matrix.os }}",
                "    strategy:",
                "      matrix:",
                "        skill: [book-knowledge]",
                "        os: [ubuntu-24.04]",
                "    steps:",
                "      - name: pytest",
                "        run: |",
                "          cd skills/${{ matrix.skill }}",
                "          python -m pytest tests -q",
            ]
        ),
        encoding="utf-8",
    )

    jobs = extract_ci_jobs(tmp_path)
    assert jobs == [
        {
            "id": "ci-job:.github/workflows/ci.yml:compute",
            "workflow_id": "ci-workflow:.github/workflows/ci.yml",
            "name": "compute",
            "required": False,
            "selector": "",
            "command": "python -m ci.compute_matrix --profile pr",
            "source_path": ".github/workflows/ci.yml",
            "source_line": 4,
        },
        {
            "id": "ci-job:.github/workflows/ci.yml:python-skill-matrix",
            "workflow_id": "ci-workflow:.github/workflows/ci.yml",
            "name": "python-skill (${{ matrix.skill }})",
            "required": False,
            "selector": (
                'needs=["compute"];matrix={"os":["ubuntu-24.04"],'
                '"skill":["book-knowledge"]}'
            ),
            "command": (
                "cd skills/${{ matrix.skill }} && "
                "python -m pytest tests -q"
            ),
            "source_path": ".github/workflows/ci.yml",
            "source_line": 8,
        },
    ]


def test_project_tests_and_ci_is_read_only_and_idempotent() -> None:
    test_path = FIXTURE_ROOT / "tests/test_fixture_pipeline.py"
    workflow_path = FIXTURE_ROOT / ".github/workflows/ci.yml"
    before_test = test_path.read_text(encoding="utf-8")
    before_workflow = workflow_path.read_text(encoding="utf-8")

    store = CozoStore.in_memory(schema_path=SCHEMA_PATH)
    project_tests_and_ci(FIXTURE_ROOT, store)
    project_tests_and_ci(FIXTURE_ROOT, store)

    tests = store.query(
        "?[id, name, framework, target, source_path, source_line] := "
        "*test_case{id, name, framework, target, source_path, source_line}"
    )
    workflows = store.query(
        "?[id, name, trigger, source_path, source_line] := "
        "*ci_workflow{id, name, trigger, source_path, source_line}"
    )
    jobs = store.query(
        "?[id, workflow_id, name, required, selector, command, source_path, source_line] := "
        "*ci_job{id, workflow_id, name, required, selector, command, source_path, source_line}"
    )

    assert tests == [
        [
            "test-case:pytest:tests/test_fixture_pipeline.py::"
            "test_REQ_KG_901_fixture_requirement",
            "test_REQ_KG_901_fixture_requirement",
            "pytest",
            "REQ-KG-901",
            "tests/test_fixture_pipeline.py",
            9,
        ]
    ]
    assert workflows == [
        [
            "ci-workflow:.github/workflows/ci.yml",
            "fixture-ci",
            "pull_request,push",
            ".github/workflows/ci.yml",
            1,
        ]
    ]
    assert jobs == [
        [
            "ci-job:.github/workflows/ci.yml:design-kg-required",
            "ci-workflow:.github/workflows/ci.yml",
            "design-kg-required",
            True,
            "",
            "python -m pytest tests/test_fixture_pipeline.py -q",
            ".github/workflows/ci.yml",
            12,
        ]
    ]
    assert test_path.read_text(encoding="utf-8") == before_test
    assert workflow_path.read_text(encoding="utf-8") == before_workflow


def test_design_kg_snapshot_has_canonical_fixture_rows() -> None:
    snapshot = extract_design_kg_snapshot(FIXTURE_ROOT)

    assert extract_design_kg_snapshot(FIXTURE_ROOT) == snapshot
    assert snapshot == {
        "design-requirement": [
            {
                "id": "openspec:sample-capability:REQ-KG-901",
                "requirement_id": "REQ-KG-901",
                "capability": "sample-capability",
                "status": "fixture",
                "text": (
                    "The fixture SHALL expose a deterministic design graph input "
                        "that links a requirement, design decision, test case, CI job, "
                        "and graphify code node. The fixture implementation source is "
                        "`src/fixture.py`."
                ),
                "source_path": "openspec/specs/sample-capability/spec.md",
                "source_line": 5,
            }
        ],
        "design-scenario": [
            {
                "id": (
                    "openspec-scenario:sample-capability:REQ-KG-901:14:"
                    "fixture-requirement-is-covered-by-a-test"
                ),
                "requirement_id": "REQ-KG-901",
                "capability": "sample-capability",
                "text": (
                    "fixture requirement is covered by a test WHEN the "
                    "design-KG extractor reads this fixture THEN it emits a "
                    "`design-requirement` row for `REQ-KG-901` AND "
                    "`tests/test_fixture_pipeline.py::"
                    "test_REQ_KG_901_fixture_requirement` covers it"
                ),
                "source_path": "openspec/specs/sample-capability/spec.md",
                "source_line": 14,
            }
        ],
        "design-decision": [
            {
                "id": (
                    "design-doc:docs/design.md:3:decision:"
                    "keep-design-extraction-deterministic"
                ),
                "kind": "decision",
                "status": "accepted",
                "text": (
                    "keep design extraction deterministic. The design-intelligence "
                    "KG extracts authored requirements, decisions, tests, CI jobs, "
                    "and graphify code nodes from a fixed tree without mutating any "
                    "input file. The implementation source is `src/fixture.py`."
                ),
                "rationale": (
                    "deterministic extraction lets the graph participate in golden "
                    "tests and makes agent answers reviewable."
                ),
                "source_path": "docs/design.md",
                "source_line": 3,
            },
            {
                "id": (
                    "design-doc:docs/design.md:14:non-goal:"
                    "infer-canonical-links-from-weak-text-similarity"
                ),
                "kind": "non-goal",
                "status": "documented",
                "text": (
                    "infer canonical links from weak text similarity. Weak lexical "
                    "or semantic matches may be stored as evidence, but this fixture "
                    "expects canonical links only from exact identifiers, paths, or "
                    "reviewed evidence."
                ),
                "rationale": "",
                "source_path": "docs/design.md",
                "source_line": 14,
            },
            {
                "id": (
                    "design-doc:docs/design.md:19:risk:"
                    "stale-design-docs-drift-from-tests"
                ),
                "kind": "risk",
                "status": "documented",
                "text": (
                    "stale design docs drift from tests. Mitigation: fixture tests "
                    "compare canonical rows from the extractor."
                ),
                "rationale": "",
                "source_path": "docs/design.md",
                "source_line": 19,
            },
            {
                "id": (
                    "design-doc:docs/design.md:23:alternative:"
                    "infer-decisions-from-commit-history"
                ),
                "kind": "alternative",
                "status": "documented",
                "text": (
                    "infer decisions from commit history. Rejected: authored docs "
                    "carry better review provenance than commit messages."
                ),
                "rationale": "",
                "source_path": "docs/design.md",
                "source_line": 23,
            },
        ],
        "operator-command": [
            {
                "id": "operator-command:docs/design.md:30",
                "command": (
                    "python -m graphify "
                    "skills/book-knowledge/tests/fixtures/design-kg/src "
                    "--output graphify-out"
                ),
                "shell": "powershell",
                "purpose": "regenerate fixture graph",
                "source_path": "docs/design.md",
                "source_line": 30,
            }
        ],
        "test-case": [
            {
                "id": (
                    "test-case:pytest:tests/test_fixture_pipeline.py::"
                    "test_REQ_KG_901_fixture_requirement"
                ),
                "name": "test_REQ_KG_901_fixture_requirement",
                "framework": "pytest",
                "target": "REQ-KG-901",
                "source_path": "tests/test_fixture_pipeline.py",
                "source_line": 9,
            }
        ],
        "ci-workflow": [
            {
                "id": "ci-workflow:.github/workflows/ci.yml",
                "name": "fixture-ci",
                "trigger": "pull_request,push",
                "source_path": ".github/workflows/ci.yml",
                "source_line": 1,
            }
        ],
        "ci-job": [
            {
                "id": "ci-job:.github/workflows/ci.yml:design-kg-required",
                "workflow_id": "ci-workflow:.github/workflows/ci.yml",
                "name": "design-kg-required",
                "required": True,
                "selector": "",
                "command": "python -m pytest tests/test_fixture_pipeline.py -q",
                "source_path": ".github/workflows/ci.yml",
                "source_line": 12,
            }
        ],
    }


def test_extracts_promoted_traceability_links_from_exact_evidence() -> None:
    rows = extract_traceability_links(FIXTURE_ROOT)

    assert rows == [
        {
            "id": (
                "trace:decision-constrains-code:design-doc:docs/design.md:3:"
                "decision:keep-design-extraction-deterministic->fixture_module:"
                "src-fixture-py"
            ),
            "from_id": (
                "design-doc:docs/design.md:3:decision:"
                "keep-design-extraction-deterministic"
            ),
            "to_id": "fixture_module",
            "kind": "decision-constrains-code",
            "confidence": 1.0,
            "witness": "src/fixture.py",
            "provenance": "deterministic:exact-path",
            "promoted": True,
            "source_path": "docs/design.md",
            "source_line": 3,
        },
        {
            "id": (
                "trace:requirement-covered-by:openspec:sample-capability:"
                "REQ-KG-901->test-case:pytest:tests/test_fixture_pipeline.py::"
                "test_REQ_KG_901_fixture_requirement:req-kg-901"
            ),
            "from_id": "openspec:sample-capability:REQ-KG-901",
            "to_id": (
                "test-case:pytest:tests/test_fixture_pipeline.py::"
                "test_REQ_KG_901_fixture_requirement"
            ),
            "kind": "requirement-covered-by",
            "confidence": 1.0,
            "witness": "REQ-KG-901",
            "provenance": "deterministic:exact-req-id",
            "promoted": True,
            "source_path": "tests/test_fixture_pipeline.py",
            "source_line": 9,
        },
        {
            "id": (
                "trace:requirement-gated-by:openspec:sample-capability:"
                "REQ-KG-901->ci-job:.github/workflows/ci.yml:"
                "design-kg-required:tests-test-fixture-pipeline-py"
            ),
            "from_id": "openspec:sample-capability:REQ-KG-901",
            "to_id": "ci-job:.github/workflows/ci.yml:design-kg-required",
            "kind": "requirement-gated-by",
            "confidence": 1.0,
            "witness": "tests/test_fixture_pipeline.py",
            "provenance": "deterministic:ci-command-invokes-test",
            "promoted": True,
            "source_path": ".github/workflows/ci.yml",
            "source_line": 12,
        },
        {
            "id": (
                "trace:requirement-implemented-by:openspec:sample-capability:"
                "REQ-KG-901->fixture_module:src-fixture-py"
            ),
            "from_id": "openspec:sample-capability:REQ-KG-901",
            "to_id": "fixture_module",
            "kind": "requirement-implemented-by",
            "confidence": 1.0,
            "witness": "src/fixture.py",
            "provenance": "deterministic:exact-path",
            "promoted": True,
            "source_path": "openspec/specs/sample-capability/spec.md",
            "source_line": 5,
        },
        {
            "id": (
                "trace:test-exercises-code:test-case:pytest:"
                "tests/test_fixture_pipeline.py::"
                "test_REQ_KG_901_fixture_requirement->fixture_module:src-fixture"
            ),
            "from_id": (
                "test-case:pytest:tests/test_fixture_pipeline.py::"
                "test_REQ_KG_901_fixture_requirement"
            ),
            "to_id": "fixture_module",
            "kind": "test-exercises-code",
            "confidence": 1.0,
            "witness": "src.fixture",
            "provenance": "deterministic:python-import",
            "promoted": True,
            "source_path": "tests/test_fixture_pipeline.py",
            "source_line": 6,
        },
        {
            "id": (
                "trace:workflow-runs-test:ci-job:.github/workflows/ci.yml:"
                "design-kg-required->test-case:pytest:"
                "tests/test_fixture_pipeline.py::"
                "test_REQ_KG_901_fixture_requirement:tests-test-fixture-pipeline-py"
            ),
            "from_id": "ci-job:.github/workflows/ci.yml:design-kg-required",
            "to_id": (
                "test-case:pytest:tests/test_fixture_pipeline.py::"
                "test_REQ_KG_901_fixture_requirement"
            ),
            "kind": "workflow-runs-test",
            "confidence": 1.0,
            "witness": "tests/test_fixture_pipeline.py",
            "provenance": "deterministic:ci-command-invokes-test",
            "promoted": True,
            "source_path": ".github/workflows/ci.yml",
            "source_line": 12,
        },
    ]


def test_reviewed_traceability_manifest_promotes_explicit_links(
    tmp_path: Path,
) -> None:
    spec_dir = tmp_path / "openspec" / "changes" / "reviewed" / "specs" / "manifest"
    spec_dir.mkdir(parents=True)
    (spec_dir / "spec.md").write_text(
        "\n".join(
            [
                "# Capability: manifest",
                "",
                "### Requirement: REQ-KG-905 - Reviewed manifest links (Ubiquitous)",
                "",
                "The fixture SHALL promote reviewed traceability evidence.",
            ]
        ),
        encoding="utf-8",
    )
    graph_dir = tmp_path / "graphify"
    graph_dir.mkdir()
    source_dir = tmp_path / "src"
    source_dir.mkdir()
    (source_dir / "impl.py").write_text("VALUE = 1\n", encoding="utf-8")
    (graph_dir / "graph.json").write_text(
        json.dumps(
            {
                "nodes": [
                    {
                        "id": "impl_module",
                        "label": "impl.py",
                        "source_file": "src/impl.py",
                    }
                ],
                "links": [],
            }
        ),
        encoding="utf-8",
    )
    test_dir = tmp_path / "tests"
    test_dir.mkdir()
    (test_dir / "test_manifest.py").write_text(
        "\n".join(
            [
                "def test_manifest_contract():",
                "    assert True",
            ]
        ),
        encoding="utf-8",
    )
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "ci.yml").write_text(
        "\n".join(
            [
                "name: ci",
                "on: [pull_request]",
                "jobs:",
                "  tools-test:",
                "    runs-on: ubuntu-24.04",
                "    steps:",
                "      - run: python -m pytest tests/test_manifest.py -q",
            ]
        ),
        encoding="utf-8",
    )
    manifest_path = tmp_path / "openspec" / "changes" / "reviewed" / "traceability.json"
    manifest_path.write_text(
        json.dumps(
            {
                "version": 1,
                "links": [
                    {
                        "requirement_id": "REQ-KG-905",
                        "capability": "manifest",
                        "requirement_source": (
                            "openspec/changes/reviewed/specs/manifest/spec.md"
                        ),
                        "kind": "requirement-implemented-by",
                        "target_type": "code-path",
                        "target": "src/impl.py",
                    },
                    {
                        "requirement_id": "REQ-KG-905",
                        "capability": "manifest",
                        "requirement_source": (
                            "openspec/changes/reviewed/specs/manifest/spec.md"
                        ),
                        "kind": "requirement-covered-by",
                        "target_type": "test-case",
                        "target": (
                            "tests/test_manifest.py::test_manifest_contract"
                        ),
                    },
                    {
                        "requirement_id": "REQ-KG-905",
                        "capability": "manifest",
                        "requirement_source": (
                            "openspec/changes/reviewed/specs/manifest/spec.md"
                        ),
                        "kind": "requirement-gated-by",
                        "target_type": "ci-job",
                        "target": ".github/workflows/ci.yml:tools-test",
                    },
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    reviewed = [
        row
        for row in extract_traceability_links(tmp_path)
        if row["provenance"] == "reviewed:traceability-manifest"
    ]

    assert reviewed == [
        {
            "id": (
                "trace:requirement-covered-by:openspec:manifest:REQ-KG-905->"
                "test-case:pytest:tests/test_manifest.py::"
                "test_manifest_contract:tests-test-manifest-py-test-manifest-contract"
            ),
            "from_id": "openspec:manifest:REQ-KG-905",
            "to_id": (
                "test-case:pytest:tests/test_manifest.py::"
                "test_manifest_contract"
            ),
            "kind": "requirement-covered-by",
            "confidence": 1.0,
            "witness": "tests/test_manifest.py::test_manifest_contract",
            "provenance": "reviewed:traceability-manifest",
            "promoted": True,
            "source_path": "openspec/changes/reviewed/traceability.json",
            "source_line": 18,
        },
        {
            "id": (
                "trace:requirement-gated-by:openspec:manifest:REQ-KG-905->"
                "ci-job:.github/workflows/ci.yml:tools-test:"
                "github-workflows-ci-yml-tools-test"
            ),
            "from_id": "openspec:manifest:REQ-KG-905",
            "to_id": "ci-job:.github/workflows/ci.yml:tools-test",
            "kind": "requirement-gated-by",
            "confidence": 1.0,
            "witness": ".github/workflows/ci.yml:tools-test",
            "provenance": "reviewed:traceability-manifest",
            "promoted": True,
            "source_path": "openspec/changes/reviewed/traceability.json",
            "source_line": 26,
        },
        {
            "id": (
                "trace:requirement-implemented-by:openspec:manifest:"
                "REQ-KG-905->impl_module:src-impl-py"
            ),
            "from_id": "openspec:manifest:REQ-KG-905",
            "to_id": "impl_module",
            "kind": "requirement-implemented-by",
            "confidence": 1.0,
            "witness": "src/impl.py",
            "provenance": "reviewed:traceability-manifest",
            "promoted": True,
            "source_path": "openspec/changes/reviewed/traceability.json",
            "source_line": 10,
        },
    ]


def test_ambiguous_symbol_links_are_evidence_only(tmp_path: Path) -> None:
    spec_dir = tmp_path / "openspec" / "specs" / "ambiguous"
    spec_dir.mkdir(parents=True)
    (spec_dir / "spec.md").write_text(
        "\n".join(
            [
                "# Capability: ambiguous",
                "",
                "### Requirement: REQ-KG-903 - Ambiguous symbol (Ubiquitous)",
                "",
                "The fixture SHALL mention `shared_symbol` without disambiguation.",
            ]
        ),
        encoding="utf-8",
    )
    graph_dir = tmp_path / "graphify"
    graph_dir.mkdir()
    (graph_dir / "graph.json").write_text(
        (
            '{"nodes":['
            '{"id":"a","label":"shared_symbol()","source_file":"src/a.py"},'
            '{"id":"b","label":"shared_symbol()","source_file":"src/b.py"}'
            '],"links":[]}'
        ),
        encoding="utf-8",
    )

    rows = extract_traceability_links(tmp_path)
    assert rows == [
        {
            "id": (
                "trace:requirement-implemented-by:openspec:ambiguous:"
                "REQ-KG-903->a:shared-symbol"
            ),
            "from_id": "openspec:ambiguous:REQ-KG-903",
            "to_id": "a",
            "kind": "requirement-implemented-by",
            "confidence": 0.5,
            "witness": "shared_symbol",
            "provenance": "deterministic:ambiguous-symbol",
            "promoted": False,
            "source_path": "openspec/specs/ambiguous/spec.md",
            "source_line": 3,
        },
        {
            "id": (
                "trace:requirement-implemented-by:openspec:ambiguous:"
                "REQ-KG-903->b:shared-symbol"
            ),
            "from_id": "openspec:ambiguous:REQ-KG-903",
            "to_id": "b",
            "kind": "requirement-implemented-by",
            "confidence": 0.5,
            "witness": "shared_symbol",
            "provenance": "deterministic:ambiguous-symbol",
            "promoted": False,
            "source_path": "openspec/specs/ambiguous/spec.md",
            "source_line": 3,
        },
    ]


def test_weak_lexical_symbol_links_are_evidence_only(tmp_path: Path) -> None:
    spec_dir = tmp_path / "openspec" / "specs" / "lexical"
    spec_dir.mkdir(parents=True)
    (spec_dir / "spec.md").write_text(
        "\n".join(
            [
                "# Capability: lexical",
                "",
                "### Requirement: REQ-KG-904 - Lexical symbol (Ubiquitous)",
                "",
                "The fixture SHALL mention shared_utility only as prose.",
            ]
        ),
        encoding="utf-8",
    )
    graph_dir = tmp_path / "graphify"
    graph_dir.mkdir()
    (graph_dir / "graph.json").write_text(
        (
            '{"nodes":['
            '{"id":"shared","label":"shared_utility()","source_file":"src/shared.py"}'
            '],"links":[]}'
        ),
        encoding="utf-8",
    )

    rows = extract_traceability_links(tmp_path)
    assert rows == [
        {
            "id": (
                "trace:requirement-implemented-by:openspec:lexical:"
                "REQ-KG-904->shared:shared-utility"
            ),
            "from_id": "openspec:lexical:REQ-KG-904",
            "to_id": "shared",
            "kind": "requirement-implemented-by",
            "confidence": 0.25,
            "witness": "shared_utility",
            "provenance": "deterministic:lexical-symbol",
            "promoted": False,
            "source_path": "openspec/specs/lexical/spec.md",
            "source_line": 3,
        }
    ]


def test_project_traceability_links_is_idempotent() -> None:
    store = CozoStore.in_memory(schema_path=SCHEMA_PATH)
    project_traceability_links(FIXTURE_ROOT, store)
    project_traceability_links(FIXTURE_ROOT, store)

    rows = store.query(
        "?[id, from_id, to_id, kind, promoted, source_path, source_line] := "
        "*traceability_link{id, from_id, to_id, kind, promoted, source_path, source_line}"
    )
    assert len(rows) == 6
    assert all(row[4] is True for row in rows)
