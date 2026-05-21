import json
from pathlib import Path

from scripts.audit_sample import sample_audit, evaluate_audit_decisions


def _build_verified(tmp_path: Path, n: int) -> Path:
    path = tmp_path / "verified.jsonl"
    rows = [
        {"candidate_id": f"problems-{i:03d}", "paragraph_text": f"para {i}",
         "rhetorical_move_tag": "domain_contrast",
         "calibration_lesson": f"lesson {i}"}
        for i in range(n)
    ]
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    return path


def test_sample_audit_returns_5pct_floor_one(tmp_path: Path) -> None:
    verified = _build_verified(tmp_path, 100)
    out_md = tmp_path / "sample.md"
    sampled = sample_audit(verified_path=verified, out_path=out_md, sample_rate=0.05, seed=42)
    assert len(sampled) == 5
    assert out_md.exists()
    text = out_md.read_text(encoding="utf-8")
    for entry in sampled:
        assert entry["candidate_id"] in text


def test_sample_audit_with_tiny_batch_samples_at_least_one(tmp_path: Path) -> None:
    verified = _build_verified(tmp_path, 3)
    out_md = tmp_path / "sample.md"
    sampled = sample_audit(verified_path=verified, out_path=out_md, sample_rate=0.05, seed=42)
    assert len(sampled) == 1


def test_evaluate_audit_decisions_halts_above_threshold() -> None:
    decisions = ["accept", "accept", "reject", "accept", "reject"]  # 40% reject rate
    decision = evaluate_audit_decisions(decisions, halt_threshold=0.10)
    assert decision.action == "halt"
    assert decision.reject_rate == 0.4


def test_evaluate_audit_decisions_proceeds_below_threshold() -> None:
    decisions = ["accept"] * 19 + ["reject"]  # 5% reject rate
    decision = evaluate_audit_decisions(decisions, halt_threshold=0.10)
    assert decision.action == "proceed"
    assert decision.reject_rate == 0.05
