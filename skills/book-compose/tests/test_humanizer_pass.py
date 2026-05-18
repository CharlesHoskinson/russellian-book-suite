
from scripts.humanizer_pass import assess_draft


def test_clean_draft_has_zero_fingerprints(tmp_path):
    text = "# Sample\n\nThe script provisions the server. Logs persist to disk."
    f = tmp_path / "clean.md"; f.write_text(text, encoding="utf-8")
    r = assess_draft(f)
    assert r.total_fingerprints == 0


def test_ai_vocabulary_caught(tmp_path):
    text = "# Sample\n\nThis comprehensive solution leverages a robust framework to delve into the data."
    f = tmp_path / "ai.md"; f.write_text(text, encoding="utf-8")
    r = assess_draft(f)
    assert r.ai_vocab_count >= 4


def test_filler_caught(tmp_path):
    text = "# Sample\n\nWe configure the server in order to provision it. Due to the fact that the daemon runs."
    f = tmp_path / "filler.md"; f.write_text(text, encoding="utf-8")
    r = assess_draft(f)
    assert r.filler_count >= 2


def test_em_dashes_counted_but_not_gated(tmp_path):
    text = "# Sample\n\nThe pipeline — an end-to-end compiler — produces output."
    f = tmp_path / "em.md"; f.write_text(text, encoding="utf-8")
    r = assess_draft(f)
    assert r.em_dash_count == 2
    # em_dashes don't count toward total_fingerprints
    assert r.total_fingerprints == 0
