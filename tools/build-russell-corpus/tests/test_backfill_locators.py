import json
from pathlib import Path

from scripts.backfill_locators import backfill_content_locators


FIXTURES = Path(__file__).parent / "fixtures"
SOURCE_CACHE = FIXTURES / "source_cache"


def _locatorless_index(tmp_path: Path) -> Path:
    """An index whose entries carry no content_locator — exactly like the 50 committed
    seed entries. line_hint points at the <p> line in problems_subset.html."""
    idx = tmp_path / "index.json"
    idx.write_text(json.dumps({
        "version": "0.1.0",
        "paragraph_count": 2,
        "sources": {
            "problems": {"title": "x", "url": "u", "copyright_status": "public_domain_us", "mode": ["m"]}
        },
        "paragraphs": [
            {"id": "problems-001", "source": "problems", "line_hint": 2,
             "rhetorical_move": "rm1", "tags": ["t1"]},
            {"id": "problems-002", "source": "problems", "line_hint": 3,
             "rhetorical_move": "rm2", "tags": ["t2"]},
        ],
    }, indent=2), encoding="utf-8")
    return idx


def test_backfill_adds_canonical_content_locator(tmp_path: Path) -> None:
    idx_path = _locatorless_index(tmp_path)
    updated = backfill_content_locators(
        index_path=idx_path,
        source_cache_dir=SOURCE_CACHE,
        cache_filename=lambda sid: f"{sid}_subset.html",
    )
    assert updated == 2
    idx = json.loads(idx_path.read_text(encoding="utf-8"))
    e1 = idx["paragraphs"][0]
    assert e1["content_locator"] == (
        "Philosophy, throughout its history, has consisted of two parts inharmoniously "
        "blended: on the one hand a theory as to th"
    )
    # second paragraph in the fixture
    assert idx["paragraphs"][1]["content_locator"].startswith("The failure to separate these two")


def test_backfill_is_idempotent_and_skips_already_backfilled(tmp_path: Path) -> None:
    idx_path = _locatorless_index(tmp_path)
    first = backfill_content_locators(
        index_path=idx_path,
        source_cache_dir=SOURCE_CACHE,
        cache_filename=lambda sid: f"{sid}_subset.html",
    )
    assert first == 2
    second = backfill_content_locators(
        index_path=idx_path,
        source_cache_dir=SOURCE_CACHE,
        cache_filename=lambda sid: f"{sid}_subset.html",
    )
    assert second == 0  # nothing left to backfill


def test_backfilled_locator_matches_reextraction_dedup_key(tmp_path: Path) -> None:
    """The backfilled content_locator must equal content_locator(paragraph_text) of a
    re-extracted candidate, so the canonical-locator dedup branch (Check 4a) catches it."""
    from scripts.corpus_io import content_locator
    from scripts.sentinel import run_sentinel

    idx_path = _locatorless_index(tmp_path)
    backfill_content_locators(
        index_path=idx_path,
        source_cache_dir=SOURCE_CACHE,
        cache_filename=lambda sid: f"{sid}_subset.html",
    )
    paragraph = (
        "Philosophy, throughout its history, has consisted of two parts inharmoniously "
        "blended: on the one hand a theory as to the nature of the world, on the other an "
        "ethical or political doctrine as to the best way of living."
    )
    idx = json.loads(idx_path.read_text(encoding="utf-8"))
    assert idx["paragraphs"][0]["content_locator"] == content_locator(paragraph)

    allow_list = tmp_path / "pd-allow-list.yaml"
    allow_list.write_text(
        "allowed:\n"
        "  - source_id: problems\n"
        "    title: \"The Problems of Philosophy\"\n"
        "    url: \"https://www.gutenberg.org/cache/epub/5827/pg5827-images.html\"\n",
        encoding="utf-8",
    )
    assets = Path(__file__).parent.parent / "assets"
    # Re-extracted candidate with a DIFFERENT line_hint (so only the locator key can catch
    # it) but the identical paragraph text.
    candidate = {
        "candidate_id": "problems-900",
        "source_id": "problems",
        "source_url": "u",
        "line_hint": 99999,
        "content_locator": "Philosophy, throughout its history,",
        "paragraph_text": paragraph,
        "rhetorical_move_tag": "domain_contrast",
        "calibration_lesson": "splits philosophy into two domains.",
    }
    outcome = run_sentinel(
        candidate=candidate,
        source_path=SOURCE_CACHE / "problems_subset.html",
        allow_list_path=allow_list,
        vocabulary_path=assets / "vocabulary.json",
        generic_phrases_path=assets / "generic-phrases.yaml",
        existing_index_path=idx_path,
        batch_seen_locators=set(),
    )
    assert outcome.status == "reject"
    assert outcome.reason == "duplicate"
