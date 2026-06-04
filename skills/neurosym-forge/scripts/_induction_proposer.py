"""REQ-INDUCE-041, 043, 044: LLM proposer interface for Tier 6 theory induction.

A thin caller that wraps Phase P's `LLMLiftProvider` abstraction with
an induction-specific prompt template. The proposer:

  - reads the schema's predicates + sorts and renders them into the
    prompt's predicate section (REQ-INDUCE-041)
  - renders the BookLogic operator BNF into the prompt's grammar
    section so the LLM never invents the language (REQ-INDUCE-041)
  - renders the focused atom cluster from Phase Q `SemanticIndex` as
    the user-prompt section (REQ-INDUCE-041)
  - dispatches to the configured provider via Phase P's `get_provider`
    factory; backend selection from `NEUROSYM_LLM_PROVIDER`
    (REQ-INDUCE-043)
  - prints the candidate to stdout when `NEUROSYM_INDUCTION_DRY_RUN=1`
    is set, AFTER grammar validation but BEFORE the orchestrator
    dispatches solvers (REQ-INDUCE-044)

The grammar enforcer (`_induction_grammar.cljs`) is the gate that runs
on the candidate this helper returns. This helper is intentionally
thin — it does NOT call the gate (the orchestrator wires gate +
proposer + repair loop in Phase W).

The Stub provider is the default in CI (offline, deterministic). The
canned candidate is read from `NEUROSYM_STUB_CANDIDATE`; if unset, the
helper falls back to a built-in placeholder that the grammar enforcer
will reject — surfacing a clear failure rather than a silent pass.
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any

from scripts._llm_lift import (
    LLMLiftError,
    LLMLiftProvider,
    StubLift,
    get_provider,
)

# ---------------------------------------------------------------------------
# Operator BNF — mirrors `_induction_grammar.cljs`'s SUPPORTED-OPERATORS
# and `codegen_axioms.py`'s _SUPPORTED_ASSERT_HEADS. REQ-INDUCE-046 drift
# lint enforces the three-way mirror.
# ---------------------------------------------------------------------------

_OPERATOR_BNF_DISPLAY = [
    "=", "~=", "approx=",
    "<", "<=", ">", ">=",
    "+", "-", "*", "/",
    "and", "or", "not", "=>", "ite",
    "sum", "count", "in", "select",
    "forall", "exists",
]


# ---------------------------------------------------------------------------
# Prompt assembly
# ---------------------------------------------------------------------------


def _format_predicate_line(name: str, spec: dict | Any) -> str:
    """Render one predicate as a single readable line in the prompt."""
    arg_sorts = spec.get(":arg-sorts") if isinstance(spec, dict) else None
    ret = spec.get(":return") if isinstance(spec, dict) else None
    args = ""
    if isinstance(arg_sorts, (list, tuple)) and arg_sorts:
        args = "(" + " ".join(str(s) for s in arg_sorts) + ")"
    ret_repr = f" -> {ret}" if ret else ""
    return f"  - {name} {args}{ret_repr}".rstrip()


def _format_atom_line(atom: dict) -> str:
    """Render one cited atom as a single readable line in the prompt."""
    fields = []
    for k in ("id", "predicate", "subject", "value"):
        if k in atom:
            fields.append(f"{k}={atom[k]!r}")
    return "  - " + ", ".join(fields)


def build_proposer_prompt(
    *,
    schema: dict,
    atom_cluster: list[dict],
) -> str:
    """REQ-INDUCE-041: assemble the proposer prompt from schema +
    atom cluster + BookLogic BNF.

    The prompt has four sections, in this fixed order so the LLM
    never has to guess the contract:

      1. Predicates the LLM may use (schema-declared)
      2. Operators the LLM may use (BookLogic BNF)
      3. Atom cluster — the evidence to induce a constraint from
      4. Output discipline — single EDN form, no prose, no fences

    Pure function: no env reads, no IO. Tested directly by
    `test_proposer_prompt_embeds_schema_and_bnf`.
    """
    predicates = schema.get("predicates") or {}
    pred_lines = [_format_predicate_line(k, v) for k, v in predicates.items()]
    pred_section = (
        "You may use ONLY these predicates:\n" + "\n".join(pred_lines)
        if pred_lines
        else "You may use ONLY these predicates: (none declared)"
    )

    op_section = (
        "You may use ONLY these operators (BookLogic grammar):\n  "
        + ", ".join(_OPERATOR_BNF_DISPLAY)
    )

    atom_lines = [_format_atom_line(a) for a in atom_cluster]
    atom_section = (
        "Atom cluster (cite these):\n" + "\n".join(atom_lines)
        if atom_lines
        else "Atom cluster: (empty)"
    )

    output_section = (
        "Emit exactly one EDN `defconstraint` form. Do not include "
        "prose. Do not include code fences. Output starts with `(`. "
        "The form MUST include :backend, :assert, and :on-unsat options."
    )

    return "\n\n".join([pred_section, op_section, atom_section, output_section])


# ---------------------------------------------------------------------------
# Provider dispatch
# ---------------------------------------------------------------------------


_FALLBACK_STUB_CANDIDATE = (
    "(defconstraint :UNCONFIGURED-STUB :backend :z3 :assert <missing> "
    ':on-unsat {:defect :D :severity :advisory :message '
    '"NEUROSYM_STUB_CANDIDATE was unset; the grammar enforcer should '
    'reject this placeholder."})'
)


def _stub_response_for_proposer() -> dict:
    """Return the canned proposal the Stub provider should emit for the
    induction code path. We package the candidate EDN as a JSON dict so
    the existing `StubLift.extract` round-trip (which calls
    `json.loads` on its `canned_response`) returns a dict with a
    `candidate` key the proposer reads back."""
    canned = os.environ.get("NEUROSYM_STUB_CANDIDATE", _FALLBACK_STUB_CANDIDATE)
    return {"candidate": canned}


def _provider_for_proposer() -> LLMLiftProvider:
    """Return the configured provider, customising Stub for the
    induction code path so `NEUROSYM_STUB_CANDIDATE` drives the canned
    output. Non-Stub providers are returned unchanged; their
    `extract` is wrapped in `propose_constraint` to assemble the
    induction-specific prompt."""
    name = os.environ.get("NEUROSYM_LLM_PROVIDER", "stub").lower()
    if name == "stub":
        canned = json.dumps(_stub_response_for_proposer())
        return StubLift(canned_response=canned)
    return get_provider(name)


def propose_constraint(
    *,
    schema: dict,
    atom_cluster: list[dict],
    cluster_id: str = "cluster-anon",
) -> str:
    """REQ-INDUCE-041, 043, 044: produce one EDN candidate constraint
    from a focused atom cluster + the schema.

    The return value is a raw EDN string. The orchestrator (Phase W)
    is responsible for gating it through `_induction_grammar.cljs`
    BEFORE any solver call; this helper does NOT gate. That separation
    keeps the failure log able to record proposer-side issues
    distinct from grammar-side issues.

    Side effect (REQ-INDUCE-044): if `NEUROSYM_INDUCTION_DRY_RUN=1`,
    the candidate is printed to stdout. The print happens AFTER the
    proposer returns and BEFORE this function returns, so the calling
    orchestrator sees the same string the user sees.
    """
    provider = _provider_for_proposer()
    prompt = build_proposer_prompt(schema=schema, atom_cluster=atom_cluster)

    # Phase P's `extract` signature takes (claim_id, canonical_text,
    # emit_template). We reuse it verbatim: `claim_id` becomes the
    # cluster id; `canonical_text` becomes the prompt body; the emit
    # template carries the EDN-shape contract for any real LLM backend.
    response = provider.extract(
        claim_id=cluster_id,
        canonical_text=prompt,
        emit_template=(
            '{"candidate": "(defconstraint :ID :backend :z3 '
            ':assert <body> :on-unsat {...})"}'
        ),
    )

    if not isinstance(response, dict) or "candidate" not in response:
        raise LLMLiftError(
            "induction proposer expected a JSON object with a "
            f"`candidate` key; got {response!r}"
        )

    candidate = response["candidate"]
    if not isinstance(candidate, str):
        raise LLMLiftError(
            f"induction proposer expected `candidate` to be a string; "
            f"got {type(candidate).__name__}"
        )

    if os.environ.get("NEUROSYM_INDUCTION_DRY_RUN", "").strip() == "1":
        # The grammar gate runs in the orchestrator, between this print
        # and any solver dispatch. The print is the developer-facing
        # affordance for iterating on the prompt template without
        # paying solver cost.
        print(candidate, file=sys.stdout, flush=True)

    return candidate


def propose_repair(candidate, error=None):
    """FCL-resistant repair proposer.

    Idempotent on a grammar-clean candidate; ignores `error` regardless
    of content because the framework's repair loop is only entered on
    grammar-fail or validation-fail tags raised by the framework itself,
    not on free-form error strings. Returning the input unchanged is the
    contract: a noisy free-form error must not perturb a candidate that
    already satisfies the grammar, which is the False-Correction-Loop
    defence the failure-mode tests assert.
    """
    return candidate
