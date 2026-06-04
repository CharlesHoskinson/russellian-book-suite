"""Blocking stdin prompt for the expansion gate.

The audit pauses here and waits for the operator to either approve the audit sample
or halt. Returns a list of accept/reject decisions, OR the string "halt" if the
operator typed halt.
"""

from __future__ import annotations

from pathlib import Path


def prompt_operator(sample_path: Path, n_sample: int, n_verified: int, input_fn=input) -> str | list[str]:
    """Prompt operator for accept/reject/tag-revise decisions or halt.

    Returns:
      "halt" if the operator typed halt.
      list[str] of {"accept", "reject"} tokens otherwise. The "tag-revise" token from the
      audit-sample markdown is accepted and normalized to "accept" — the audit pipeline
      treats tag-revise as a non-halt outcome (the index entry lands; the operator notes
      the tag for a later revision pass outside this audit).

    Raises ValueError if the response contains an unrecognised token or wrong count.
    """
    prompt = (
        f"\nAudit sample written to: {sample_path}\n"
        f"The sample contains {n_sample} entries ({n_sample}/{n_verified} verified).\n"
        "For each entry, mark accept, reject, or tag-revise.\n\n"
        "Reply with a comma-separated list of decisions in order, e.g.:\n"
        "    accept,accept,reject\n"
        "    accept,tag-revise,accept\n\n"
        "tag-revise is treated as accept for the audit pass — the entry lands in the\n"
        "index and you note the tag for a later revision outside this audit.\n\n"
        "Or reply 'halt' to stop without appending any entries.\n\n"
        "Decision: "
    )
    raw = input_fn(prompt).strip()
    if raw.lower() == "halt":
        return "halt"
    tokens = [t.strip().lower() for t in raw.split(",") if t.strip()]
    if not all(t in {"accept", "reject", "tag-revise"} for t in tokens):
        raise ValueError(f"unexpected token in response: {raw!r}")
    if len(tokens) != n_sample:
        raise ValueError(f"expected {n_sample} decisions, got {len(tokens)}")
    # Normalise tag-revise to accept for downstream reject-rate computation.
    return ["accept" if t == "tag-revise" else t for t in tokens]
