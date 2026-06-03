"""Stage-awareness tests for book-qa.

book-qa's mechanical defects (D1-D8) are register-neutral integrity checks:
citations, broken xrefs, asset 404s, heading hierarchy, count-contracts. They
do not penalise an informal/conversational register, so a Feynman-final chapter
needs no suppression there. The one register-sensitive mechanical defect, D6
(paragraph-length variance / mean), only ever emits MINOR severity and is
therefore never in the hard-fail set — it cannot false-fail a release.

The register-sensitive checks that CAN hard-fail live in the Stage-2 per-chapter
QA swarm (checklist items C10 paragraph-length variance and C11 Russell-style
discipline): an agent marking either `critical` blocks release. Those checks are
driven by the checklist payload, so the fix is to thread the contract `stage`
marker into the chapter QA payload `meta` and have the checklist instruct the
agent to relax C10/C11 for feynman-final chapters.

These tests pin:
  * stage threading into `prepare_chapter_payload` meta when a feynman-final
    contract is present,
  * default behaviour (no contract / russell stage) is unchanged,
  * D6 never appears in the sentinel hard-fail set regardless of stage.
"""
from __future__ import annotations

import json
from pathlib import Path

from scripts.dispatch_chapter_qa import prepare_chapter_payload
from scripts.sentinel import _is_hard_fail


def _write_draft(workspace: Path, chapter_id: str, text: str = "# Chapter 1: X\n\nBody.\n") -> None:
    draft = workspace / "chapters" / "drafts" / chapter_id / "draft.md"
    draft.parent.mkdir(parents=True, exist_ok=True)
    draft.write_text(text, encoding="utf-8")


def _write_contract(workspace: Path, chapter_id: str, stage: str | None) -> None:
    contracts = workspace / "chapters" / "contracts"
    contracts.mkdir(parents=True, exist_ok=True)
    lines = [f"chapter_id: {chapter_id}", "title: X"]
    if stage is not None:
        lines.append(f'stage: "{stage}"')
    (contracts / f"{chapter_id}.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_stage_threaded_for_feynman_final(tmp_path: Path):
    _write_draft(tmp_path, "ch-01")
    _write_contract(tmp_path, "ch-01", "feynman-final")
    payload = prepare_chapter_payload(tmp_path, "ch-01")
    assert payload.meta.get("chapter_stage") == "feynman-final"
    # Provenance flag the Stage-2 agent keys on for C10/C11 relaxation.
    assert payload.meta.get("relax_register_checks") is True
    # The pre-existing pipeline-stage key (Stage 2) must be untouched.
    assert payload.meta.get("stage") == 2


def test_default_no_contract_unchanged(tmp_path: Path):
    _write_draft(tmp_path, "ch-01")
    payload = prepare_chapter_payload(tmp_path, "ch-01")
    # No contract -> meta is exactly the pre-existing default, no stage marker.
    assert payload.meta == {"stage": 2, "checklist_items": 15}


def test_russell_stage_not_relaxed(tmp_path: Path):
    _write_draft(tmp_path, "ch-01")
    _write_contract(tmp_path, "ch-01", "russell")
    payload = prepare_chapter_payload(tmp_path, "ch-01")
    assert payload.meta.get("chapter_stage") == "russell"
    assert payload.meta.get("relax_register_checks") in (None, False)


def test_d6_never_hard_fails_any_stage():
    # D6 is register-sensitive but only ever MINOR -> never a hard fail,
    # so no stage-conditional suppression is needed for it.
    assert _is_hard_fail("D6", "minor") is False
    # And integrity classes stay hard regardless (sanity).
    assert _is_hard_fail("D1", "critical") is True
    assert _is_hard_fail("D3", "critical") is True
