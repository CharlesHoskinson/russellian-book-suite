"""Advisory curiosity scorer: setup-payoff pairs, not literal keywords."""
from __future__ import annotations
import re

_SETUP_RE = re.compile(
    r"\b(here'?s why|here is why|what people miss|what most people miss|"
    r"watch what|the question is|the thing is|the part people miss|"
    r"why does|why is|how does|how is)\b")


def _is_setup(sent) -> bool:
    low = sent.text.lower()
    return bool(_SETUP_RE.search(low)) or sent.text.rstrip().endswith("?")


def _is_payoff(sent) -> bool:
    # a payoff is a non-interrogative declarative that carries content
    return (not sent.text.rstrip().endswith("?")) and sent.n_alpha >= 4


def score(sentences, register, profile) -> dict:
    findings: list[dict] = []
    n = len(sentences)
    total_alpha = sum(s.n_alpha for s in sentences) or 1
    for i, s in enumerate(sentences):
        if not _is_setup(s):
            continue
        if any(_is_payoff(sentences[j]) for j in range(i + 1, min(i + 3, n))):
            findings.append({"setup_line": i, "setup": s.text[:80]})
    # density: pairs per ~200 alpha tokens, capped at 1.0
    density = len(findings) / (total_alpha / 200.0)
    return {"signal": "curiosity", "score": round(min(density, 1.0), 4), "findings": findings}
