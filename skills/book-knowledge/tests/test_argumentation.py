"""Tests for grounded argumentation labels and warnings (REQ-ARG-001..007)."""
from __future__ import annotations

from pathlib import Path

from scripts.argumentation import (
    ARGUMENTATION_RULES,
    canonical_argumentation_result,
    run_argumentation,
)
from scripts.booklogic_kg import compile_argumentation_rules
from scripts.cozo_store import CozoStore
from scripts.ledger import append_claim
from scripts.project_ledger_cozo import project_ledger
from scripts.workspace import WorkspaceLayout, init_workspace

SCHEMA = Path(__file__).resolve().parents[1] / "assets" / "kg-schema.edn"


def _claim(
    num: int,
    *,
    conflicts_with: list[str] | None = None,
    load_bearing: bool = False,
    axiom: bool = False,
) -> dict:
    cid = f"clm-2026-{num:06d}"
    return {
        "claim_id": cid,
        "canonical_text": f"Argument fixture claim {num}",
        "status": "verified",
        "claim_type": "fact",
        "confidence": 0.9,
        "load_bearing": load_bearing,
        "axiom": axiom,
        "source_spans": [{"doc_id": f"doc-{num}", "locator_text": f"locator {num}"}],
        "created_at": "2026-06-18T00:00:00+00:00",
        "conflicts_with": conflicts_with or [],
    }


def _fixture_store() -> CozoStore:
    store = CozoStore.in_memory(SCHEMA)
    claims = [
        _claim(1),
        _claim(2, conflicts_with=["clm-2026-000003"]),
        _claim(3, load_bearing=True),
        _claim(4, conflicts_with=["clm-2026-000005"]),
        _claim(5, conflicts_with=["clm-2026-000004"]),
        _claim(6, conflicts_with=["clm-2026-000007"]),
        _claim(7, conflicts_with=["clm-2026-000008"]),
        _claim(8, conflicts_with=["clm-2026-000006"]),
        _claim(9, load_bearing=True),
        _claim(10, load_bearing=True),
        _claim(11, load_bearing=True),
        _claim(12, axiom=True),
        _claim(13, load_bearing=True),
        _claim(14),
        _claim(15, load_bearing=True),
    ]
    claims[0]["conflicts_with"] = ["clm-2026-000002"]
    store.load(
        "claim",
        [
            {
                "id": c["claim_id"],
                "canonical_text": c["canonical_text"],
                "status": c["status"],
                "claim_type": c["claim_type"],
                "confidence": c["confidence"],
                "load_bearing": c["load_bearing"],
                "axiom": c["axiom"],
                "created_at": c["created_at"],
            }
            for c in claims
        ],
    )
    store.load(
        "claim-conflict",
        [
            {
                "id": f"{c['claim_id']}\x1f{target}",
                "claim_id": c["claim_id"],
                "other_id": target,
            }
            for c in claims
            for target in c["conflicts_with"]
        ],
    )
    store.load(
        "counter-claim",
        [
            {
                "id": "cc-2026-aaaaaa",
                "cc_id": "cc-2026-aaaaaa",
                "target_claim_id": "clm-2026-000009",
                "cc_status": "open",
            },
            {
                "id": "cc-2026-bbbbbb",
                "cc_id": "cc-2026-bbbbbb",
                "target_claim_id": "clm-2026-000010",
                "cc_status": "addressed",
            },
        ],
    )
    store.load(
        "claim-implies",
        [
            {
                "id": "clm-2026-000001\x1fclm-2026-000003",
                "claim_id": "clm-2026-000001",
                "target_id": "clm-2026-000003",
            },
            {
                "id": "clm-2026-000001\x1fclm-2026-000009",
                "claim_id": "clm-2026-000001",
                "target_id": "clm-2026-000009",
            },
            {
                "id": "clm-2026-000001\x1fclm-2026-000010",
                "claim_id": "clm-2026-000001",
                "target_id": "clm-2026-000010",
            },
            {
                "id": "clm-2026-000012\x1fclm-2026-000011",
                "claim_id": "clm-2026-000012",
                "target_id": "clm-2026-000011",
            },
            {
                "id": "clm-2026-000014\x1fclm-2026-000013",
                "claim_id": "clm-2026-000014",
                "target_id": "clm-2026-000013",
            },
        ],
    )
    return store


