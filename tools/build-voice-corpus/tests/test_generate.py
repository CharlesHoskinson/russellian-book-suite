from scripts.generate import (
    load_exemplars, select_exemplars, build_generation_prompt, generate, MODES,
)
import pytest


def test_load_exemplars_reads_real_corpus():
    ex = load_exemplars()
    assert len(ex) >= 50
    assert all("text" in e and "rhetorical_move" in e for e in ex)


def test_select_exemplars_deterministic():
    ex = load_exemplars()
    a = [e["id"] for e in select_exemplars(ex, n=6, seed=3)]
    b = [e["id"] for e in select_exemplars(ex, n=6, seed=3)]
    assert a == b and len(a) == 6


def test_build_prompt_hoskinson_grounds_in_exemplars():
    ex = select_exemplars(load_exemplars(), n=4, seed=1)
    p = build_generation_prompt("formal verification", mode="hoskinson", exemplars=ex, guide="G")
    assert "formal verification" in p
    assert "Charles Hoskinson" in p
    # at least one exemplar's text fragment appears in the prompt
    assert any(e["text"][:30] in p for e in ex)


def test_build_prompt_triadic_includes_three_voices_and_guide():
    ex = select_exemplars(load_exemplars(), n=4, seed=1)
    p = build_generation_prompt("x", mode="triadic", exemplars=ex, guide="GUIDETEXT")
    assert "HOSKINSON" in p and "FEYNMAN" in p and "RUSSELL" in p
    assert "GUIDETEXT" in p


def test_build_prompt_rejects_bad_mode():
    with pytest.raises(ValueError):
        build_generation_prompt("x", mode="bogus", exemplars=[], guide="")


def test_generate_uses_injected_llm():
    captured = {}
    def fake_llm(prompt: str) -> str:
        captured["prompt"] = prompt
        return "  GENERATED PASSAGE  "
    out = generate("zk proofs", mode="hoskinson", llm_call=fake_llm, n_exemplars=3, seed=2)
    assert out == "GENERATED PASSAGE"
    assert "zk proofs" in captured["prompt"]


def test_generate_rejects_bad_mode():
    with pytest.raises(ValueError):
        generate("x", mode="bogus", llm_call=lambda p: "")


def test_triadic_prompt_has_variation_and_economy():
    from scripts.generate import build_generation_prompt, select_exemplars, load_exemplars
    ex = select_exemplars(load_exemplars(), n=4, seed=1)
    p = build_generation_prompt("x", mode="triadic", exemplars=ex, guide="G")
    # Feynman is now a method menu, not a single analogy slot
    assert "worked example" in p and "counterexample" in p
    # opening + closing rotation present
    assert "Vary the opening move" in p
    assert "Rotate the close type" in p
    # Elements-of-Style economy pressure present
    assert "omit needless words" in p.lower()


def test_hoskinson_prompt_has_tic_budget_and_economy():
    from scripts.generate import build_generation_prompt, select_exemplars, load_exemplars
    ex = select_exemplars(load_exemplars(), n=3, seed=1)
    p = build_generation_prompt("x", mode="hoskinson", exemplars=ex, guide="G")
    assert "at most one overt catchphrase" in p
    assert "omit needless words" in p.lower()
