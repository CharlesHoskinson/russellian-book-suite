"""REQ-INDUCE-050..057: 3-source candidate generation orchestrator.

Phase W of the Tier 6 theory-induction layer. These tests exercise the
Python-side implementation of the orchestrator
(`scripts._induction_orchestrator`) and the three candidate sources
(`scripts._induction_sources`). The CLJS entry point
`scripts/induce_theory.cljs` mirrors the Python logic; the nbb subprocess
test (`test_orchestrator_entrypoint_runs_on_fixture_project`) skips when
nbb is not on PATH.

Phase V's `_induction_proposer.py` and `_induction_grammar.cljs` are
imported conditionally — when absent, the LLM source is disabled and the
Horn-body + Popper sources still run.
"""
from __future__ import annotations

import platform
import sys
from pathlib import Path

import pytest

# Make `scripts.*` importable regardless of the test runner cwd.
SCRIPTS_PARENT = Path(__file__).resolve().parent.parent
if str(SCRIPTS_PARENT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_PARENT))

from scripts import _induction_orchestrator as orch  # noqa: E402
from scripts import _induction_sources as sources  # noqa: E402
from scripts._edn_reader import Keyword  # noqa: E402
from scripts._io import read_edn_file  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _seed_project(root: Path, *, atoms: list[dict], predicates: dict) -> Path:
    """Seed a minimal project root with a schema + atomspace.

    The atomspace is the post-lift form: one atom per (claim, predicate)
    binding. The Horn-body source counts predicate-pair co-occurrence per
    document over this list.
    """
    root.mkdir(parents=True, exist_ok=True)
    rules = root / "rules"
    rules.mkdir(exist_ok=True)
    schema = {
        Keyword("version"): 1,
        Keyword("sorts"): [Keyword("disease"), Keyword("population")],
        Keyword("predicates"): {
            Keyword(name): {
                Keyword("arg-sorts"): sig["arg-sorts"],
                Keyword("return"): sig["return"],
            }
            for name, sig in predicates.items()
        },
    }
    from scripts._edn_writer import write_edn

    (rules / "booklogic-schema.edn").write_text(
        write_edn(schema, pretty=True) + "\n", encoding="utf-8", newline="\n"
    )

    # Atomspace shape: a flat list of {:claim-id :document :predicate :subject :value}.
    atomspace = {
        Keyword("version"): 1,
        Keyword("atoms"): [
            {
                Keyword("claim-id"): a["claim_id"],
                Keyword("document"): a["document"],
                Keyword("predicate"): Keyword(a["predicate"]),
                Keyword("subject"): Keyword(a["subject"]),
                Keyword("value"): a["value"],
            }
            for a in atoms
        ],
    }
    (rules / "atomspace.edn").write_text(
        write_edn(atomspace, pretty=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return root


def _fixture_atoms() -> list[dict]:
    """Synthetic 12-atom corpus: R0 + threshold co-occur in 4 docs; coverage
    appears alone in 2 docs. The Horn-body source should rank
    (R0, threshold) above (R0, coverage)."""
    atoms = []
    # 4 docs where R0 and threshold co-occur (high support for the pair).
    for i, doc in enumerate(["doc-1", "doc-2", "doc-3", "doc-4"]):
        atoms.append(
            {
                "claim_id": f"c-r0-{i}",
                "document": doc,
                "predicate": "basic-reproduction-number",
                "subject": "measles",
                "value": 15.0 + i,
            }
        )
        atoms.append(
            {
                "claim_id": f"c-thr-{i}",
                "document": doc,
                "predicate": "herd-immunity-threshold",
                "subject": "measles",
                "value": 0.94 - i * 0.01,
            }
        )
    # 2 docs with only coverage (low support for any pair involving coverage).
    for i, doc in enumerate(["doc-5", "doc-6"]):
        atoms.append(
            {
                "claim_id": f"c-cov-{i}",
                "document": doc,
                "predicate": "vaccination-coverage",
                "subject": "p1",
                "value": 0.95 - i * 0.02,
            }
        )
    return atoms


def _fixture_predicates() -> dict:
    return {
        "basic-reproduction-number": {
            "arg-sorts": [Keyword("disease")],
            "return": Keyword("real"),
        },
        "vaccination-coverage": {
            "arg-sorts": [Keyword("population")],
            "return": Keyword("real"),
        },
        "herd-immunity-threshold": {
            "arg-sorts": [Keyword("disease")],
            "return": Keyword("real"),
        },
    }


@pytest.fixture()
def seeded_project(tmp_path: Path) -> Path:
    return _seed_project(
        tmp_path / "proj",
        atoms=_fixture_atoms(),
        predicates=_fixture_predicates(),
    )


# ---------------------------------------------------------------------------
# REQ-INDUCE-050: orchestrator entry point
# ---------------------------------------------------------------------------


def test_orchestrator_python_entrypoint_runs_on_fixture_project(seeded_project: Path) -> None:
    """REQ-INDUCE-050, 051: the Python orchestrator main runs over a
    fixture project and writes candidates.edn from the three sources."""
    rc = orch.main([str(seeded_project)])
    assert rc == 0
    out = seeded_project / "work" / "induction" / "candidates.edn"
    assert out.exists(), "candidates.edn must be written"
    payload = read_edn_file(out)
    assert payload[Keyword("version")] == 1
    assert isinstance(payload[Keyword("candidates")], list)
    assert len(payload[Keyword("candidates")]) > 0


def test_orchestrator_entrypoint_runs_on_fixture_project(seeded_project: Path) -> None:
    """REQ-INDUCE-050: nbb induce_theory.cljs <project> writes
    candidates.edn. Skipped where nbb is absent on PATH (typical CI on
    Windows runners that don't install nbb)."""
    import shutil
    import subprocess

    if not shutil.which("nbb"):
        pytest.skip("nbb not available on PATH")
    cljs = SCRIPTS_PARENT / "scripts" / "induce_theory.cljs"
    result = subprocess.run(
        ["nbb", str(cljs), str(seeded_project)],
        capture_output=True,
        text=True,
        check=False,
        shell=(platform.system() == "Windows"),
    )
    assert result.returncode == 0, result.stderr
    assert (seeded_project / "work" / "induction" / "candidates.edn").exists()


# ---------------------------------------------------------------------------
# REQ-INDUCE-051: three sources, per-source cap
# ---------------------------------------------------------------------------


def test_horn_body_source_in_isolation(seeded_project: Path) -> None:
    """REQ-INDUCE-051(a), 057: Horn-body source emits candidates from
    frequent predicate-pair co-occurrence."""
    schema = orch.load_schema(seeded_project)
    atoms = orch.load_atoms(seeded_project)
    cands = sources.horn_mine(atoms, schema)
    assert len(cands) > 0
    # The (R0, threshold) pair co-occurs in 4 docs, the strongest signal.
    forms = [c["canonical_form"] for c in cands]
    assert any(
        "basic-reproduction-number" in f and "herd-immunity-threshold" in f
        for f in forms
    )
    # Each candidate carries its origin tag.
    for c in cands:
        assert sources.HORN_BODY in c["origin"]


def test_popper_source_in_isolation(seeded_project: Path) -> None:
    """REQ-INDUCE-051(b), 057: Popper-style typed search emits typed
    candidate templates respecting predicate signatures from
    booklogic-schema.edn."""
    schema = orch.load_schema(seeded_project)
    cands = sources.popper_search(schema)
    assert len(cands) > 0
    # All Popper outputs must respect the literal-count cap (≤4 literals).
    for c in cands:
        assert c["literal_count"] <= 4
        assert sources.POPPER in c["origin"]
    # Predicates of matching :return :real are paired into approx= templates.
    forms = [c["canonical_form"] for c in cands]
    assert any("approx=" in f for f in forms)


def test_llm_source_against_stub(seeded_project: Path) -> None:
    """REQ-INDUCE-051(c), 057: the LLM source pulls candidates from the
    Phase V proposer's stub backend. When Phase V is absent, the source
    returns [] without raising."""
    schema = orch.load_schema(seeded_project)
    atoms = orch.load_atoms(seeded_project)
    cluster = [a for a in atoms if a["predicate"] == "basic-reproduction-number"]
    cands = sources.llm_propose(
        schema=schema,
        cluster=cluster,
        provider=sources.StubProposer(),
    )
    assert len(cands) >= 1
    for c in cands:
        assert sources.LLM in c["origin"]


def test_each_source_respects_per_source_cap(seeded_project: Path, monkeypatch) -> None:
    """REQ-INDUCE-051: per-source cap is the
    NEUROSYM_INDUCTION_CANDIDATES_PER_SOURCE env var (default 20)."""
    monkeypatch.setenv("NEUROSYM_INDUCTION_CANDIDATES_PER_SOURCE", "1")
    schema = orch.load_schema(seeded_project)
    atoms = orch.load_atoms(seeded_project)
    cap = sources.per_source_cap()
    assert cap == 1
    assert len(sources.horn_mine(atoms, schema)) <= cap
    assert len(sources.popper_search(schema)) <= cap


# ---------------------------------------------------------------------------
# REQ-INDUCE-054: small corpora skip Horn-body
# ---------------------------------------------------------------------------


def test_horn_body_skipped_with_warning_on_small_corpus(tmp_path: Path) -> None:
    """REQ-INDUCE-054: <10 atoms → Horn-body source emits a structured
    warning and returns []. Popper + LLM still run downstream."""
    small_atoms = _fixture_atoms()[:5]  # 5 atoms < 10
    proj = _seed_project(
        tmp_path / "small",
        atoms=small_atoms,
        predicates=_fixture_predicates(),
    )
    schema = orch.load_schema(proj)
    atoms = orch.load_atoms(proj)
    cands = sources.horn_mine(atoms, schema)
    assert cands == []
    warnings = sources.last_warnings()
    assert any(w.get("warning") == "corpus-too-small" for w in warnings)


# ---------------------------------------------------------------------------
# REQ-INDUCE-052: dedup by canonical form, origin set union
# ---------------------------------------------------------------------------


def test_alpha_equivalent_candidates_collapse_with_merged_origin() -> None:
    """REQ-INDUCE-052: two candidates with alpha-equivalent canonical forms
    collapse to one entry whose :origin field carries the union of source
    tags."""
    c1 = {
        "canonical_form": "(defconstraint :induced/c (implies (:p ?d) (:q ?d)))",
        "cited_atoms": ["a-1", "a-2"],
        "origin": [sources.HORN_BODY],
        "support": 4,
    }
    c2 = {
        # Alpha-equivalent: same shape with different var name. After
        # canonicalisation both reduce to the same key.
        "canonical_form": "(defconstraint :induced/c (implies (:p ?x) (:q ?x)))",
        "cited_atoms": ["a-3", "a-4"],
        "origin": [sources.LLM],
        "support": 3,
    }
    merged = sources.dedup([c1, c2])
    assert len(merged) == 1
    survivor = merged[0]
    assert set(survivor["origin"]) == {sources.HORN_BODY, sources.LLM}
    # Cited-atom set is the union as well.
    assert set(survivor["cited_atoms"]) == {"a-1", "a-2", "a-3", "a-4"}


def test_dedup_merges_origins_when_three_sources_agree() -> None:
    """REQ-INDUCE-057: three sources producing the same canonical form
    collapse to one candidate whose :origin is the 3-element union."""
    base = "(defconstraint :c (implies (:p ?d) (:q ?d)))"
    cands = [
        {"canonical_form": base, "cited_atoms": ["a-1"], "origin": [sources.HORN_BODY]},
        {"canonical_form": base, "cited_atoms": ["a-2"], "origin": [sources.POPPER]},
        {"canonical_form": base, "cited_atoms": ["a-3"], "origin": [sources.LLM]},
    ]
    merged = sources.dedup(cands)
    assert len(merged) == 1
    assert set(merged[0]["origin"]) == {sources.HORN_BODY, sources.POPPER, sources.LLM}


# ---------------------------------------------------------------------------
# REQ-INDUCE-055: persisted queue with rejection reasons
# ---------------------------------------------------------------------------


def test_queue_persists_rejected_candidates_with_reason_tags(seeded_project: Path) -> None:
    """REQ-INDUCE-055: rejected candidates remain in the queue with
    :status :rejected and :rejection-reason set."""
    rc = orch.main([str(seeded_project)])
    assert rc == 0
    out = seeded_project / "work" / "induction" / "candidates.edn"
    payload = read_edn_file(out)
    cands = payload[Keyword("candidates")]
    for c in cands:
        assert Keyword("status") in c
        assert Keyword("rejection-reason") in c
        status = c[Keyword("status")]
        assert status in (Keyword("pending"), Keyword("rejected"))


def test_duplicate_candidate_is_rejected_with_duplicate_reason() -> None:
    """REQ-INDUCE-055: when dedup merges two alpha-equivalent
    candidates, the survivor enters the queue with :status :pending; an
    explicit-duplicate test path emits one as :rejected with
    :rejection-reason :duplicate."""
    c1 = {
        "canonical_form": "(defconstraint :c (implies (:p ?d) (:q ?d)))",
        "cited_atoms": ["a-1"],
        "origin": [sources.HORN_BODY],
    }
    c2 = {
        "canonical_form": "(defconstraint :c (implies (:p ?x) (:q ?x)))",
        "cited_atoms": ["a-1"],
        "origin": [sources.LLM],
    }
    merged, rejected = sources.dedup_with_rejection_log([c1, c2])
    assert len(merged) == 1
    assert len(rejected) == 1
    assert rejected[0]["rejection_reason"] == "duplicate"
