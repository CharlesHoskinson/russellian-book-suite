"""Feynman-final stage integration with the chapter gate.

A contract that declares stage == "feynman-final" must:
  - NOT hard-fail on surface-class Russell dimensions (hedges, conversational
    address) that a Feynman-final chapter legitimately overrides, and
  - expose Feynman metrics in the returned metrics dict so the contract's
    acceptance_tests can gate on Feynman budgets.

The SAME draft under a default contract (no stage) behaves exactly as before.
"""
import pytest

pytestmark = pytest.mark.windows_canary

from scripts.chapter_contract_check import check_draft


# Conversational / direct-address / contraction-laden prose. Russell's surface
# checks (hedging, conversational tone) would flag this; a Feynman-final
# chapter accepts it.
FEYNMAN_DRAFT = """
# How a Daemon Wakes Up

Think of the daemon like a sleepy night watchman. You knock, and it stirs.
Why does it wait? It's listening for a knock on a socket. When you send a
request, it can't just ignore you. It wakes up, reads what you wrote, and
gets to work.

Now imagine a hundred knocks at once. Doesn't that sound like chaos? It would
be, except the watchman keeps a little notebook. Each knock gets a line. He
works through them one by one, the way you'd answer a stack of letters.
"""

FEYNMAN_METRIC_KEYS = [
    "reading_grade_violations",
    "conversational_cold_count",
    "latinate_diction_count",
    "analogy_absent_count",
    "abstraction_heavy_count",
    "curiosity_absent_count",
]


def test_feynman_final_does_not_hard_fail_surface_russell(tmp_path):
    """A feynman-final contract gating only on Feynman budgets does not fail on
    surface Russell dimensions, even though the draft is conversational."""
    draft = tmp_path / "draft.md"
    draft.write_text(FEYNMAN_DRAFT, encoding="utf-8")
    contract = {
        "chapter_id": "ch-07",
        "title": "How a Daemon Wakes Up",
        "purpose": "Teach the request loop by analogy",
        "audience": "developer",
        "chapter_type": "tutorial",
        "evidence_requirements": {
            "minimum_verified_claims": 0,
            "max_unresolved_conflicts": 0,
        },
        # Gate ONLY on Feynman budgets + an integrity check. No surface Russell
        # thresholds (hedge_count, passive_voice_ratio) are listed, so they
        # cannot hard-fail this chapter.
        "acceptance_tests": [
            "conversational_cold_count == 0",
            "citation_token_count == 0",
        ],
        "output_formats": ["markdown"],
        "stage": "feynman-final",
    }
    result = check_draft(draft, contract)
    # Feynman metrics are present.
    for key in FEYNMAN_METRIC_KEYS:
        assert key in result.metrics, f"missing Feynman metric {key}"
    # Surface Russell metrics still computed (for visibility) but not gated.
    assert "hedge_count" in result.metrics
    # Integrity check kept running.
    assert result.metrics["citation_token_count"] == 0
    # Passes: only Feynman + integrity tests gate, and this conversational
    # draft satisfies them.
    assert result.passes is True, result.failed_tests


def test_feynman_final_gates_on_feynman_budget(tmp_path):
    """Feynman metrics actually drive the gate: a contract demanding zero
    abstraction-heavy passages can fail a draft that violates it."""
    draft = tmp_path / "draft.md"
    # Abstract-noun saturated, no analogy: trips abstraction-heavy / analogy.
    draft.write_text(
        "# Abstraction\n\n"
        "The implementation's instantiation of the configuration's "
        "normalization necessitates the materialization of the "
        "serialization's representation through the orchestration of the "
        "transformation's optimization and the reconciliation of the "
        "authorization's federation.\n",
        encoding="utf-8",
    )
    contract = {
        "chapter_id": "ch-08",
        "title": "Abstraction",
        "purpose": "Negative control for Feynman gating",
        "audience": "developer",
        "chapter_type": "tutorial",
        "evidence_requirements": {
            "minimum_verified_claims": 0,
            "max_unresolved_conflicts": 0,
        },
        "acceptance_tests": ["abstraction_heavy_count == 0"],
        "output_formats": ["markdown"],
        "stage": "feynman-final",
    }
    result = check_draft(draft, contract)
    assert result.metrics["abstraction_heavy_count"] >= 1
    assert result.passes is False
    assert any("abstraction_heavy_count" in t for t in result.failed_tests)


def test_default_contract_unchanged_no_feynman_metrics(tmp_path):
    """The SAME conversational draft under a default (no-stage) contract behaves
    exactly as before: Feynman metrics are NOT computed, and a surface Russell
    threshold (hedge_count) still gates normally."""
    draft = tmp_path / "draft.md"
    draft.write_text(FEYNMAN_DRAFT, encoding="utf-8")
    contract = {
        "chapter_id": "ch-09",
        "title": "How a Daemon Wakes Up",
        "purpose": "Default-stage behavior",
        "audience": "developer",
        "chapter_type": "tutorial",
        "evidence_requirements": {
            "minimum_verified_claims": 0,
            "max_unresolved_conflicts": 0,
        },
        "acceptance_tests": ["hedge_count == 0"],
        "output_formats": ["markdown"],
        # no `stage`
    }
    result = check_draft(draft, contract)
    # No Feynman metrics under default stage.
    for key in FEYNMAN_METRIC_KEYS:
        assert key not in result.metrics, f"Feynman metric {key} leaked into default stage"
    # Russell surface metric still present and gating.
    assert "hedge_count" in result.metrics
