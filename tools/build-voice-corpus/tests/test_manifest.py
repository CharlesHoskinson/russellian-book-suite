from pathlib import Path

from scripts.manifest import STAGES, record, latest_state, pending


def test_latest_state_takes_last_row(tmp_path: Path):
    m = tmp_path / "manifest.jsonl"
    record(m, "vid1", "discovered")
    record(m, "vid1", "sampled")
    record(m, "vid1", "fetched")
    state = latest_state(m)
    assert state["vid1"]["stage"] == "fetched"


def test_skipped_is_terminal(tmp_path: Path):
    m = tmp_path / "manifest.jsonl"
    record(m, "vid1", "sampled")
    record(m, "vid1", "skipped", reason="no_captions")
    state = latest_state(m)
    assert state["vid1"]["stage"] == "skipped"
    assert state["vid1"]["reason"] == "no_captions"


def test_pending_excludes_completed_and_skipped(tmp_path: Path):
    m = tmp_path / "manifest.jsonl"
    record(m, "a", "tagged")
    record(m, "b", "skipped", reason="x")
    record(m, "c", "fetched")
    result = pending(m, ["a", "b", "c", "d"], target="tagged")
    assert result == ["c", "d"]


def test_stage_order_is_canonical():
    assert STAGES.index("discovered") < STAGES.index("tagged")
