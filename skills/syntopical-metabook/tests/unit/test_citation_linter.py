from scripts.synthesize.citation_linter import lint_paragraph, CitationIssue

def test_paragraph_with_claim_id_passes():
    text = "Finality holds in the long-chain rule [cl-abc-123]."
    assert lint_paragraph(text) == []

def test_paragraph_with_wiki_slug_passes():
    text = "See [[nakamoto-consensus]] for the canonical statement."
    assert lint_paragraph(text) == []

def test_paragraph_with_rule_id_passes():
    text = "By rule-unify-1, the surface forms collapse."
    assert lint_paragraph(text) == []

def test_paragraph_with_no_citation_fails():
    text = "Finality is irreversible."
    issues = lint_paragraph(text)
    assert len(issues) == 1
    assert isinstance(issues[0], CitationIssue)

def test_section_headings_and_table_rows_are_skipped():
    text = "## Heading\n\n| a | b |\n|---|---|\n| 1 | 2 |\n"
    issues = lint_paragraph(text)
    assert issues == []
