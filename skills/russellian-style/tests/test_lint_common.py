from pathlib import Path
from scripts.lint_common import load_markdown, iter_sentences, load_rules


def test_load_markdown_returns_text():
    path = Path("tests/fixtures/compliant_sample.md")
    text = load_markdown(path)
    assert "## " in text or "# " in text


def test_iter_sentences_yields_position_tagged_sentences():
    text = "First sentence. Second sentence here.\n\nThird in new paragraph."
    sentences = list(iter_sentences(text))
    assert len(sentences) == 3
    s0 = sentences[0]
    assert s0.text == "First sentence."
    assert s0.line == 1
    assert s0.col == 1


def test_iter_sentences_preserves_line_numbers_across_paragraphs():
    text = "Line one.\n\n\nLine four."
    sentences = list(iter_sentences(text))
    assert sentences[1].line == 4


def test_load_rules_returns_dict():
    rules = load_rules()
    assert "hedge_terms" in rules
    assert "modifier_budget_ratio" in rules
    assert isinstance(rules["hedge_terms"], list)


def test_iter_sentences_skips_headings():
    text = "# Heading sentence.\n\nReal sentence."
    sentences = list(iter_sentences(text))
    assert len(sentences) == 1
    assert sentences[0].text == "Real sentence."


def test_iter_sentences_skips_fenced_code_blocks():
    text = "```\ncode sentence.\n```\n\nReal sentence."
    sentences = list(iter_sentences(text))
    assert len(sentences) == 1
    assert sentences[0].text == "Real sentence."


def test_iter_sentences_skips_indented_code_blocks():
    text = "    indented code sentence.\n\nReal sentence."
    sentences = list(iter_sentences(text))
    assert len(sentences) == 1
    assert sentences[0].text == "Real sentence."


def test_iter_sentences_skips_list_markers():
    text = "- list item sentence.\n\nReal sentence."
    sentences = list(iter_sentences(text))
    assert len(sentences) == 1
    assert sentences[0].text == "Real sentence."


def test_iter_sentences_handles_empty_text():
    assert list(iter_sentences("")) == []


def test_iter_sentences_handles_whitespace_only():
    assert list(iter_sentences("   \n\n  \n")) == []


def test_sentence_splitter_does_not_fragment_on_abbreviations():
    text = "We arrived in St. George's at noon. The town is old."
    sentences = list(iter_sentences(text))
    assert len(sentences) == 2
    assert "St. George's" in sentences[0].text


def test_sentence_splitter_does_not_fragment_on_decimals():
    text = "Growth was 4.5 percent in 2024. Inflation eased to 2.0 percent."
    sentences = list(iter_sentences(text))
    assert len(sentences) == 2


def test_sentence_splitter_does_not_fragment_on_initials():
    text = "L. F. Wade International Airport opened in 1948. The runway is long."
    sentences = list(iter_sentences(text))
    assert len(sentences) == 2
