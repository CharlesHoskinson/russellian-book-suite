"""skill_api exports all five capabilities at API 0.3."""
import skill_api


def test_api_version_is_0_3():
    assert skill_api.API_VERSION == (0, 3)


def test_exports_all_capabilities():
    for name in [
        "expand_seeds", "rank", "triage", "apply_veto", "download_and_ingest", "run_acquire",
        "build_topic_map", "build_disputed_questions", "build_concept_reconciliation", "run_synthesize",
        "project_lens",
        "build_coverage_report", "seed_from_gap_report",
        "build_positions", "render_per_rule", "render_consensus_map",
        "render_adversarial", "governance_filter", "GateDecision",
    ]:
        assert hasattr(skill_api, name), f"missing export: {name}"