def _labels(result: dict) -> dict[str, str]:
    return {
        row["claim_id"]: row["label"]
        for row in result["labels"]
    }


def _warnings(result: dict, warning_type: str) -> list[dict]:
    return [
        row for row in result["warnings"]
        if row["type"] == warning_type
    ]


def test_derived_relations_present() -> None:
    """REQ-ARG-001: derived relations exist and input edge rows are unchanged."""
    store = _fixture_store()
    before = store.query("?[id, claim_id, other_id] := *claim_conflict{id, claim_id, other_id}")

    result = run_argumentation(store)

    assert set(result["derived"]) == {
        "attacked",
        "defended",
        "undefeated-attacker",
        "grounded-accepted",
        "grounded-rejected",
    }
    assert {
        ("clm-2026-000002", "clm-2026-000001", "claim"),
        ("clm-2026-000009", "cc-2026-aaaaaa", "counter-claim"),
    }.issubset(
        {
            (row["claim_id"], row["attacker_id"], row["attacker_type"])
            for row in result["derived"]["attacked"]
        }
    )
    assert {
        ("clm-2026-000003", "clm-2026-000002", "clm-2026-000001")
    }.issubset(
        {
            (row["claim_id"], row["attacker_id"], row["defender_id"])
            for row in result["derived"]["defended"]
        }
    )
    assert result["derived"]["grounded-accepted"]
    assert result["derived"]["grounded-rejected"]
    after = store.query("?[id, claim_id, other_id] := *claim_conflict{id, claim_id, other_id}")
    assert after == before


def test_exactly_one_grounded_label() -> None:
    """REQ-ARG-002: every in-scope claim has exactly one grounded label."""
    labels = _labels(run_argumentation(_fixture_store()))

    assert set(labels) == {f"clm-2026-{i:06d}" for i in range(1, 16)}
    assert labels["clm-2026-000001"] == "accepted"
    assert labels["clm-2026-000002"] == "rejected"
    assert labels["clm-2026-000003"] == "accepted"
    assert labels["clm-2026-000004"] == "undecided"
    assert labels["clm-2026-000005"] == "undecided"
    assert labels["clm-2026-000006"] == "undecided"
    assert labels["clm-2026-000007"] == "undecided"
    assert labels["clm-2026-000008"] == "undecided"
    assert labels["clm-2026-000009"] == "rejected"
    assert labels["clm-2026-000010"] == "accepted"
    assert len(labels) == len(set(labels))


def test_grounded_only() -> None:
    """REQ-ARG-003: no preferred or stable extension is materialized."""
    result = run_argumentation(_fixture_store())
    script = compile_argumentation_rules(
        ARGUMENTATION_RULES.read_text(encoding="utf-8"),
        SCHEMA,
        max_iterations=3,
        output="labels",
    )

    assert "preferred" not in result
    assert "stable" not in result
    assert "preferred" not in script
    assert "stable" not in script


def test_contested_load_bearing_warning() -> None:
    """REQ-ARG-004: undefeated attackers warn only on contested load-bearing claims."""
    result = run_argumentation(_fixture_store())
    contested = _warnings(result, "contested-load-bearing-with-undefended-attack")

    assert {
        (row["claim_id"], row["attacker_id"])
        for row in contested
    } == {("clm-2026-000009", "cc-2026-aaaaaa")}
    assert "clm-2026-000003" not in {row["claim_id"] for row in contested}
    assert "clm-2026-000010" not in {row["claim_id"] for row in contested}


