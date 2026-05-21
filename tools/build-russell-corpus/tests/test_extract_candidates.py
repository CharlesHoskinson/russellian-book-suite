import json
from pathlib import Path

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
