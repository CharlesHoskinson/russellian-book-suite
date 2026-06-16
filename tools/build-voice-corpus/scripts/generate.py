"""Generate voice text from the Hoskinson corpus + triadic-voice guide via an injected llm_call.

The pipeline builds the corpus; this module consumes it to produce prose. Network/LLM access
is an injected `llm_call` (wire the real one with scripts.adapters.make_anthropic_llm_call).
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Callable

LlmCall = Callable[[str], str]
MODES = ("hoskinson", "triadic")

_REPO = Path(__file__).resolve().parents[3]
_CORPUS = _REPO / "skills" / "russellian-style" / "assets" / "hoskinson-corpus" / "index.json"
_GUIDE = _REPO / "skills" / "russellian-style" / "references" / "triadic-voice-guide.md"


def load_exemplars(corpus_path: Path = _CORPUS) -> list[dict[str, Any]]:
    return json.loads(Path(corpus_path).read_text(encoding="utf-8"))["paragraphs"]


def select_exemplars(exemplars: list[dict[str, Any]], *, n: int, seed: int) -> list[dict[str, Any]]:
    """Deterministic sample of up to n exemplars (stable for a given seed)."""
    pool = sorted(exemplars, key=lambda e: e["id"])
    rng = random.Random(seed)
    rng.shuffle(pool)
    return pool[:n]


def _exemplar_block(exemplars: list[dict[str, Any]]) -> str:
    lines = []
    for e in exemplars:
        tags = ", ".join(e.get("tags", []))
        text = e["text"].strip()
        if len(text) > 320:
            text = text[:320].rstrip() + "..."
        lines.append(f'- ({tags}) {e["rhetorical_move"]}: "{text}"')
    return "\n".join(lines)


def build_generation_prompt(topic: str, *, mode: str, exemplars: list[dict[str, Any]], guide: str) -> str:
    if mode not in MODES:
        raise ValueError(f"unknown mode {mode!r}; expected one of {MODES}")
    block = _exemplar_block(exemplars)
    if mode == "hoskinson":
        return (
            "Write a single passage of 150-220 words in the spoken voice of Charles Hoskinson, "
            "founder of Cardano/IOG, on the topic below. He speaks in unscripted whiteboard videos "
            "and AMAs.\n\n"
            "Ground the voice in the real exemplars below - his own transcribed words, each labeled "
            "with the rhetorical move it performs. Reproduce his actual moves and cadence: a warm "
            "signature open when natural; candor and the occasional combative aside at critics; "
            "'the thing people miss is...' framing; framing a critique or design choice as a "
            "systems-design tradeoff; direct address and rhetorical questions; the 'walk before you "
            "run' incremental-discipline maxim; forward momentum.\n\n"
            "Use at most one overt catchphrase per passage (a signature greeting, 'the thing people "
            "miss', 'walk before you run', 'do the work', a blunt 'No.'); earn it with topic-specific "
            "substance first. Omit needless words and prefer concrete nouns - a mechanism, an actor, a "
            "failure mode - over generic abstractions; no decorative triples; never restate the "
            "previous sentence.\n\n"
            "Do NOT invent generic crypto-founder filler (no 'revolutionary', no 'game-changer', no "
            "vague 'airplanes and nuclear reactors'). Every distinctive turn should resemble a move "
            "shown below. No AI-writing tells (no 'key insight', no rule-of-three padding, no em-dash "
            "overuse). Output ONLY the passage.\n\n"
            f"TOPIC: {topic}\n\n"
            f"EXEMPLARS OF HIS VOICE:\n{block}\n"
        )
    return (
        "Write a single passage of 150-220 words that fuses three writing voices on the topic "
        "below, following the triadic-voice guide.\n\n"
        f"THE GUIDE:\n{guide}\n\n"
        "Open with HOSKINSON: state the stakes plainly with candor, direct address, and momentum. "
        "Vary the opening move across generations - rotate among direct stakes, a hostile objection, "
        "a concrete scene, a flat definition, and a contradiction - and do not reuse the previous "
        "passage's opening. Use at most one overt Hoskinson catchphrase per passage, earned with "
        "topic-specific substance first.\n"
        "Develop with FEYNMAN: build the intuition from scratch and show WHY before any formalism, "
        "with warmth. Pick ONE development method and vary it across a batch - an analogy, a worked "
        "example, a counterexample, a failure case, a toy model, or a step-by-step derivation - and "
        "avoid leaning on the cue words 'imagine', 'picture', 'think of', or 'consider' every time.\n"
        "Close with RUSSELL: compress to one exact, declarative, unhedged sentence. Rotate the close "
        "type across a batch - an exact definition, a boundary condition, a causal claim, a necessary "
        "condition, a consequence, or an exception - rather than ending every passage on the same "
        "aphorism.\n"
        "Throughout, hold the discipline floor and Elements-of-Style economy: active voice, high "
        "signal density, omit needless words, prefer concrete nouns (a mechanism, an actor, a failure "
        "mode) over generic abstractions, no decorative triples, and never restate the previous "
        "sentence.\n\n"
        "Ground the Hoskinson register in these real exemplars of his voice (the Feynman corpus is "
        "pointers-only by copyright, so draw Feynman's contribution from the guide, not quoted text):\n"
        f"{block}\n\n"
        "No AI-writing tells. Output ONLY the passage.\n\n"
        f"TOPIC: {topic}\n"
    )


def generate(topic: str, *, mode: str, llm_call: LlmCall,
             corpus_path: Path = _CORPUS, guide_path: Path = _GUIDE,
             n_exemplars: int = 8, seed: int = 0) -> str:
    """Generate a voice passage on `topic`. mode in MODES. Returns the model's text."""
    if mode not in MODES:
        raise ValueError(f"unknown mode {mode!r}; expected one of {MODES}")
    exemplars = select_exemplars(load_exemplars(corpus_path), n=n_exemplars, seed=seed)
    guide = Path(guide_path).read_text(encoding="utf-8")
    prompt = build_generation_prompt(topic, mode=mode, exemplars=exemplars, guide=guide)
    return llm_call(prompt).strip()


def main() -> None:
    import argparse

    from scripts.adapters import make_anthropic_llm_call

    parser = argparse.ArgumentParser(description="Generate Hoskinson / triadic voice text from the corpus")
    parser.add_argument("--topic", required=True)
    parser.add_argument("--mode", choices=MODES, default="triadic")
    parser.add_argument("--n-exemplars", type=int, default=8)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--model", default=None, help="override the model (default claude-opus-4-8)")
    args = parser.parse_args()

    llm_call = make_anthropic_llm_call(model=args.model)
    print(generate(args.topic, mode=args.mode, llm_call=llm_call,
                   n_exemplars=args.n_exemplars, seed=args.seed))


if __name__ == "__main__":
    main()
