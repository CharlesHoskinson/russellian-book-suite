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

import pytest

pytestmark = pytest.mark.windows_canary

import json
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


# ---------------------------------------------------------------------------
# REQ-INDUCE-053: semantic-coherence ranking
# ---------------------------------------------------------------------------


class _FakeSemanticIndex:
    """Deterministic cosine over a small lookup table for ranking tests."""

    def __init__(self, table: dict[tuple[str, str], float]) -> None:
        self._table = table

    def cosine(self, a: str, b: str) -> float:
        if a == b:
            return 1.0
        key = tuple(sorted([a, b]))
        return self._table.get(key, 0.0)


def test_semantic_ranking_orders_by_coherence_descending() -> None:
    """REQ-INDUCE-053: ranking puts higher-coherence candidates first."""
    idx = _FakeSemanticIndex(
        {
            ("a-1", "a-2"): 0.9,   # high coherence
            ("a-3", "a-4"): 0.5,   # mid
            ("a-5", "a-6"): 0.1,   # low
        }
    )
    cands = [
        {"id": "c-low",  "cited_atoms": ["a-5", "a-6"], "origin": [sources.HORN_BODY]},
        {"id": "c-high", "cited_atoms": ["a-1", "a-2"], "origin": [sources.HORN_BODY]},
        {"id": "c-mid",  "cited_atoms": ["a-3", "a-4"], "origin": [sources.HORN_BODY]},
    ]
    ranked = sources.rank_by_semantic_coherence(cands, idx)
    assert [c["id"] for c in ranked] == ["c-high", "c-mid", "c-low"]
    assert ranked[0]["coherence"] == pytest.approx(0.9)
    assert ranked[-1]["coherence"] == pytest.approx(0.1)


def test_ranking_falls_back_to_stable_order_without_index() -> None:
    """REQ-INDUCE-053: WHERE SemanticIndex is absent, ranking is a no-op
    and preserves insertion order."""
    cands = [
        {"id": "c-a", "cited_atoms": ["x", "y"], "origin": [sources.HORN_BODY]},
        {"id": "c-b", "cited_atoms": ["z", "w"], "origin": [sources.HORN_BODY]},
    ]
    ranked = sources.rank_by_semantic_coherence(cands, sem_index=None)
    assert [c["id"] for c in ranked] == ["c-a", "c-b"]
    # The coherence field is still present (None) so downstream consumers
    # have a consistent shape.
    assert all("coherence" in c for c in ranked)


def test_singleton_cited_atom_has_unit_coherence() -> None:
    """REQ-INDUCE-053: a candidate with <2 cited atoms has coherence 1.0
    (the mean over an empty pair set is defined as 1.0 by convention; a
    1-atom candidate is maximally self-coherent)."""
    idx = _FakeSemanticIndex({})
    cands = [{"id": "c", "cited_atoms": ["only"], "origin": [sources.LLM]}]
    ranked = sources.rank_by_semantic_coherence(cands, idx)
    assert ranked[0]["coherence"] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# REQ-INDUCE-056: budget tracking halts LLM source
# ---------------------------------------------------------------------------


def test_budget_halts_llm_but_other_sources_complete(tmp_path: Path, monkeypatch) -> None:
    """REQ-INDUCE-056: NEUROSYM_INDUCTION_BUDGET_USD=0.01 halts LLM after
    the first call (each stub call costs 0.008); Horn-body and Popper
    sources run to completion."""
    proj = _seed_project(
        tmp_path / "budget",
        atoms=_fixture_atoms(),
        predicates=_fixture_predicates(),
    )
    monkeypatch.setenv("NEUROSYM_INDUCTION_BUDGET_USD", "0.01")
    # Force a high per-call cost so the budget exhausts on call 2.
    monkeypatch.setenv("NEUROSYM_INDUCTION_STUB_COST_USD", "0.008")
    rc = orch.main([str(proj)])
    assert rc == 0
    budget_log = proj / "work" / "induction" / "budget.json"
    assert budget_log.exists()
    data = json.loads(budget_log.read_text(encoding="utf-8"))
    assert data["limit_usd"] == pytest.approx(0.01)
    assert data["spent_usd"] <= 0.01 + 0.008  # one overshoot is allowed at the boundary
    assert data["llm_halted"] is True
    # Horn-body and Popper still contributed; verify by reading the queue.
    payload = read_edn_file(proj / "work" / "induction" / "candidates.edn")
    origins = set()
    for c in payload[Keyword("candidates")]:
        for o in c.get(Keyword("origin"), []):
            origins.add(o)
    assert Keyword("horn-body") in origins
    assert Keyword("popper") in origins


