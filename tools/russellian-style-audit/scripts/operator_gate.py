"""Blocking stdin prompt for the expansion gate.

The audit pauses here and waits for the operator to either approve the audit sample
or halt. Returns a list of accept/reject decisions, OR the string "halt" if the
operator typed halt.
"""

from __future__ import annotations

from pathlib import Path


def prompt_operator(sample_path: Path, n_sample: int, n_verified: int, input_fn=input) -> str | list[str]:
    """Prompt operator for accept/reject decisions or halt.

    Returns:
      "halt" if the operator typed halt.
      list[str] of accept/reject tokens otherwise.

    Raises ValueError if the response is unparseable or has wrong token count.
    """
    prompt = (
        f"\nAudit sample written to: {sample_path}\n"
        f"The sample contains {n_sample} entries ({n_sample}/{n_verified} verified).\n"
        "For each entry, mark accept or reject.\n\n"
        "Reply with a comma-separated list of decisions in order, e.g.:\n"
        "    accept,accept,reject\n\n"
        "Or reply 'halt' to stop without appending any entries.\n\n"
        "Decision: "
    )
    raw = input_fn(prompt).strip()
    if raw.lower() == "halt":
        return "halt"
    tokens = [t.strip().lower() for t in raw.split(",") if t.strip()]
    if not all(t in {"accept", "reject"} for t in tokens):
        raise ValueError(f"unexpected token in response: {raw!r}")
    if len(tokens) != n_sample:
        raise ValueError(f"expected {n_sample} decisions, got {len(tokens)}")
    return tokens
