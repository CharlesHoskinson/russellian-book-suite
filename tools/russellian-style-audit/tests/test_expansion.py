"""Expansion staging tests — an audit run must not mutate the committed russellian-style
corpus assets unless explicitly promoted. Finding expansion-writes-real-corpus-bypassing-runs."""
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_AUDIT_ROOT = _REPO_ROOT / "tools" / "russellian-style-audit"
sys.path.insert(0, str(_AUDIT_ROOT))

import scripts.expansion as expansion  # noqa: E402


def _stub_pipeline(monkeypatch, run_dir: Path):
    """Stub the build-corpus stage callables so the pipeline runs offline and yields one
    verified entry, without any live LLM call."""
    def fake_extract(**kwargs):
        kwargs["out_path"].parent.mkdir(parents=True, exist_ok=True)
        kwargs["out_path"].write_text('{"candidate_id": "problems-051"}\n', encoding="utf-8")

    def fake_sentinel(**kwargs):
        (run_dir / "passed-sentinel.jsonl").write_text('{"candidate_id": "problems-051"}\n', encoding="utf-8")

    def fake_cross_check(**kwargs):
        kwargs["verified_path"].write_text(
            '{"candidate_id": "problems-051", "source_id": "problems", "line_hint": 1, '
            '"content_locator": "x", "paragraph_text": "Philosophy is two things.", '
            '"rhetorical_move_tag": "domain_contrast", "calibration_lesson": "splits."}\n',
            encoding="utf-8",
        )

    def fake_sample_audit(**kwargs):
        kwargs["out_path"].parent.mkdir(parents=True, exist_ok=True)
        kwargs["out_path"].write_text("# sample\n", encoding="utf-8")
        return [{"candidate_id": "problems-051"}]

    monkeypatch.setattr(expansion, "extract_candidates", fake_extract)
    monkeypatch.setattr(expansion, "run_sentinel_batch", fake_sentinel)
    monkeypatch.setattr(expansion, "run_cross_check_batch", fake_cross_check)
    monkeypatch.setattr(expansion, "sample_audit", fake_sample_audit)
    # Point the live index at a throwaway path so a stray write to the canonical
    # asset would be caught by the assertion below (which checks the real path).
    monkeypatch.setattr(expansion, "extract_llm", lambda p: "")
    monkeypatch.setattr(expansion, "cross_check_llm", lambda p: "")


def test_expansion_does_not_touch_live_corpus_without_promote(monkeypatch, tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    _stub_pipeline(monkeypatch, run_dir)

    appended_to = []
    monkeypatch.setattr(
        expansion, "append_verified_to_index",
        lambda **kw: appended_to.append(Path(kw["index_path"])),
    )
    monkeypatch.setattr(
        expansion, "regenerate_corpus_map",
        lambda **kw: appended_to.append(Path(kw["out_path"])),
    )

    result = expansion.run_expansion_batch(
        batch_id="b1", source_id="problems", source_path=tmp_path / "src.html",
        n=1, run_dir=run_dir, operator_decision_fn=lambda *a: ["accept"],
        promote=False,
    )
    # The canonical committed assets must NOT be written.
    assert expansion._INDEX_PATH not in appended_to
    assert expansion._CORPUS_MAP_PATH not in appended_to
    assert result["appended"] is False
    assert result.get("staged") is True
    # A staged copy must exist under the batch's run_dir.
    assert (run_dir / "staged-index.json").exists() or (run_dir / "verified.jsonl").exists()


def test_expansion_promote_writes_live_corpus(monkeypatch, tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    _stub_pipeline(monkeypatch, run_dir)

    appended_to = []
    monkeypatch.setattr(
        expansion, "append_verified_to_index",
        lambda **kw: appended_to.append(Path(kw["index_path"])),
    )
    monkeypatch.setattr(
        expansion, "regenerate_corpus_map",
        lambda **kw: appended_to.append(Path(kw["out_path"])),
    )

    result = expansion.run_expansion_batch(
        batch_id="b1", source_id="problems", source_path=tmp_path / "src.html",
        n=1, run_dir=run_dir, operator_decision_fn=lambda *a: ["accept"],
        promote=True,
    )
    assert expansion._INDEX_PATH in appended_to
    assert expansion._CORPUS_MAP_PATH in appended_to
    assert result["appended"] is True