def test_budget_unset_does_not_halt_llm(tmp_path: Path, monkeypatch) -> None:
    """REQ-INDUCE-056: WHERE NEUROSYM_INDUCTION_BUDGET_USD is unset, the
    LLM source runs without spend-tracking enforcement; the budget log
    still emits with limit_usd=null."""
    proj = _seed_project(
        tmp_path / "unbudgeted",
        atoms=_fixture_atoms(),
        predicates=_fixture_predicates(),
    )
    monkeypatch.delenv("NEUROSYM_INDUCTION_BUDGET_USD", raising=False)
    rc = orch.main([str(proj)])
    assert rc == 0
    budget_log = proj / "work" / "induction" / "budget.json"
    data = json.loads(budget_log.read_text(encoding="utf-8"))
    assert data["limit_usd"] is None
    assert data["llm_halted"] is False


# ---------------------------------------------------------------------------
# REQ-INDUCE-046: generated candidates must use grammar-supported operators
# ---------------------------------------------------------------------------


# The canonical operator set, mirrored from `_induction_grammar.cljs`'s
# SUPPORTED-OPERATORS and `codegen_axioms.py`'s _SUPPORTED_ASSERT_HEADS.
_SUPPORTED_OPS = {
    "=", "~=", "approx=",
    "<", "<=", ">", ">=",
    "+", "-", "*", "/",
    "and", "or", "not", "=>", "ite",
    "sum", "count", "in", "select",
    "forall", "exists",
}


def _assert_body(edn: str) -> str:
    """Pull the text following ``:assert`` up to ``:on-unsat`` from a
    generated defconstraint EDN string."""
    start = edn.index(":assert") + len(":assert")
    end = edn.index(":on-unsat", start)
    return edn[start:end]


def _operator_heads(assert_body: str) -> set[str]:
    """Collect every operator head (the symbol immediately after a ``(``
    that is not a ``:keyword`` predicate call) from an :assert body.

    Mirrors the cljs ``collect-operators`` walk: a ``(`` followed by a
    keyword is a predicate call (skipped); a ``(`` followed by anything
    else is an operator call whose head is the first token."""
    import re

    heads: set[str] = set()
    for m in re.finditer(r"\(\s*([^\s()]+)", assert_body):
        head = m.group(1)
        if head.startswith(":"):
            continue  # predicate call, not an operator
        heads.add(head)
    return heads


def _grammar_check_via_nbb(form_edn: str, schema_edn: str) -> dict:
    """Run the real `_induction_grammar.cljs` gate against a generated
    candidate by writing the eval expression to a temp .cljs file under
    the scripts dir and shelling into nbb.

    We invoke nbb on a file rather than `nbb -e <expr>` because the `=>`
    operator the Horn-body source emits contains `>`, which the Windows
    `cmd.exe` nbb shim treats as a redirection metacharacter on the
    command line. A file argument sidesteps that."""
    import os
    import shutil
    import subprocess
    import tempfile

    nbb = shutil.which("nbb")
    assert nbb is not None
    grammar_dir = SCRIPTS_PARENT / "scripts"
    expr = (
        "(require '[_induction-grammar :as g]) "
        f"(println (g/grammar-conforming-json {json.dumps(form_edn)} "
        f"{json.dumps(schema_edn)}))"
    )
    with tempfile.NamedTemporaryFile(
        "w", suffix=".cljs", dir=str(grammar_dir), delete=False, encoding="utf-8"
    ) as fh:
        fh.write(expr)
        script = fh.name
    try:
        result = subprocess.run(
            [nbb, "--classpath", str(grammar_dir), script],
            capture_output=True, text=True, check=False, timeout=60,
        )
    finally:
        os.unlink(script)
    assert result.returncode == 0, f"nbb failed: {result.stderr!r}"
    line = result.stdout.strip().splitlines()[-1]
    return json.loads(line)


