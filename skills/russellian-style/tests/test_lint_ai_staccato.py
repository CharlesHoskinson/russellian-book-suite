"""lint_ai_staccato: cross-paragraph staccato detection."""
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "ai_staccato"


def test_staccato_paragraph_run_fires():
    from scripts.lint_ai_staccato import lint_ai_staccato
    findings = lint_ai_staccato(FIXTURES / "staccato_run.md")
    runs = [f for f in findings if f["rule"] == "staccato-paragraph-run"]
    assert runs, "expected staccato-paragraph-run to fire"
    f = runs[0]
    assert f["tier"] == "important"
    assert f["severity"] == "advisory"
    assert f["run_length"] >= 3


def test_staccato_paragraph_run_silent_on_varied_prose():
    from scripts.lint_ai_staccato import lint_ai_staccato
    findings = lint_ai_staccato(FIXTURES / "staccato_run_clean.md")
    runs = [f for f in findings if f["rule"] == "staccato-paragraph-run"]
    assert runs == []


def test_negation_affirmation_template_fires():
    from scripts.lint_ai_staccato import lint_ai_staccato
    findings = lint_ai_staccato(FIXTURES / "negation_affirmation.md")
    hits = [f for f in findings if f["rule"] == "negation-affirmation-template"]
    assert hits, "expected negation-affirmation-template to fire"
    assert hits[0]["match_count"] >= 2


def test_negation_affirmation_template_silent_on_clean():
    from scripts.lint_ai_staccato import lint_ai_staccato
    findings = lint_ai_staccato(FIXTURES / "negation_affirmation_clean.md")
    hits = [f for f in findings if f["rule"] == "negation-affirmation-template"]
    assert hits == []


def test_this_is_conclusion_overuse_fires():
    from scripts.lint_ai_staccato import lint_ai_staccato
    findings = lint_ai_staccato(FIXTURES / "this_is_stacking.md")
    hits = [f for f in findings if f["rule"] == "this-is-conclusion-overuse"]
    assert hits, "expected this-is-conclusion-overuse to fire"
    assert hits[0]["match_count"] >= 3


def test_this_is_conclusion_overuse_silent_on_clean():
    from scripts.lint_ai_staccato import lint_ai_staccato
    findings = lint_ai_staccato(FIXTURES / "this_is_stacking_clean.md")
    hits = [f for f in findings if f["rule"] == "this-is-conclusion-overuse"]
    assert hits == []


def test_abstract_subject_run_fires():
    from scripts.lint_ai_staccato import lint_ai_staccato
    findings = lint_ai_staccato(FIXTURES / "abstract_subject_run.md")
    hits = [f for f in findings if f["rule"] == "abstract-subject-run"]
    assert hits, "expected abstract-subject-run to fire"
    assert hits[0]["subject"] in {"system", "protocol", "ledger"}
    assert hits[0]["run_length"] >= 4


def test_abstract_subject_run_silent_on_varied_subjects():
    from scripts.lint_ai_staccato import lint_ai_staccato
    findings = lint_ai_staccato(FIXTURES / "abstract_subject_run_clean.md")
    hits = [f for f in findings if f["rule"] == "abstract-subject-run"]
    assert hits == []


def test_abstract_subject_run_spans_paragraph_break(tmp_path):
    # A same-subject run that crosses a blank line must be detected; the old
    # per-paragraph reset would split it into two short sub-runs and miss it.
    from scripts.lint_ai_staccato import lint_ai_staccato
    text = (
        "The system records claims as data. The system projects them onto a graph.\n\n"
        "The system validates the graph. The system blocks the release on failure.\n"
    )
    p = tmp_path / "draft.md"
    p.write_text(text, encoding="utf-8")
    findings = lint_ai_staccato(p)
    hits = [f for f in findings if f["rule"] == "abstract-subject-run"]
    assert hits, findings
    assert hits[0]["subject"] == "system"
    assert hits[0]["run_length"] >= 4


