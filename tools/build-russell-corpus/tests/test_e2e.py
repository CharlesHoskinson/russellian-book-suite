import json
import shutil
from pathlib import Path

from scripts.extract_candidates import extract_candidates
from scripts.sentinel import run_sentinel_batch
from scripts.cross_check import run_cross_check_batch
from scripts.audit_sample import sample_audit, evaluate_audit_decisions
from scripts.append_to_index import append_verified_to_index, regenerate_corpus_map


FIXTURES = Path(__file__).parent / "fixtures"
SOURCE_CACHE = FIXTURES / "source_cache"
ASSETS = Path(__file__).parent.parent / "assets"


def _stub_extract_llm(prompt: str) -> str:
    return json.dumps({
        "candidate_id": "problems-051",
        "source_id": "problems",
        "source_url": "https://www.gutenberg.org/cache/epub/5827/pg5827-images.html",
        "line_hint": 2,
        "content_locator": "Philosophy, throughout its history,",
        "paragraph_text": "Philosophy, throughout its history, has consisted of two parts inharmoniously blended: on the one hand a theory as to the nature of the world, on the other an ethical or political doctrine as to the best way of living.",
        "rhetorical_move_tag": "domain_contrast",
        "calibration_lesson": "Russell opens by splitting philosophy into two domains the chapter will pull apart.",
    })


def _stub_cross_check_llm(prompt: str) -> str:
    return json.dumps({
        "top1_tag": "domain_contrast",
        "top3_tags": ["domain_contrast", "antithesis", "diagnosis"],
        "is_quotation": False,
        "lesson_specific_to_paragraph": True,
        "lesson_specificity_evidence": "names the exact two domains"
    })


def test_e2e_one_candidate_lands_in_index(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    index_copy = tmp_path / "index.json"
    shutil.copy(FIXTURES / "existing_index_sample.json", index_copy)
    # Patch allow-list with the fixture URL
    allow_list = tmp_path / "pd-allow-list.yaml"
    allow_list.write_text(
        "allowed:\n"
        "  - source_id: problems\n"
        "    title: \"The Problems of Philosophy\"\n"
        "    url: \"https://www.gutenberg.org/cache/epub/5827/pg5827-images.html\"\n",
        encoding="utf-8",
    )

    # Stage 1 — extract
    candidates = run_dir / "candidates.jsonl"
    extract_candidates(
        source_path=SOURCE_CACHE / "problems_subset.html",
        source_id="problems",
        source_url="https://www.gutenberg.org/cache/epub/5827/pg5827-images.html",
        vocabulary_path=ASSETS / "vocabulary.json",
        prompt_path=ASSETS / "extractor-prompt.md",
        out_path=candidates,
        n=1,
        llm_call=_stub_extract_llm,
    )
    # Stage 2 — sentinel
    run_sentinel_batch(
        candidates_path=candidates,
        source_cache_dir=SOURCE_CACHE,
        allow_list_path=allow_list,
        vocabulary_path=ASSETS / "vocabulary.json",
        generic_phrases_path=ASSETS / "generic-phrases.yaml",
        existing_index_path=index_copy,
        run_dir=run_dir,
    )
    assert (run_dir / "passed-sentinel.jsonl").exists()

    # Stage 3 — cross-check
    run_cross_check_batch(
        passed_sentinel_path=run_dir / "passed-sentinel.jsonl",
        rejected_path=run_dir / "rejected.jsonl",
        verified_path=run_dir / "verified.jsonl",
        vocabulary_path=ASSETS / "vocabulary.json",
        llm_call=_stub_cross_check_llm,
    )
    assert (run_dir / "verified.jsonl").exists()

    # Stage 4 — audit
    sample_audit(verified_path=run_dir / "verified.jsonl", out_path=run_dir / "audit" / "sample.md")
    decision = evaluate_audit_decisions(["accept"], halt_threshold=0.10)
    assert decision.action == "proceed"

    # Stage 5 — append
    corpus_map = tmp_path / "russell-corpus-map.md"
    append_verified_to_index(verified_path=run_dir / "verified.jsonl", index_path=index_copy)
    regenerate_corpus_map(index_path=index_copy, out_path=corpus_map)

    idx = json.loads(index_copy.read_text())
    ids = [e["id"] for e in idx["paragraphs"]]
    assert "problems-051" in ids
    assert "problems-051" in corpus_map.read_text(encoding="utf-8")
