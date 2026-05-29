import json
from pathlib import Path

from scripts.sentinel import run_sentinel, run_sentinel_batch, SentinelOutcome


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


def test_sentinel_rejects_duplicate_appended_by_prior_run(tmp_path: Path) -> None:
    """A paragraph already committed to the index by a prior pipeline run (i.e. via
    append_to_index, which stores the LLM's short content_locator snippet) must be
    rejected as a duplicate on re-extraction. The dedup key must be derived
    consistently on both sides — finding sentinel-cross-index-dedup-broken."""
    from scripts.append_to_index import _project_candidate_to_index_entry

    candidate = json.loads((CANDIDATES / "good.json").read_text())
    # Simulate the index entry exactly as a prior run would have written it.
    prior_entry = _project_candidate_to_index_entry({
        **candidate,
        "candidate_id": "problems-001",
    })
    index = tmp_path / "index.json"
    index.write_text(json.dumps({
        "version": "0.1.0",
        "paragraph_count": 1,
        "sources": {"problems": {"title": "x", "url": "u", "copyright_status": "public_domain_us", "mode": ["m"]}},
        "paragraphs": [prior_entry],
    }), encoding="utf-8")
    outcome = run_sentinel(
        candidate=candidate,
        source_path=SOURCE_CACHE / "problems_subset.html",
        allow_list_path=_patched_allow_list_for_tests(tmp_path),
        vocabulary_path=VOCABULARY,
        generic_phrases_path=GENERIC_PHRASES,
        existing_index_path=index,
        batch_seen_locators=set(),
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


def test_run_sentinel_batch_routes_outcomes_to_three_ledgers(tmp_path: Path) -> None:
    # Build a candidates.jsonl with one good, one hallucinated, one novel-tag.
    cands = tmp_path / "candidates.jsonl"
    rows = [
        json.loads((CANDIDATES / "good.json").read_text()),
        json.loads((CANDIDATES / "hallucinated.json").read_text()),
        json.loads((CANDIDATES / "novel_tag.json").read_text()),
    ]
    cands.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    run_dir = tmp_path / "run"
    run_sentinel_batch(
        candidates_path=cands,
        source_cache_dir=SOURCE_CACHE,
        allow_list_path=_patched_allow_list_for_tests(tmp_path),
        vocabulary_path=VOCABULARY,
        generic_phrases_path=GENERIC_PHRASES,
        existing_index_path=EXISTING_INDEX,
        run_dir=run_dir,
    )
    passed = [json.loads(l) for l in (run_dir / "passed-sentinel.jsonl").read_text().splitlines() if l.strip()]
    rejected = [json.loads(l) for l in (run_dir / "rejected.jsonl").read_text().splitlines() if l.strip()]
    pending = [json.loads(l) for l in (run_dir / "pending-tag.jsonl").read_text().splitlines() if l.strip()]
    proposed_tags = [json.loads(l) for l in (run_dir / "proposed-tags.jsonl").read_text().splitlines() if l.strip()]

    assert len(passed) == 1 and passed[0]["candidate_id"] == "problems-051"
    assert len(rejected) == 1 and rejected[0]["reason"] == "source-mismatch"
    assert len(pending) == 1 and pending[0]["candidate_id"] == "problems-053"
    assert len(proposed_tags) == 1 and proposed_tags[0]["tag"] == "metaphor_destabilisation"
