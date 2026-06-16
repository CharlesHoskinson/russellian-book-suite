"""3.6: dispatch_halmos_review must validate the dispatcher's output shape
before treating it as a findings dict — a malformed return (non-dict, or wrong
value types) should fail loud, not as a raw AttributeError at .setdefault()."""
import pytest

pytestmark = pytest.mark.windows_canary

from scripts.dispatch_halmos_review import dispatch_halmos_review


def _ws(tmp_path, chapters):
    ws = tmp_path / "ws"
    for cid, body in chapters.items():
        d = ws / "chapters" / "drafts" / cid
        d.mkdir(parents=True)
        (d / "draft.md").write_text(body, encoding="utf-8")
    (ws / "references").mkdir(parents=True, exist_ok=True)
    return ws


def _chapters():
    return {"ch-01": "The bounded polis question is introduced here.",
            "ch-02": "Atoms jiggle; the bounded polis question returns."}


def test_non_dict_dispatcher_output_raises(tmp_path):
    ws = _ws(tmp_path, _chapters())
    with pytest.raises(ValueError, match=r"(?i)dispatcher.*(dict|mapping|object|shape)"):
        dispatch_halmos_review(ws, "ch-02", dispatcher=lambda payload: ["not", "a", "dict"])


def test_none_dispatcher_output_raises(tmp_path):
    ws = _ws(tmp_path, _chapters())
    with pytest.raises(ValueError, match=r"(?i)dispatcher"):
        dispatch_halmos_review(ws, "ch-02", dispatcher=lambda payload: None)


def test_wrong_value_type_raises(tmp_path):
    ws = _ws(tmp_path, _chapters())
    with pytest.raises(ValueError, match=r"(?i)findings"):
        dispatch_halmos_review(ws, "ch-02",
                               dispatcher=lambda payload: {"findings": "should-be-a-list"})


def test_valid_dispatcher_output_passes(tmp_path):
    ws = _ws(tmp_path, _chapters())
    out = dispatch_halmos_review(ws, "ch-02", dispatcher=lambda payload: {})
    assert out["spiral_coherence"] == "acceptable"
    assert out["findings"] == []
    assert out["per_prior_chapter"] == {}