def test_generated_candidates_pass_the_real_grammar_gate(seeded_project: Path) -> None:
    """generators-emit-unsupported-ops: every Horn-body and Stub-LLM
    candidate, run through the production cljs grammar gate, must
    conform. Before the fix, `implies` / `positive` were rejected as
    `:grammar-fail/illegal-op`. Skips when nbb is not on PATH."""
    import shutil

    if not shutil.which("nbb"):
        pytest.skip("nbb not available on PATH")

    schema = orch.load_schema(seeded_project)
    atoms = orch.load_atoms(seeded_project)
    # Schema EDN string with the fixture predicates so the gate does not
    # trip on :grammar-fail/unknown-predicate.
    preds = " ".join(
        f":{name} {{:arg-sorts [:s] :return :real}}"
        for name in ("basic-reproduction-number", "herd-immunity-threshold",
                     "vaccination-coverage")
    )
    schema_edn = f"{{:predicates {{{preds}}} :sorts [:s]}}"

    cands = list(sources.horn_mine(atoms, schema))
    cluster = [a for a in atoms if a["predicate"] == "basic-reproduction-number"]
    cands += list(
        sources.llm_propose(
            schema=schema, cluster=cluster, provider=sources.StubProposer()
        )
    )
    assert cands
    for c in cands:
        result = _grammar_check_via_nbb(c["edn"], schema_edn)
        assert result["ok"] is True, (
            f"candidate rejected by grammar gate: {result} :: {c['edn']}"
        )


def test_horn_candidates_use_supported_operators(seeded_project: Path) -> None:
    """REQ-INDUCE-046: every operator a Horn-body candidate emits must be
    in the BookLogic supported-operator set, so the grammar gate accepts
    it. `implies` is not in the set; the implication head is `=>`."""
    schema = orch.load_schema(seeded_project)
    atoms = orch.load_atoms(seeded_project)
    for c in sources.horn_mine(atoms, schema):
        ops = _operator_heads(_assert_body(c["edn"]))
        illegal = ops - _SUPPORTED_OPS
        assert not illegal, f"Horn candidate emits unsupported op(s) {illegal}: {c['edn']}"


def test_stub_llm_candidate_uses_supported_operators(seeded_project: Path) -> None:
    """REQ-INDUCE-046: the Stub LLM proposer must emit only supported
    operators. `positive` is not in the set; use a numeric comparison."""
    schema = orch.load_schema(seeded_project)
    atoms = orch.load_atoms(seeded_project)
    cluster = [a for a in atoms if a["predicate"] == "basic-reproduction-number"]
    cands = sources.llm_propose(
        schema=schema, cluster=cluster, provider=sources.StubProposer()
    )
    assert cands
    for c in cands:
        ops = _operator_heads(_assert_body(c["edn"]))
        illegal = ops - _SUPPORTED_OPS
        assert not illegal, f"Stub candidate emits unsupported op(s) {illegal}: {c['edn']}"


# ---------------------------------------------------------------------------
# REQ-INDUCE-041/043: Phase V proposer wiring
# ---------------------------------------------------------------------------


def test_phase_v_available_when_proposer_module_present() -> None:
    """phase-v-import-always-fails: the Phase V conditional import must
    resolve a symbol that actually exists in `_induction_proposer`, so
    PHASE_V_AVAILABLE is True when the proposer module is on the branch."""
    import importlib

    import scripts._induction_sources as fresh
    fresh = importlib.reload(fresh)
    assert fresh.PHASE_V_AVAILABLE is True, (
        "PHASE_V_AVAILABLE must be True when scripts._induction_proposer "
        "is importable; the conditional import targets a nonexistent symbol"
    )
    assert fresh._phase_v_propose is not None


def test_phase_v_propose_returns_candidate_dict(seeded_project: Path, monkeypatch) -> None:
    """phase-v-import-always-fails: when Phase V is active, llm_propose
    must hand back a well-shaped candidate dict (not a raw EDN string),
    driven by the deterministic stub provider so no live LLM is called."""
    monkeypatch.setenv("NEUROSYM_LLM_PROVIDER", "stub")
    canned = (
        "(defconstraint :induced/llm-r0 :backend :z3 "
        ":assert (> (:basic-reproduction-number ?d) 0) "
        ':on-unsat {:defect :D-induced-l :severity :advisory :message "x"})'
    )
    monkeypatch.setenv("NEUROSYM_STUB_CANDIDATE", canned)

    schema = orch.load_schema(seeded_project)
    atoms = orch.load_atoms(seeded_project)
    cluster = [a for a in atoms if a["predicate"] == "basic-reproduction-number"]
    cands = sources.llm_propose(
        schema=schema, cluster=cluster, provider=sources.StubProposer()
    )
    assert cands, "Phase V path must yield at least one candidate"
    for c in cands:
        assert isinstance(c, dict), f"candidate must be a dict, got {type(c)}"
        assert isinstance(c["canonical_form"], str)
        assert isinstance(c["edn"], str)
        assert sources.LLM in c["origin"]
