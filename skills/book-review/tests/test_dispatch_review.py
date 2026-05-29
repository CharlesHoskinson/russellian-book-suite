import pytest

pytestmark = pytest.mark.windows_canary

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


DOUBLE_DIGIT_REVIEW = """---
persona: gottlieb
chapter_id: ch-04
verdict: NEEDS_WORK
critical_count: 12
important_count: 0
minor_count: 0
reviewed_at: 2026-05-10T12:00:00+00:00
---

## Critical findings (gating)
1. First.
2. Second.
3. Third.
4. Fourth.
5. Fifth.
6. Sixth.
7. Seventh.
8. Eighth.
9. Ninth.
10. Tenth.
11. Eleventh.
12. Twelfth.
"""


BAD_VERDICT_REVIEW = """---
persona: gottlieb
chapter_id: ch-04
verdict: TOTALLY_FINE
critical_count: 0
important_count: 0
minor_count: 0
reviewed_at: 2026-05-10T12:00:00+00:00
---

## Critical findings (gating)
(none)
"""

BAD_CHAPTER_ID_REVIEW = """---
persona: gottlieb
chapter_id: Chapter Four!
verdict: APPROVED
critical_count: 0
important_count: 0
minor_count: 0
reviewed_at: 2026-05-10T12:00:00+00:00
---

## Critical findings (gating)
(none)
"""


def test_parse_review_report_rejects_invalid_verdict(tmp_path):
    f = tmp_path / "gottlieb.md"
    f.write_text(BAD_VERDICT_REVIEW, encoding="utf-8")
    with pytest.raises(ValueError):
        parse_review_report(f)


def test_parse_review_report_rejects_bad_chapter_id(tmp_path):
    f = tmp_path / "gottlieb.md"
    f.write_text(BAD_CHAPTER_ID_REVIEW, encoding="utf-8")
    with pytest.raises(ValueError):
        parse_review_report(f)


NO_PERSONA_REVIEW = """---
chapter_id: ch-04
verdict: APPROVED
critical_count: 0
important_count: 0
minor_count: 0
reviewed_at: 2026-05-10T12:00:00+00:00
---

## Critical findings (gating)
(none)
"""


def test_parse_review_report_falls_back_to_filename_stem(tmp_path):
    f = tmp_path / "domain-expert.md"
    f.write_text(NO_PERSONA_REVIEW, encoding="utf-8")
    result = parse_review_report(f)
    assert result.persona_id == "domain-expert"


def test_parse_review_report_keeps_double_digit_findings(tmp_path):
    f = tmp_path / "review.md"
    f.write_text(DOUBLE_DIGIT_REVIEW, encoding="utf-8")
    result = parse_review_report(f)
    assert len(result.critical) == 12
    texts = [x.text for x in result.critical]
    assert "Tenth." in texts
    assert "Twelfth." in texts


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
