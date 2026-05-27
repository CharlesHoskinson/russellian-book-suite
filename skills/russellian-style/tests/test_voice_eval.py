"""Cites REQ-VEVAL-001, REQ-VEVAL-002, REQ-VEVAL-008."""
import pytest
pytestmark = pytest.mark.windows_canary
from scripts.voice_eval import build_generation_prompt, generate_paragraphs, DEFAULT_N


def test_default_paragraph_count_is_30():
    assert DEFAULT_N == 30

def test_prompt_embeds_contract_topic_and_count():
    p = build_generation_prompt("the history of zero", "polemic", 12)
    assert "the history of zero" in p
    assert "12" in p
    assert "# Calibration and planning" in p
    assert "verdict" in p.lower() or "antithesis" in p.lower()

def test_generate_paragraphs_calls_llm_with_prompt_and_returns_output():
    captured = {}
    def fake_llm(prompt):
        captured["prompt"] = prompt
        return "GENERATED PROSE"
    out = generate_paragraphs("topic X", mode="technical-exposition", n=5, llm_call=fake_llm)
    assert out == "GENERATED PROSE"
    assert "topic X" in captured["prompt"]
    assert "5" in captured["prompt"]

def test_generate_paragraphs_rejects_unknown_mode():
    with pytest.raises(ValueError):
        generate_paragraphs("t", mode="nope", n=5, llm_call=lambda p: "")

def test_evaluate_reports_delta_and_linters():
    from scripts.voice_eval import evaluate
    text = "The nineteenth century discovered pure mathematics. " * 80
    rep = evaluate(text)
    g = rep["generated"]
    assert g["russell_delta"]["metric"] == "russell-burrows-delta"
    assert "verdict" in g["russell_delta"]
    assert g["n_words"] > 0
    assert "hedges" in g["linters"] and "passive_voice" in g["linters"]
    assert set(g["linters"]["hedges"]) == {"count", "per_1000"}
    assert rep["baseline"] is None

def test_evaluate_with_baseline_reports_side_by_side():
    from scripts.voice_eval import evaluate
    gen = "The argument proceeds by cases. " * 80
    base = "Philosophy is to be studied for the questions themselves. " * 80
    rep = evaluate(gen, russell_baseline_text=base)
    assert rep["baseline"] is not None
    assert rep["baseline"]["russell_delta"]["metric"] == "russell-burrows-delta"

def test_run_orchestrates_generation_and_eval():
    from scripts.voice_eval import run
    rep = run("the calculus", mode="technical-exposition", n=4,
              llm_call=lambda prompt: "The calculus was invented twice. " * 80)
    assert rep["meta"]["topic"] == "the calculus"
    assert rep["meta"]["n_requested"] == 4
    assert rep["generated_text"].startswith("The calculus")
    assert rep["generated"]["russell_delta"]["metric"] == "russell-burrows-delta"

def test_write_report_emits_paragraphs_and_table(tmp_path):
    from scripts.voice_eval import run, write_report
    rep = run("x", mode="polemic", n=3, llm_call=lambda p: "An argument with a turn. " * 80)
    out = tmp_path / "report.md"
    write_report(rep, out)
    md = out.read_text(encoding="utf-8")
    assert "russell-burrows-delta" in md
    assert "An argument with a turn." in md
    assert "| linter |" in md
