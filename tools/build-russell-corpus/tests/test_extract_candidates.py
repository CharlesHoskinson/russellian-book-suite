import json
from pathlib import Path

import pytest

from scripts.extract_candidates import extract_candidates


FIXTURE_SOURCE = Path(__file__).parent / "fixtures" / "source_cache" / "problems_subset.html"


def _fake_llm_returns_two_candidates(prompt: str) -> str:
    return "\n".join([
        json.dumps({
            "candidate_id": "problems-051",
            "source_id": "problems",
            "source_url": "https://www.gutenberg.org/cache/epub/5827/pg5827-images.html",
            "line_hint": 2,
            "content_locator": "Philosophy, throughout its history,",
            "paragraph_text": "Philosophy, throughout its history, has consisted of two parts inharmoniously blended: on the one hand a theory as to the nature of the world, on the other an ethical or political doctrine as to the best way of living.",
            "rhetorical_move_tag": "domain_contrast",
            "calibration_lesson": "Russell opens by splitting philosophy into two domains that the rest of the chapter will pull apart.",
        }),
        json.dumps({
            "candidate_id": "problems-052",
            "source_id": "problems",
            "source_url": "https://www.gutenberg.org/cache/epub/5827/pg5827-images.html",
            "line_hint": 3,
            "content_locator": "The failure to separate these two",
            "paragraph_text": "The failure to separate these two with sufficient clarity has been a source of much confused thinking.",
            "rhetorical_move_tag": "diagnosis",
            "calibration_lesson": "A single short sentence indicts the prior confusion before the analysis begins.",
        }),
    ])


def test_extract_candidates_writes_jsonl(tmp_path: Path) -> None:
    out = tmp_path / "candidates.jsonl"
    extract_candidates(
        source_path=FIXTURE_SOURCE,
        source_id="problems",
        source_url="https://www.gutenberg.org/cache/epub/5827/pg5827-images.html",
        vocabulary_path=Path(__file__).parent.parent / "assets" / "vocabulary.json",
        prompt_path=Path(__file__).parent.parent / "assets" / "extractor-prompt.md",
        out_path=out,
        n=2,
        llm_call=_fake_llm_returns_two_candidates,
    )
    rows = [json.loads(line) for line in out.read_text().splitlines() if line.strip()]
    assert len(rows) == 2
    assert rows[0]["candidate_id"] == "problems-051"
    assert rows[1]["rhetorical_move_tag"] == "diagnosis"


def _candidate_obj(cid: str) -> dict:
    return {
        "candidate_id": cid,
        "source_id": "problems",
        "source_url": "u",
        "line_hint": 2,
        "content_locator": "Philosophy, throughout its history,",
        "paragraph_text": "Philosophy, throughout its history, has consisted of two parts.",
        "rhetorical_move_tag": "domain_contrast",
        "calibration_lesson": "Russell splits philosophy into two domains.",
    }


def test_extract_candidates_parses_top_level_json_array(tmp_path: Path) -> None:
    """A pretty-printed top-level JSON array (a common LLM deviation from the JSONL
    contract) must be parsed, not silently dropped. Finding extract-jsonl-only-silent-drop."""
    out = tmp_path / "candidates.jsonl"

    def array_llm(prompt: str) -> str:
        return json.dumps([_candidate_obj("problems-051"), _candidate_obj("problems-052")], indent=2)

    extract_candidates(
        source_path=FIXTURE_SOURCE, source_id="problems", source_url="u",
        vocabulary_path=Path(__file__).parent.parent / "assets" / "vocabulary.json",
        prompt_path=Path(__file__).parent.parent / "assets" / "extractor-prompt.md",
        out_path=out, n=2, llm_call=array_llm,
    )
    rows = [json.loads(l) for l in out.read_text().splitlines() if l.strip()]
    assert [r["candidate_id"] for r in rows] == ["problems-051", "problems-052"]


def test_extract_candidates_raises_when_zero_parsed_from_nonempty_output(tmp_path: Path) -> None:
    """Non-empty LLM output that yields zero candidates (e.g. prose / code-fenced junk)
    must raise rather than silently writing an empty file and deferring to a confusing
    zero-candidate sentinel run. Finding extract-jsonl-only-silent-drop."""
    out = tmp_path / "candidates.jsonl"

    def junk_llm(prompt: str) -> str:
        return "Here are your candidates:\n```\nnot json at all\n```\n"

    with pytest.raises(ValueError, match="0 candidates"):
        extract_candidates(
            source_path=FIXTURE_SOURCE, source_id="problems", source_url="u",
            vocabulary_path=Path(__file__).parent.parent / "assets" / "vocabulary.json",
            prompt_path=Path(__file__).parent.parent / "assets" / "extractor-prompt.md",
            out_path=out, n=2, llm_call=junk_llm,
        )


def test_extract_candidates_allows_empty_output(tmp_path: Path) -> None:
    """Genuinely empty LLM output (the model found nothing) must not raise — only
    non-empty output that parses to zero candidates is an error."""
    out = tmp_path / "candidates.jsonl"
    extract_candidates(
        source_path=FIXTURE_SOURCE, source_id="problems", source_url="u",
        vocabulary_path=Path(__file__).parent.parent / "assets" / "vocabulary.json",
        prompt_path=Path(__file__).parent.parent / "assets" / "extractor-prompt.md",
        out_path=out, n=2, llm_call=lambda prompt: "   \n  \n",
    )
    assert not out.exists() or out.read_text().strip() == ""


def test_extract_candidates_passes_n_and_source_into_prompt(tmp_path: Path) -> None:
    captured: dict[str, str] = {}

    def capturing_llm(prompt: str) -> str:
        captured["prompt"] = prompt
        return ""

    extract_candidates(
        source_path=FIXTURE_SOURCE,
        source_id="problems",
        source_url="https://www.gutenberg.org/cache/epub/5827/pg5827-images.html",
        vocabulary_path=Path(__file__).parent.parent / "assets" / "vocabulary.json",
        prompt_path=Path(__file__).parent.parent / "assets" / "extractor-prompt.md",
        out_path=tmp_path / "candidates.jsonl",
        n=7,
        llm_call=capturing_llm,
    )
    assert "Philosophy, throughout its history" in captured["prompt"]
    # vocabulary block should be substituted
    assert "{{VOCABULARY}}" not in captured["prompt"]
    assert "{{SOURCE_TEXT}}" not in captured["prompt"]
