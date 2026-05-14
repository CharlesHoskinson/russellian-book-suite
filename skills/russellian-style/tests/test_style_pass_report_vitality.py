"""style_pass_report v0.2: emits vitality_metrics block + corpus_anchors list."""
from pathlib import Path


def _write(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "draft.md"
    p.write_text(text, encoding="utf-8")
    return p


def test_report_includes_vitality_metrics_block(tmp_path):
    from scripts.style_pass_report import generate_report_dict
    text = "Short sentence one. Another short one. Third short. Fourth short."
    report = generate_report_dict(_write(tmp_path, text))
    assert "vitality_metrics" in report
    vm = report["vitality_metrics"]
    expected_keys = {
        "burstiness_fano_factor",
        "in_band_proportion",
        "ai_vocabulary_violations",
        "concrete_instance_density_violations",
        "epistemic_precision_violations",
        "paragraph_motion_score",
        "russell_vitality_score",
    }
    assert expected_keys <= set(vm.keys())


def test_corpus_anchors_attached_when_paragraph_motion_fires(tmp_path):
    from scripts.style_pass_report import generate_report_dict
    text = (
        "The ledger records claims.\n\n"
        "The graph projects relations.\n\n"
        "The validator enforces shapes.\n\n"
        "The report summarises findings.\n"
    )
    report = generate_report_dict(_write(tmp_path, text))
    motion_fired = any(
        isinstance(item, dict)
        and item.get("section") == "vitality"
        and item.get("finding", {}).get("rule") == "paragraph-motion"
        for item in report.get("findings", [])
    )
    if motion_fired:
        anchors = report["corpus_anchors"]
        assert anchors, "expected anchor when paragraph-motion fires"
        a = anchors[0]
        assert "corpus_id" in a["anchor"]
        assert "calibration_lesson" in a["anchor"]


def test_negative_metrics_block_unchanged(tmp_path):
    from scripts.style_pass_report import generate_report_dict
    text = "Hello world."
    report = generate_report_dict(_write(tmp_path, text))
    assert "negative_metrics" in report
    neg = report["negative_metrics"]
    expected_neg = {
        "hedge_count", "passive_voice_ratio", "modifier_budget_violations",
        "parallel_structure_violations", "listicle_abstract_count", "rhythm_violations",
    }
    assert expected_neg <= set(neg.keys())


def test_build_report_still_works_unchanged(tmp_path):
    """The existing template-based renderer must continue to work."""
    from scripts.style_pass_report import build_report
    text = "Short. Longer sentence here for context."
    report_md = build_report(_write(tmp_path, text))
    assert isinstance(report_md, str)
    assert len(report_md) > 0


def test_report_dict_has_positive_checks_block(tmp_path):
    from scripts.style_pass_report import generate_report_dict
    sample = tmp_path / "draft.md"
    sample.write_text(
        "The ledger records claims, but the act of recording is more than a list — every "
        "entry carries a date, a source, and a state.\n\n"
        "A graph projects relations from those claims, and the projection is where "
        "contradictions surface that the prose would otherwise hide.\n",
        encoding="utf-8",
    )
    report = generate_report_dict(sample)
    assert "positive_checks" in report
    pc = report["positive_checks"]
    for key in (
        "sentence_length_fano",
        "paragraph_shape_diversity",
        "concession_turn_count",
        "concrete_instance_count",
        "template_repetition_rate",
    ):
        assert key in pc, f"missing positive check: {key}"
    assert pc["concession_turn_count"] >= 1


def test_report_dict_includes_ai_staccato_findings(tmp_path):
    from scripts.style_pass_report import generate_report_dict
    sample = tmp_path / "staccato.md"
    sample.write_text(
        "The ledger records claims. It tracks every change.\n\n"
        "The graph holds relations. It projects them from claims.\n\n"
        "The validator checks shapes. It rejects malformed input.\n\n"
        "The report names defects. It links each one to a source.\n",
        encoding="utf-8",
    )
    report = generate_report_dict(sample)
    finds = [f for f in report["findings"]
             if f.get("finding", {}).get("rule") == "staccato-paragraph-run"]
    assert finds, "expected ai_staccato findings to appear in report dict"
