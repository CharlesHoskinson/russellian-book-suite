"""Live warning surface scaffold tests (REQ-DRAFT-007..012)."""
from __future__ import annotations

import json
from pathlib import Path


def _bundle(
    *,
    warnings: list[dict] | None = None,
    contradiction_alerts: list[dict] | None = None,
    effective_confidence: list[dict] | None = None,
    threshold: float = 0.6,
    extra_claims: list[dict] | None = None,
) -> dict:
    claims = [
        {
            "claim-id": "clm-2026-000201",
            "text": "The core claim is load bearing.",
            "status": "verified",
            "confidence": 0.95,
            "source-span-ids": ["span-201"],
        },
        {
            "claim-id": "clm-2026-000202",
            "text": "The second claim must not conflict with the first.",
            "status": "verified",
            "confidence": 0.90,
            "source-span-ids": ["span-202"],
        },
    ]
    if extra_claims:
        claims.extend(extra_claims)
    payload = {
        "schema": "chapter-retrieval-bundle/v1",
        "chapter-id": "ch-01",
        "chapter-uri": "https://example.org/book-knowledge/chapters/ch-01",
        "dominant-communities": [],
        "load-bearing-claims": claims,
        "unresolved-rebuttals": [],
        "source-span-anchors": [
            {
                "span-id": "span-201",
                "claim-id": "clm-2026-000201",
                "doc-id": "doc-a",
                "node-id": "node-a",
                "page-index": 1,
                "locator-text": "The core claim is load bearing.",
            },
            {
                "span-id": "span-202",
                "claim-id": "clm-2026-000202",
                "doc-id": "doc-b",
                "node-id": "node-b",
                "page-index": 2,
                "locator-text": "The second claim is distinct.",
            },
        ],
        "effective-confidence-threshold": threshold,
    }
    if warnings is not None:
        payload["warnings"] = warnings
    if contradiction_alerts is not None:
        payload["contradiction-alerts"] = contradiction_alerts
    if effective_confidence is not None:
        payload["effective-confidence"] = effective_confidence
    return {
        "chapter_id": "ch-01",
        "payload": payload,
        "json": json.dumps(payload, indent=2, sort_keys=True) + "\n",
        "edn": "{:schema \"chapter-retrieval-bundle/v1\"}\n",
        "prompt_scaffold": "Thesis cue: write from anchored claims.",
    }


def _surface(bundle: dict) -> list[dict]:
    from scripts.draft_chapter import build_bundle_scaffold

    return build_bundle_scaffold(bundle).get("warning-surface", [])


def test_scaffold_carries_warning_surface() -> None:
    """REQ-DRAFT-007: scaffold exposes S3, S4, and S5 warning kinds."""
    from scripts.draft_chapter import build_bundle_scaffold, render_drafting_prompt

    scaffold = build_bundle_scaffold(
        _bundle(
            warnings=[
                {
                    "type": "unsupported-load-bearing",
                    "claim_id": "clm-2026-000201",
                    "justification": {"kind": "missing-support"},
                }
            ],
            contradiction_alerts=[
                {
                    "type": "hard-contradiction",
                    "rule": "quantity-clash",
                    "claim_ids": ["clm-2026-000201", "clm-2026-000202"],
                }
            ],
            effective_confidence=[
                {
                    "claim_id": "clm-2026-000202",
                    "effective": 0.4,
                    "support_erosion_reason": [{"kind": "counter-claim"}],
                }
            ],
        )
    )
    prompt = render_drafting_prompt(scaffold)

    kinds = {row["kind"] for row in scaffold["warning-surface"]}
    assert kinds == {
        "grounded-acceptability",
        "contradiction-alert",
        "effective-confidence",
    }
    assert "Warning surface:" in prompt
    assert "unsupported-load-bearing" in prompt
    assert "do not assert both sides" in prompt
    assert "use hedged phrasing; reason counter-claim" in prompt


def test_contested_claim_defend_or_downgrade() -> None:
    """REQ-DRAFT-008: contested load-bearing claims instruct defend/downgrade."""
    from scripts.draft_chapter import build_bundle_scaffold, render_drafting_prompt

    contested = build_bundle_scaffold(
        _bundle(
            warnings=[
                {
                    "type": "contested-load-bearing-with-undefended-attack",
                    "claim_id": "clm-2026-000201",
                    "attacker_id": "cc-2026-attack",
                },
                {
                    "type": "contested-load-bearing-with-undefended-attack",
                    "claim_id": "clm-2026-outside",
                    "attacker_id": "cc-2026-outside",
                },
            ]
        )
    )
    clean = build_bundle_scaffold(_bundle(warnings=[]))

    prompt = render_drafting_prompt(contested)
    assert {
        "claim-id": "clm-2026-000201",
        "kind": "grounded-acceptability",
        "warning-type": "contested-load-bearing-with-undefended-attack",
        "instruction": "defend-or-downgrade",
        "attacker-id": "cc-2026-attack",
    } in contested["warning-surface"]
    assert "cc-2026-attack" in prompt
    assert "defend or downgrade" in prompt
    assert "clm-2026-outside" not in prompt
    assert "warning-surface" not in clean


