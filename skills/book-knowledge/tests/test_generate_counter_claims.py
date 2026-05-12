import json
from pathlib import Path
from scripts.workspace import init_workspace, WorkspaceLayout
from scripts.generate_counter_claims import generate_for_claim, prompt_for_claim


def fake_llm(prompt: str) -> str:
    return json.dumps([
        {"text": "Ferry consolidation reversed since 2020.",
         "disagreement_vector": "scope"},
        {"text": "The cited 2019 study used a flawed denominator.",
         "disagreement_vector": "measurement"},
    ])


def test_prompt_for_claim_contains_claim_text():
    claim = {"claim_id": "clm-2026-000001",
             "canonical_text": "Bermuda's ferry network expanded since 2020."}
    p = prompt_for_claim(claim)
    assert "Bermuda's ferry network expanded since 2020." in p
    assert "rival" in p.lower()
    assert "disagreement" in p.lower()


def test_generate_for_claim_writes_records(tmp_path):
    init_workspace(tmp_path)
    layout = WorkspaceLayout(tmp_path)
    target = {"claim_id": "clm-2026-000001",
              "canonical_text": "Bermuda's ferry network expanded since 2020.",
              "status": "verified", "claim_type": "fact", "confidence": 0.8,
              "source_spans": [{"doc_id": "d", "locator_text": "abcd"}],
              "created_at": "2026-05-11T00:00:00Z",
              "load_bearing": True}
    layout.ledger.write_text(json.dumps(target) + "\n", encoding="utf-8")
    ids = generate_for_claim(tmp_path, target["claim_id"], llm_call=fake_llm)
    assert len(ids) == 2
    cc_path = layout.root / "claims" / "counter-claims.jsonl"
    items = [json.loads(l) for l in cc_path.read_text(encoding="utf-8").splitlines()]
    assert {it["target_claim_id"] for it in items} == {"clm-2026-000001"}
    assert {it["disagreement_vector"] for it in items} == {"scope", "measurement"}


def test_generate_for_claim_appends_ids_to_target(tmp_path):
    init_workspace(tmp_path)
    layout = WorkspaceLayout(tmp_path)
    target = {"claim_id": "clm-2026-000001",
              "canonical_text": "X happens since 2020.",
              "status": "verified", "claim_type": "fact", "confidence": 0.8,
              "source_spans": [{"doc_id": "d", "locator_text": "abcd"}],
              "created_at": "2026-05-11T00:00:00Z",
              "load_bearing": True}
    layout.ledger.write_text(json.dumps(target) + "\n", encoding="utf-8")
    new_ids = generate_for_claim(tmp_path, target["claim_id"], llm_call=fake_llm)
    records = [json.loads(l) for l in layout.ledger.read_text(encoding="utf-8").splitlines()]
    latest = [r for r in records if r["claim_id"] == "clm-2026-000001"][-1]
    assert latest.get("counter_claim_ids") == new_ids
