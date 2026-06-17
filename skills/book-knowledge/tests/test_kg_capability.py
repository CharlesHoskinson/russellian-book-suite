"""Cross-graph capability / acceptance test (P4.3) — THE deliverable.

This is the "test of the abilities of the skill". It proves the homoiconic KG's
headline ability: the CODE graph (from graphify) and the CLAIMS graph (from the
ledger) live in ONE Cozo store and a SINGLE query can join across both. The
parallel RDF/SPARQL path could not do this — it holds only claims, never the code
graph — so this join is genuinely new capability, not a re-port.

Scenario: a couple of verified claims (plus a near-miss proposed claim) projected
from a synthetic ledger; the fixture code graph projected from graphify; and a
handful of explicit ``code-claim-link`` rows connecting code modules to the claims
they support. The unified query reaches code-node -> code-claim-link -> claim and
returns the (code, claim) pairs for VERIFIED claims only.

(Production semantics for deriving code<->claim links from real data — a claim's
source file resolving to a code module, symbol references — is a follow-on; the
link is an explicit relation here, which is all the join needs to be proven.)
"""
from __future__ import annotations

from pathlib import Path

from scripts.cozo_store import CozoStore
from scripts.ledger import append_claim
from scripts.project_graphify import project_graphify
from scripts.project_ledger_cozo import project_ledger
from scripts.workspace import WorkspaceLayout, init_workspace

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "assets" / "kg-schema.edn"
FIXTURE = Path(__file__).parent / "fixtures" / "graphify-sample.json"


def _claim(claim_id: str, status: str = "verified", **overrides) -> dict:
    record = {
        "claim_id": claim_id,
        "canonical_text": "a sufficiently long canonical claim text",
        "status": status,
        "claim_type": "fact",
        "confidence": 0.9,
        "source_spans": [
            {"doc_id": "doc-1", "locator_text": "the source locator text"}
        ],
        "created_at": "2026-06-16T00:00:00+00:00",
    }
    record.update(overrides)
    return record


def _unified_store(tmp_path: Path) -> CozoStore:
    """One store holding BOTH graphs + the explicit code<->claim links."""
    root = init_workspace(tmp_path / "ws")
    layout = WorkspaceLayout(root)

    # Claims graph: two verified claims + a near-miss proposed claim.
    append_claim(layout, _claim("clm-2026-000001", status="verified"))
    append_claim(layout, _claim("clm-2026-000002", status="verified"))
    append_claim(layout, _claim("clm-2026-000003", status="proposed"))

    store = CozoStore.in_memory(schema_path=SCHEMA_PATH)
    project_ledger(layout, store)         # claims graph
    project_graphify(FIXTURE, store)      # code graph (mod_alpha, mod_beta, ...)

    # Explicit code<->claim links (the fusion edge). mod_alpha supports a verified
    # claim AND the proposed near-miss; mod_beta supports the other verified claim.
    store.load(
        "code-claim-link",
        [
            {
                "id": "mod_alpha\x1fclm-2026-000001",
                "code_id": "mod_alpha",
                "claim_id": "clm-2026-000001",
            },
            {
                # NEAR-MISS: link to a NON-verified (proposed) claim — must be
                # excluded by the verified filter in the unified query.
                "id": "mod_alpha\x1fclm-2026-000003",
                "code_id": "mod_alpha",
                "claim_id": "clm-2026-000003",
            },
            {
                "id": "mod_beta\x1fclm-2026-000002",
                "code_id": "mod_beta",
                "claim_id": "clm-2026-000002",
            },
        ],
    )
    return store


def test_code_and_claims_unified_query(tmp_path: Path) -> None:
    """ONE query joins code-node -> code-claim-link -> claim (verified only).

    The join spans both graphs in a single store. The near-miss link (to a
    proposed claim) must NOT appear, proving the verified filter joins through the
    claims graph while keyed off the code graph.
    """
    store = _unified_store(tmp_path)

    # code-node --(code-claim-link.code-id)--> link --(claim-id)--> claim,
    # filtered to verified claims. All three relations participate in ONE query.
    rows = store.query_edn(
        "(defquery :code-supported-by-verified-claims "
        " :find [?code-label ?claim-id]"
        " :where [[?c :code-node/id ?code-id]"
        "         [?c :code-node/label ?code-label]"
        "         [?l :code-claim-link/code-id ?code-id]"
        "         [?l :code-claim-link/claim-id ?claim-id]"
        "         [?cl :claim/id ?claim-id]"
        "         [?cl :claim/status \"verified\"]])"
    )

    pairs = sorted(tuple(r) for r in rows)
    assert pairs == [
        ("alpha.py", "clm-2026-000001"),
        ("beta.py", "clm-2026-000002"),
    ]
    # The near-miss (proposed) claim is excluded.
    assert ("alpha.py", "clm-2026-000003") not in pairs


def test_count_verified_claims_per_code_node(tmp_path: Path) -> None:
    """Second capability assertion: an aggregation spanning both graphs.

    Proves the two relations co-reside and join under aggregation — count the
    VERIFIED claims linked to each code node. mod_alpha links one verified + one
    proposed claim, so its verified count is 1 (not 2); mod_beta's is 1.
    """
    store = _unified_store(tmp_path)

    rows = store.query_edn(
        "(defquery :verified-claim-count-per-code-node "
        " :find [?code-label (count-distinct ?claim-id)]"
        " :where [[?c :code-node/id ?code-id]"
        "         [?c :code-node/label ?code-label]"
        "         [?l :code-claim-link/code-id ?code-id]"
        "         [?l :code-claim-link/claim-id ?claim-id]"
        "         [?cl :claim/id ?claim-id]"
        "         [?cl :claim/status \"verified\"]])"
    )

    counts = {r[0]: r[1] for r in rows}
    assert counts == {"alpha.py": 1, "beta.py": 1}
