import json
from pathlib import Path

import pytest

from scripts.chapter_contract import load_brief

_CONTRACT_YAML = """\
chapter_id: ch-07
title: Housing and Immigration
purpose: Describe housing costs and immigration rules that govern residency.
audience: developer
chapter_type: reference
claims:
  - clm-2026-000001
must_include:
  - housing rental costs
must_not_do:
  - speculate beyond verified claims
evidence_requirements:
  minimum_verified_claims: 2
  max_unresolved_conflicts: 0
acceptance_tests:
  - hedge_count == 0
output_formats: [markdown]
"""

_OPEN_CC = {
    "id": "cc-2026-abcdef",
    "target_claim_id": "clm-2026-000001",
    "text": "Rival hypothesis here.",
    "disagreement_vector": "scope",
    "status": "open",
    "provenance": {"generator": "abduction-v1", "prompt_sha256": "0" * 64},
    "created_at": "2026-05-11T00:00:00Z",
    "addressed_in_chapter": None,
}


def _seed_workspace(tmp_path: Path):
    ws = tmp_path / "ws"
    (ws / "claims").mkdir(parents=True)
    (ws / "chapters" / "contracts").mkdir(parents=True)
    cc_path = ws / "claims" / "counter-claims.jsonl"
    cc_path.write_text(json.dumps(_OPEN_CC) + "\n", encoding="utf-8")
    contract_path = ws / "chapters" / "contracts" / "ch07.yaml"
    contract_path.write_text(_CONTRACT_YAML, encoding="utf-8")
    return ws, contract_path


def test_loader_emits_must_address_for_open_counter_claims(tmp_path):
    ws, contract_path = _seed_workspace(tmp_path)
    brief = load_brief(ws, contract_path)
    must_address = brief.get("must_address")
    assert must_address is not None
    assert len(must_address) == 1
    entry = must_address[0]
    assert entry["counter_claim_id"] == "cc-2026-abcdef"
    assert entry["target_claim_id"] == "clm-2026-000001"
    assert "Rival hypothesis" in entry["text"]


def test_loader_omits_addressed_or_dismissed(tmp_path):
    ws, contract_path = _seed_workspace(tmp_path)
    addressed_cc = {
        "id": "cc-2026-fedcba",
        "target_claim_id": "clm-2026-000001",
        "text": "Another rival, already addressed.",
        "disagreement_vector": "scope",
        "status": "addressed",
        "provenance": {"generator": "abduction-v1", "prompt_sha256": "0" * 64},
        "created_at": "2026-05-11T00:00:00Z",
        "addressed_in_chapter": "ch07",
    }
    with (ws / "claims" / "counter-claims.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(addressed_cc) + "\n")
    brief = load_brief(ws, contract_path)
    must_address = brief.get("must_address", [])
    assert len(must_address) == 1  # only the open one survives


def test_loader_returns_empty_must_address_when_no_cc_file(tmp_path):
    ws = tmp_path / "ws"
    (ws / "claims").mkdir(parents=True)
    (ws / "chapters" / "contracts").mkdir(parents=True)
    contract_path = ws / "chapters" / "contracts" / "ch07.yaml"
    contract_path.write_text(_CONTRACT_YAML, encoding="utf-8")
    # no counter-claims.jsonl
    brief = load_brief(ws, contract_path)
    assert brief["must_address"] == []


def test_loader_skips_cc_targeting_other_chapter_claims(tmp_path):
    ws, contract_path = _seed_workspace(tmp_path)
    unrelated_cc = {
        "id": "cc-2026-999999",
        "target_claim_id": "clm-2026-999999",  # not in ch-07 contract
        "text": "Unrelated rival.",
        "disagreement_vector": "scope",
        "status": "open",
        "provenance": {"generator": "abduction-v1", "prompt_sha256": "0" * 64},
        "created_at": "2026-05-11T00:00:00Z",
        "addressed_in_chapter": None,
    }
    with (ws / "claims" / "counter-claims.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(unrelated_cc) + "\n")
    brief = load_brief(ws, contract_path)
    ids = [e["counter_claim_id"] for e in brief["must_address"]]
    assert "cc-2026-999999" not in ids
    assert "cc-2026-abcdef" in ids