def test_abstract_subject_run_reports_run_start_line(tmp_path):
    # The run begins on source line 5, after two unrelated lead-in lines. The
    # reported line must be where the run started, not the paragraph's line 3.
    from scripts.lint_ai_staccato import lint_ai_staccato
    text = (
        "# Heading\n"
        "\n"
        "A reader opens the chapter and skims.\n"
        "The author replies to the reader directly.\n"
        "The system records claims. The system projects them. "
        "The system validates them. The system blocks the release.\n"
    )
    p = tmp_path / "draft.md"
    p.write_text(text, encoding="utf-8")
    findings = lint_ai_staccato(p)
    hits = [f for f in findings if f["rule"] == "abstract-subject-run"]
    assert hits, findings
    assert hits[0]["line"] == 5, hits[0]


# --- antithesis-cadence rules (added with the negation-tic guard) ---

def _run(tmp_path, body):
    from scripts.lint_ai_staccato import lint_ai_staccato
    p = tmp_path / "draft.md"
    p.write_text(body, encoding="utf-8")
    return lint_ai_staccato(p)


def test_antithesis_closer_overuse_fires(tmp_path):
    body = "\n\n".join([
        "# T",
        "A long opening paragraph that simply states a fact plainly and ends on a plain statement of that fact.",
        "The structure works in one way and matters in another, and the result is layered rather than single.",
        "The first reading describes the thing, and the conclusion is not a setting but constitutional material.",
        "It defeats the obvious attack, and the real danger is not the key but the hijacked intention.",
    ])
    findings = _run(tmp_path, body)
    closer = [f for f in findings if f["rule"] == "antithesis-closer-overuse"]
    assert closer and closer[0]["match_count"] >= 3


def test_antithesis_closer_below_threshold_clean(tmp_path):
    body = "\n\n".join([
        "# T",
        "An ordinary paragraph that closes on a consequence the reader can act on.",
        "Another paragraph whose final sentence is not a contrast but a plain claim about the world.",
        "A third paragraph ending on a concrete example rather than a turn, which is one antithesis only.",
    ])
    findings = _run(tmp_path, body)
    assert not [f for f in findings if f["rule"] == "antithesis-closer-overuse"]


def test_repeated_antithesis_phrase_fires(tmp_path):
    body = "\n\n".join([
        "# T",
        "The airgap is necessary and not sufficient, which is the point of the whole design.",
        "Some intervening prose that develops the argument without any contrast at all here.",
        "Pressed again, the rule is necessary and not sufficient, and that bears repeating poorly.",
    ])
    findings = _run(tmp_path, body)
    rep = [f for f in findings if f["rule"] == "repeated-antithesis-phrase"]
    assert rep and any("sufficient" in f["phrase"] for f in rep)


def test_repeated_antithesis_ignores_footnotes(tmp_path):
    # Footnote definitions legitimately repeat "cited ... not ..." provenance boilerplate.
    body = "\n\n".join([
        "# T",
        "A clean body paragraph with no repeated contrast phrasing of any kind here.",
        "[^a]: Source `1`. A primary preprint, cited as a design and not a deployed system.",
        "[^b]: Source `2`. A primary preprint, cited as a design and not a deployed system.",
    ])
    findings = _run(tmp_path, body)
    assert not [f for f in findings if f["rule"] == "repeated-antithesis-phrase"]


def test_repeated_antithesis_ignores_function_word_repeats(tmp_path):
    # "it is not the" has no content word (>=6 chars); must not flag.
    body = "\n\n".join([
        "# T",
        "He said it is not the case, plainly, in the first paragraph of the chapter.",
        "She replied it is not the case, again, much later in the same chapter here.",
    ])
    findings = _run(tmp_path, body)
    assert not [f for f in findings if f["rule"] == "repeated-antithesis-phrase"]
