"""LLM-judge step: extracts rhetorical-move taxonomy + unsympathetic critique.

The escape from the deterministic-instrument treadmill (REQ-VOICE-022). Single
LLM call per essay, caller-provided dispatcher (mirrors
``skills/review-conductor/scripts/reading_scores.run_reading_council``). The
deterministic linters (chassis_uniformity, humanity_token_closers, etc.) stay as
cheap pre-filters; this judge sits at the top of the stack as a reader-equivalent
that catches the abstraction layer the regex is perpetually one step behind.

This module makes NO live LLM calls. Tests stub the dispatcher. Advisory only;
the judge does not gate.

The judge is NOT auto-wired into ``voice_eval`` — it requires a dispatcher and
the eval is meant to be runnable without one. Audits invoke ``chassis_judge``
directly, alongside ``voice_eval``, the way the prior audit invoked
``reading_scores`` alongside ``voice_eval``.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Callable


_PROMPT_TEMPLATE = """\
You are reading an essay for chassis monotony — the fault where every paragraph
executes the same rhetorical move. A reader catches this when surface shapes
vary but the underlying move repeats (e.g., fact → pivot → aphorism, sixteen
times). Deterministic instruments cannot detect this reliably; you can.

Read the essay below. Then answer in EXACTLY this format, with these headers
and field names, one per line where indicated:

PARAGRAPH_MOVES:
1. <a short noun phrase naming the rhetorical move executed in paragraph 1>
2. <same for paragraph 2>
... (one numbered line per paragraph in the essay)

MOVE_TAXONOMY:
- <each unique move name from above, one per line>

MOST_FREQUENT_MOVE: <the move appearing most often>
MOST_FREQUENT_MOVE_FREQUENCY: <a float between 0.0 and 1.0, the fraction of paragraphs running this move>
SINGLE_MOVE_SUMMARY: <yes or no — can the essay be summarised in a single move-shape?>
UNSYMPATHETIC_CRITIQUE: <one sentence an unsympathetic reader would write about the essay's structural fault>

ESSAY:
{doc_text}
"""


def _build_judge_prompt(doc_text: str) -> str:
    """Pure function. The prompt embeds the document and the response format."""
    return _PROMPT_TEMPLATE.format(doc_text=doc_text)


def _section(response: str, header: str) -> str:
    """Return the lines of the named section, stopping at the next ALL_CAPS header."""
    pattern = re.compile(
        rf"^{re.escape(header)}:\s*\n?(.*?)(?=^[A-Z_]+:|\Z)",
        re.DOTALL | re.MULTILINE,
    )
    m = pattern.search(response)
    return m.group(1).strip() if m else ""


def _scalar(response: str, header: str) -> str:
    """Return the value on the same line as a scalar header (e.g., MOST_FREQUENT_MOVE: foo)."""
    m = re.search(rf"^{re.escape(header)}:\s*(.+)$", response, re.MULTILINE)
    return m.group(1).strip() if m else ""


def _parse_numbered_list(block: str) -> list[str]:
    items: list[str] = []
    for line in block.splitlines():
        m = re.match(r"\s*\d+\.\s+(.*)", line)
        if m:
            items.append(m.group(1).strip())
    return items


def _parse_bulleted_list(block: str) -> list[str]:
    items: list[str] = []
    for line in block.splitlines():
        m = re.match(r"\s*-\s+(.*)", line)
        if m:
            items.append(m.group(1).strip())
    return items


def _parse_judge_response(response: str) -> dict:
    """Pure function. Parses the structured response into the typed dict."""
    paragraph_moves = _parse_numbered_list(_section(response, "PARAGRAPH_MOVES"))
    move_taxonomy = _parse_bulleted_list(_section(response, "MOVE_TAXONOMY"))
    most_frequent = _scalar(response, "MOST_FREQUENT_MOVE")
    freq_raw = _scalar(response, "MOST_FREQUENT_MOVE_FREQUENCY")
    try:
        most_frequent_freq = float(freq_raw) if freq_raw else 0.0
    except ValueError:
        most_frequent_freq = 0.0
    # REQ-VOICE-022: the frequency is a fraction in 0..1. Clamp so a malformed
    # dispatcher value cannot leak out of range or distort the preregistered
    # falsification arithmetic (Condition 1 compares against 0.50).
    most_frequent_freq = max(0.0, min(1.0, most_frequent_freq))
    single_raw = _scalar(response, "SINGLE_MOVE_SUMMARY").lower()
    single_move = single_raw.startswith("y")
    critique = _scalar(response, "UNSYMPATHETIC_CRITIQUE")
    return {
        "paragraph_moves": paragraph_moves,
        "move_taxonomy": move_taxonomy,
        "most_frequent_move": most_frequent,
        "most_frequent_move_frequency": most_frequent_freq,
        "single_move_summary": single_move,
        "unsympathetic_critique": critique,
    }


def chassis_judge(doc_text: str, *, dispatcher: Callable[[str], str]) -> dict:
    """Score an essay for chassis monotony via a single LLM call.

    ``dispatcher`` is a caller-provided ``Callable[[str], str]``. The function
    builds the prompt, passes it to the dispatcher exactly once, parses the
    response, and returns the advisory result dict (REQ-VOICE-022 schema).
    """
    prompt = _build_judge_prompt(doc_text)
    response = dispatcher(prompt)
    parsed = _parse_judge_response(response)
    return {
        "metric": "chassis-judge",
        **parsed,
        "advisory": True,
    }


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(
            "usage: chassis_judge.py <doc.md> <response.txt> [out.json]\n"
            "  doc.md       — essay to judge\n"
            "  response.txt — pre-recorded LLM response (audit replay; no live call)\n"
            "  out.json     — optional output path; default stdout",
            file=sys.stderr,
        )
        return 2
    doc_text = Path(argv[1]).read_text(encoding="utf-8")
    response = Path(argv[2]).read_text(encoding="utf-8")
    result = chassis_judge(doc_text, dispatcher=lambda _p: response)
    out = json.dumps(result, indent=2)
    if len(argv) > 3:
        Path(argv[3]).write_text(out + "\n", encoding="utf-8")
        print(f"wrote {argv[3]}")
    else:
        print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