def test_contradiction_alert_flags_both_sides() -> None:
    """REQ-DRAFT-009: contradiction alerts flag both in-scope claims."""
    from scripts.draft_chapter import build_bundle_scaffold, render_drafting_prompt

    scaffold = build_bundle_scaffold(
        _bundle(
            contradiction_alerts=[
                {
                    "type": "hard-contradiction",
                    "rule": "quantity-clash",
                    "claim_ids": ["clm-2026-000201", "clm-2026-000202"],
                }
            ]
        )
    )
    clean = build_bundle_scaffold(_bundle(contradiction_alerts=[]))
    prompt = render_drafting_prompt(scaffold)

    conflict_rows = [
        row for row in scaffold["warning-surface"]
        if row["kind"] == "contradiction-alert"
    ]
    assert {row["claim-id"] for row in conflict_rows} == {
        "clm-2026-000201",
        "clm-2026-000202",
    }
    assert "clm-2026-000201: conflicts with clm-2026-000202" in prompt
    assert "clm-2026-000202: conflicts with clm-2026-000201" in prompt
    assert "warning-surface" not in clean


def test_eroded_confidence_named_hedge() -> None:
    """REQ-DRAFT-010: below-threshold effective confidence names hedge reason."""
    from scripts.draft_chapter import build_bundle_scaffold, render_drafting_prompt

    scaffold = build_bundle_scaffold(
        _bundle(
            threshold=0.75,
            effective_confidence=[
                {
                    "claim_id": "clm-2026-000201",
                    "effective": 0.4,
                    "support_erosion_reason": [
                        {"kind": "stale-source", "source_id": "doc-a"}
                    ],
                },
                {
                    "claim_id": "clm-2026-000202",
                    "effective": 0.8,
                    "support_erosion_reason": [{"kind": "counter-claim"}],
                },
            ],
        )
    )
    prompt = render_drafting_prompt(scaffold)

    assert scaffold["warning-surface"] == [
        {
            "kind": "effective-confidence",
            "claim-id": "clm-2026-000201",
            "effective": 0.4,
            "threshold": 0.75,
            "support-erosion-reason": [
                {"kind": "stale-source", "source_id": "doc-a"}
            ],
            "instruction": "hedge-with-reason",
        }
    ]
    assert "use hedged phrasing; reason stale-source" in prompt
    assert "clm-2026-000202: effective confidence" not in prompt


def test_surface_deterministic_no_new_analysis(tmp_path: Path) -> None:
    """REQ-DRAFT-011: same snapshot is deterministic and read-only."""
    from scripts.draft_chapter import build_bundle_scaffold

    ledger = tmp_path / "claims" / "ledger.jsonl"
    ledger.parent.mkdir(parents=True)
    ledger.write_text('{"claim_id":"clm-2026-000201"}\n', encoding="utf-8")
    before = ledger.read_bytes()
    bundle = _bundle(
        warnings=[
            {
                "type": "contested-load-bearing",
                "claim_id": "clm-2026-000201",
                "attacker_id": "cc-2026-attack",
            }
        ],
        effective_confidence=[
            {
                "claim_id": "clm-2026-000201",
                "effective": 0.3,
                "support_erosion_reason_json": '[{"kind":"counter-claim"}]',
            }
        ],
    )

    first = build_bundle_scaffold(bundle)
    second = build_bundle_scaffold(bundle)

    assert first["warning-surface"] == second["warning-surface"]
    assert ledger.read_bytes() == before


def test_surface_respects_prompt_budget() -> None:
    """REQ-DRAFT-012: only load-bearing or in-scope warnings are surfaced."""
    from scripts.draft_chapter import build_bundle_scaffold, render_drafting_prompt

    scaffold = build_bundle_scaffold(
        _bundle(
            warnings=[
                {
                    "type": "unsupported-load-bearing",
                    "claim_id": "clm-2026-000201",
                },
                {
                    "type": "unsupported-load-bearing",
                    "claim_id": "clm-2026-nonloadbearing",
                },
            ],
            contradiction_alerts=[
                {
                    "claim_ids": ["clm-2026-000201", "clm-2026-000202"],
                    "rule": "quantity-clash",
                },
                {
                    "claim_ids": ["clm-2026-outside-a", "clm-2026-outside-b"],
                    "rule": "out-of-scope",
                },
            ],
            effective_confidence=[
                {"claim_id": "clm-2026-000202", "effective": 0.2},
                {"claim_id": "clm-2026-outside-c", "effective": 0.1},
            ],
        )
    )
    prompt = render_drafting_prompt(scaffold)

    surfaced = json.dumps(scaffold["warning-surface"], sort_keys=True)
    assert "clm-2026-000201" in surfaced
    assert "clm-2026-000202" in surfaced
    assert "clm-2026-nonloadbearing" not in surfaced
    assert "clm-2026-outside" not in surfaced
    assert "out-of-scope" not in prompt