def test_axiom_only_support_warning() -> None:
    """REQ-ARG-005: axiom-only support warns, non-axiom support does not."""
    result = run_argumentation(_fixture_store())
    axiom_warnings = _warnings(result, "axiom-only-support")

    assert {
        (row["claim_id"], row["support_id"])
        for row in axiom_warnings
    } == {("clm-2026-000011", "clm-2026-000012")}
    assert "clm-2026-000013" not in {row["claim_id"] for row in axiom_warnings}


def test_warning_minimal_justification() -> None:
    """REQ-ARG-006: warnings carry bounded defeater or missing-support causes."""
    result = run_argumentation(_fixture_store())
    contested = _warnings(result, "contested-load-bearing-with-undefended-attack")[0]
    unsupported = _warnings(result, "unsupported-load-bearing")[0]
    axiom = _warnings(result, "axiom-only-support")[0]

    assert contested["justification"] == {
        "kind": "defeater-set",
        "defeaters": ["cc-2026-aaaaaa"],
    }
    assert unsupported["claim_id"] == "clm-2026-000015"
    assert unsupported["justification"] == {
        "kind": "missing-support",
        "note": "load-bearing claim has no support edge",
    }
    assert axiom["justification"] == {
        "kind": "axiom-support",
        "supports": ["clm-2026-000012"],
    }
    for warning in result["warnings"]:
        assert "recursive_derivation" not in warning
        assert len(warning["justification"]) <= 2


def test_acceptance_deterministic(tmp_path: Path) -> None:
    """REQ-ARG-007: same snapshot yields result-set-equal labels via EDN->Cozo."""
    store = _fixture_store()

    first = canonical_argumentation_result(run_argumentation(store))
    second = canonical_argumentation_result(run_argumentation(store))

    assert first == second
    assert compile_argumentation_rules(
        ARGUMENTATION_RULES.read_text(encoding="utf-8"),
        SCHEMA,
        max_iterations=2,
        output="labels",
    ).startswith("claim_node")

    root = init_workspace(tmp_path / "book")
    layout = WorkspaceLayout(root)
    append_claim(layout, _claim(1, conflicts_with=["clm-2026-000002"]))
    append_claim(layout, _claim(2))
    before = layout.ledger.read_bytes()
    projected = CozoStore.in_memory(SCHEMA)
    project_ledger(layout, projected)
    run_argumentation(projected)
    assert layout.ledger.read_bytes() == before


def _chain_store() -> CozoStore:
    """Independent fixture: a length-4 attack chain 101->102->103->104."""
    store = CozoStore.in_memory(SCHEMA)
    ids = [f"clm-2026-{n:06d}" for n in (101, 102, 103, 104)]
    store.load(
        "claim",
        [
            {
                "id": cid,
                "canonical_text": f"chain {cid}",
                "status": "verified",
                "claim_type": "fact",
                "confidence": 0.9,
                "load_bearing": False,
                "axiom": False,
                "created_at": "2026-06-18T00:00:00+00:00",
            }
            for cid in ids
        ],
    )
    store.load(
        "claim-conflict",
        [
            {"id": f"{a}\x1f{b}", "claim_id": a, "other_id": b}
            for a, b in zip(ids[:-1], ids[1:])
        ],
    )
    return store


def test_grounded_chain_generalizes_beyond_fixture() -> None:
    """Auditor generality check: a length-4 attack chain on an independent graph
    yields the correct grounded labels, confirming the fixed point is not
    fixture-fitted. Hand-derived: 101 accepted, 102 rejected, 103 accepted
    (reinstated), 104 rejected."""
    labels = _labels(run_argumentation(_chain_store()))

    assert labels == {
        "clm-2026-000101": "accepted",
        "clm-2026-000102": "rejected",
        "clm-2026-000103": "accepted",
        "clm-2026-000104": "rejected",
    }
