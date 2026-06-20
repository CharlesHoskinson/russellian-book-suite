"""Cites REQ-LIVE-007 (concrete-anchor density via Brysbaert)."""
import pytest
pytestmark = pytest.mark.windows_canary
from scripts.concreteness import load_concreteness, conc
from scripts.signal_concrete import score_text


def test_loader_has_known_ratings():
    t = load_concreteness()
    assert t["bank"] >= 4.0 and t["justice"] <= 2.5
    assert conc("banks", t) == t["bank"]          # -s fallback


@pytest.mark.needs_model
def test_concrete_passage_outscores_abstract():
    concrete = "The bank, the vault, the wall, and the box all hold something you can touch."
    abstract = "Justice, freedom, truth, and morality are matters of principle and consideration."
    assert score_text(concrete)["score"] > score_text(abstract)["score"]
