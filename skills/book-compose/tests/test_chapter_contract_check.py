import pytest

pytestmark = [pytest.mark.windows_canary, pytest.mark.needs_spacy_model]

from scripts.chapter_contract_check import check_draft


GOOD_DRAFT = """
# Source Navigation and Persistent Synthesis

The script provisions the server. The daemon loads configurations.

The pipeline has three phases.
"""

HEDGY_DRAFT = """
# Bad Draft

The script might fail. The system seems to handle most requests, though it could occasionally drop. Generally, things work.
"""

GOOD_CONTRACT = {
    "chapter_id": "ch-03",
    "title": "Source Navigation",
    "purpose": "Explain ingest and synthesis",
    "audience": "senior-engineer",
    "chapter_type": "synthesis",
    "evidence_requirements": {"minimum_verified_claims": 0, "max_unresolved_conflicts": 0},
    "acceptance_tests": ["hedge_count == 0", "passive_voice_ratio < 0.05"],
    "output_formats": ["markdown"],
}


def test_clean_draft_passes(tmp_path):
    draft = tmp_path / "draft.md"
    draft.write_text(GOOD_DRAFT, encoding="utf-8")
    result = check_draft(draft, GOOD_CONTRACT)
    assert result.passes is True


def test_hedgy_draft_fails(tmp_path):
    draft = tmp_path / "draft.md"
    draft.write_text(HEDGY_DRAFT, encoding="utf-8")
    result = check_draft(draft, GOOD_CONTRACT)
    assert result.passes is False
    assert any("hedge_count" in i for i in result.failed_tests)


def test_result_includes_metrics(tmp_path):
    draft = tmp_path / "draft.md"
    draft.write_text(HEDGY_DRAFT, encoding="utf-8")
    result = check_draft(draft, GOOD_CONTRACT)
    assert "hedge_count" in result.metrics
    assert "passive_voice_ratio" in result.metrics


LEAKY_DRAFT = """
# Sample

The script provisions the server [clm-2026-000001]. The daemon loads configurations [clm-2026-000002].
"""


def test_leaky_draft_fails_citation_check(tmp_path):
    draft = tmp_path / "draft.md"
    draft.write_text(LEAKY_DRAFT, encoding="utf-8")
    contract = {
        **GOOD_CONTRACT,
        "acceptance_tests": ["citation_token_count == 0"],
    }
    result = check_draft(draft, contract)
    assert result.passes is False
    assert result.metrics["citation_token_count"] == 2
    assert "citation_token_count" in result.failed_tests[0]


def test_clean_draft_has_zero_citation_tokens(tmp_path):
    draft = tmp_path / "draft.md"
    draft.write_text(GOOD_DRAFT, encoding="utf-8")
    result = check_draft(draft, GOOD_CONTRACT)
    assert result.metrics["citation_token_count"] == 0


def test_workspace_style_overrides_env_set(tmp_path, monkeypatch):
    # Build workspace structure: ws/CLAUDE.md, ws/style-overrides.json,
    # ws/chapters/drafts/ch-NN/draft.md
    ws = tmp_path / "ws"
    drafts_dir = ws / "chapters" / "drafts" / "ch-01"
    drafts_dir.mkdir(parents=True)
    (ws / "CLAUDE.md").write_text("# workspace marker", encoding="utf-8")
    overrides = ws / "style-overrides.json"
    overrides.write_text("{}", encoding="utf-8")
    draft = drafts_dir / "draft.md"
    draft.write_text(GOOD_DRAFT, encoding="utf-8")

    monkeypatch.delenv("RUSSELLIAN_OVERRIDES", raising=False)
    check_draft(draft, GOOD_CONTRACT)
    import os as _os
    assert _os.environ.get("RUSSELLIAN_OVERRIDES") == str(overrides)
