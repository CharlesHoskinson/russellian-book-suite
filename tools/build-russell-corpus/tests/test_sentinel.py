import json
from pathlib import Path

from scripts.sentinel import run_sentinel, SentinelOutcome


FIXTURES = Path(__file__).parent / "fixtures"
SOURCE_CACHE = FIXTURES / "source_cache"
CANDIDATES = FIXTURES / "candidates"
EXISTING_INDEX = FIXTURES / "existing_index_sample.json"
ALLOW_LIST = Path(__file__).parent.parent / "assets" / "pd-allow-list.yaml"
VOCABULARY = Path(__file__).parent.parent / "assets" / "vocabulary.json"
GENERIC_PHRASES = Path(__file__).parent.parent / "assets" / "generic-phrases.yaml"


def _patched_allow_list_for_tests(tmp_path: Path) -> Path:
    """Allow-list pointing at the fixture source cache (not the live Gutenberg URL)."""
    out = tmp_path / "pd-allow-list.yaml"
    out.write_text(
        "allowed:\n"
        "  - source_id: problems\n"
        "    title: \"The Problems of Philosophy\"\n"
        "    url: \"https://www.gutenberg.org/cache/epub/5827/pg5827-images.html\"\n",
        encoding="utf-8",
    )
    return out


def test_sentinel_good_candidate_passes(tmp_path: Path) -> None:
    candidate = json.loads((CANDIDATES / "good.json").read_text())
    outcome = run_sentinel(
        candidate=candidate,
        source_path=SOURCE_CACHE / "problems_subset.html",
        allow_list_path=_patched_allow_list_for_tests(tmp_path),
        vocabulary_path=VOCABULARY,
        generic_phrases_path=GENERIC_PHRASES,
        existing_index_path=EXISTING_INDEX,
        batch_seen_locators=set(),
    )
    assert outcome.status == "pass"
    assert outcome.reason is None


def test_sentinel_rejects_hallucinated_paragraph(tmp_path: Path) -> None:
    candidate = json.loads((CANDIDATES / "hallucinated.json").read_text())
    outcome = run_sentinel(
        candidate=candidate,
        source_path=SOURCE_CACHE / "problems_subset.html",
        allow_list_path=_patched_allow_list_for_tests(tmp_path),
        vocabulary_path=VOCABULARY,
        generic_phrases_path=GENERIC_PHRASES,
        existing_index_path=EXISTING_INDEX,
        batch_seen_locators=set(),
    )
    assert outcome.status == "reject"
    assert outcome.reason == "source-mismatch"


def test_sentinel_rejects_source_off_allowlist(tmp_path: Path) -> None:
    candidate = json.loads((CANDIDATES / "not_pd.json").read_text())
    outcome = run_sentinel(
        candidate=candidate,
        source_path=SOURCE_CACHE / "problems_subset.html",
        allow_list_path=_patched_allow_list_for_tests(tmp_path),
        vocabulary_path=VOCABULARY,
        generic_phrases_path=GENERIC_PHRASES,
        existing_index_path=EXISTING_INDEX,
        batch_seen_locators=set(),
    )
    assert outcome.status == "reject"
    assert outcome.reason == "not-pd-allowed"


def test_sentinel_rejects_duplicate_in_batch(tmp_path: Path) -> None:
    candidate = json.loads((CANDIDATES / "duplicate.json").read_text())
    locator = "Philosophy, throughout its history, has consisted of two parts inharmoniously blended: on the one hand a theory as to th"
    outcome = run_sentinel(
        candidate=candidate,
        source_path=SOURCE_CACHE / "problems_subset.html",
        allow_list_path=_patched_allow_list_for_tests(tmp_path),
        vocabulary_path=VOCABULARY,
        generic_phrases_path=GENERIC_PHRASES,
        existing_index_path=EXISTING_INDEX,
        batch_seen_locators={locator},
    )
    assert outcome.status == "reject"
    assert outcome.reason == "duplicate"


def test_sentinel_defers_novel_tag(tmp_path: Path) -> None:
    candidate = json.loads((CANDIDATES / "novel_tag.json").read_text())
    outcome = run_sentinel(
        candidate=candidate,
        source_path=SOURCE_CACHE / "problems_subset.html",
        allow_list_path=_patched_allow_list_for_tests(tmp_path),
        vocabulary_path=VOCABULARY,
        generic_phrases_path=GENERIC_PHRASES,
        existing_index_path=EXISTING_INDEX,
        batch_seen_locators=set(),
    )
    assert outcome.status == "defer"
    assert outcome.reason == "novel-tag"
    assert outcome.evidence["proposed_tag"] == "metaphor_destabilisation"


def test_sentinel_rejects_generic_lesson_via_surface_filter(tmp_path: Path) -> None:
    candidate = json.loads((CANDIDATES / "generic_lesson_surface.json").read_text())
    # Patch generic-phrases for this test only — empty seed in committed file.
    gp = tmp_path / "generic-phrases.yaml"
    gp.write_text("phrases:\n  - \"varies sentence length\"\n", encoding="utf-8")
    outcome = run_sentinel(
        candidate=candidate,
        source_path=SOURCE_CACHE / "problems_subset.html",
        allow_list_path=_patched_allow_list_for_tests(tmp_path),
        vocabulary_path=VOCABULARY,
        generic_phrases_path=gp,
        existing_index_path=EXISTING_INDEX,
        batch_seen_locators=set(),
    )
    assert outcome.status == "reject"
    assert outcome.reason == "generic-lesson-filter"
    assert outcome.evidence["matched_phrase"] == "varies sentence length"
