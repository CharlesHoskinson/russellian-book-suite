from scripts.extract import markdown_to_paragraphs, html_to_markdown, DEFAULT_MIN_WORDS


def test_default_min_words():
    assert DEFAULT_MIN_WORDS == 30


def test_keeps_substantial_prose_skips_structure():
    long_a = " ".join(["alpha"] * 35)
    long_b = " ".join(["beta"] * 40)
    md = (
        "# Heading\n\n"
        "Short sentence.\n\n"
        f"{long_a}\n\n"
        "- a list item that is quite long indeed but is still a list item and not prose here yes truly\n\n"
        "> a block quote that is also long enough to pass the word count but remains a quote not a paragraph\n\n"
        f"{long_b}"
    )
    assert markdown_to_paragraphs(md) == [long_a, long_b]


def test_min_words_boundary():
    p29 = " ".join(["w"] * 29)
    p30 = " ".join(["w"] * 30)
    assert markdown_to_paragraphs(f"{p29}\n\n{p30}") == [p30]


def test_collapses_internal_whitespace():
    block = "one   two\nthree " + " ".join(["w"] * 30)
    out = markdown_to_paragraphs(block)
    assert out and "  " not in out[0] and "\n" not in out[0]


def test_html_to_markdown_extracts_body_text():
    sentence = "The snail moves slowly across the wet stone in search of food and does not hurry. "
    body = "".join(f"<p>{sentence * 3}</p>" for _ in range(4))
    html = f"<html><head><title>Snails</title></head><body><article>{body}</article></body></html>"
    md = html_to_markdown(html)
    assert "snail moves slowly" in md.lower()
