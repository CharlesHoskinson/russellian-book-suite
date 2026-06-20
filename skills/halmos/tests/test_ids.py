import pytest
pytestmark = pytest.mark.windows_canary
from scripts.ids import chapter_n


def test_chapter_n_parses_conforming_ids():
    assert chapter_n("ch-01") == 1
    assert chapter_n("ch-13") == 13
    assert chapter_n("ch-01-v6") == 1
    assert chapter_n("ch-7") == 7


def test_chapter_n_raises_on_malformed_ids():
    with pytest.raises(ValueError):
        chapter_n("intro")
    with pytest.raises(ValueError):
        chapter_n("chapter-3")
