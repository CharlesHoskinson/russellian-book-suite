from scripts.dispatch_review import render_prompt, parse_review_report, ReviewResult
from scripts.persona_loader import Persona


SAMPLE_PERSONA = Persona(
    persona_id="gottlieb",
    display_name="Robert Gottlieb",
    role="legendary editor",
    body_md="## Lens\nCadence and ruthless cuts.\n\n## Severity rubric\nFlag listicle abstracts as critical.",
)


def test_render_prompt_inlines_persona_and_draft(tmp_path):
    draft = tmp_path / "draft.md"
    draft.write_text("# Sample\n\nThe manual rests on six premises:\n", encoding="utf-8")
    chapter_meta = {
        "chapter_id": "ch-04",
        "chapter_title": "Economy",
        "chapter_purpose": "Explain GDP composition",
        "audience": "senior-engineer",
    }
    output = tmp_path / "out.md"
    prompt = render_prompt(SAMPLE_PERSONA, draft, chapter_meta, output)
    assert "Robert Gottlieb" in prompt
    assert "ruthless cuts" in prompt
    assert "rests on six premises" in prompt
    assert "ch-04" in prompt
    assert str(output) in prompt


SAMPLE_REVIEW = """---
persona: gottlieb
chapter_id: ch-04
verdict: NEEDS_WORK
critical_count: 2
important_count: 5
minor_count: 8
reviewed_at: 2026-05-10T12:00:00+00:00
---

## Verdict
NEEDS_WORK

## Critical findings (gating)
1. **Line 14:** "rests on six premises" - cut.
2. **Section 3:** mechanical enumeration.

## Important findings
- Item one.

## Minor findings
- Polish.

## Notes on voice and cadence
The chapter loses its music in section 3.
"""


def test_parse_review_report_extracts_metadata(tmp_path):
    f = tmp_path / "review.md"
    f.write_text(SAMPLE_REVIEW, encoding="utf-8")
    result = parse_review_report(f)
    assert isinstance(result, ReviewResult)
    assert result.persona_id == "gottlieb"
    assert result.chapter_id == "ch-04"
    assert result.verdict == "NEEDS_WORK"
    assert len(result.critical) == 2
    assert len(result.important) == 1
    assert len(result.minor) == 1
    assert "music" in result.voice_notes
