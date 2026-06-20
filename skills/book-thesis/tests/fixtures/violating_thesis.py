"""Build a workspace whose Datalog consistency pass is a *non-vacuous* failure.

This freezes a known-bad D9/D10/D11 baseline before the pyDatalog -> EDN -> Cozo
port (Phase P3). C0.3 captures the consistency golden from this fixture, so the
:func:`build_violating_thesis` signature is load-bearing.

The workspace is built end-to-end from an authored thesis YAML
(``compile_thesis`` -> ``.knowledge/thesis-triples.ttl``) plus a hand-written
``claims/ledger.jsonl`` that inlines ``subject``/``value``/``implies``/
``supports_nodes`` on the records (the same shortcut the contradiction/orphan
tests use; the real claim schema is additionalProperties:false, but
``datalog_consistency`` keeps a record-level fallback for synthetic records).

Intended defects (fixed ids/values, deterministic across tmp_paths):

* **D9 orphan** — ``clm-orphan`` declares ``supports_nodes: [floating-leg]`` and
  ``floating-leg`` is in NO thesis node, so it cannot reach :Thesis ->
  ``orphan_paragraph``. The same unreachable supports edge also trips one D11
  ``unreachable_supports``.
* **D10 transitive contradiction** — ``clm-b`` and ``clm-c`` share subject
  ``bmd_usd_rate`` with different values (a direct contradiction), and
  ``clm-a`` ``implies`` ``clm-b``; therefore ``clm-a`` transitively contradicts
  ``clm-c``. The pass emits the direct B<->C as one D10 and the transitive
  A<->C as a second, deduped, D10.
* **D11 invariant_violation** — the thesis authors a ``parish-count`` invariant
  (``formal: claims(P, parish_count, N), N != 9``); ``clm-bad-parish`` is a
  verified claim stating ``parish_count = 7``, violating it. ``clm-ok-parish``
  states the conforming value 9 and must NOT trip it. Note: ``clm-bad-parish``
  (7) and ``clm-ok-parish`` (9) share subject ``parish_count``, so the pass also
  emits an *intentional* ``direct_contradiction`` D10 between them. That extra
  D10 pair is expected and is recorded in the violating golden.

Every sub-argument declares ``advanced_by_chapters`` so the pass does not flood
D11 with ``sub_arg_no_chapter`` noise. ``missing_evidence`` is intentionally
allowed to fire (the ledger carries structured subjects, so each declared
evidence slot that no claim's subject meets is reported) — extra D11s are
acceptable; the golden's job is to pin >=1 of each class with >=1
invariant_violation present, which this fixture guarantees.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from compile_thesis import compile_thesis  # noqa: E402

_BOOK_ID = "violating"

# Note: ch-01/ch-02 in advanced_by_chapters are synthetic sentinel chapter ids
# not defined in the compiled TTL; they exist only to suppress sub_arg_no_chapter
# D11 noise.
_THESIS_YAML = """\
book_id: violating
thesis:
  statement: A deliberately-violating thesis for the D9-D11 consistency golden.
  polarity: descriptive
  scope: characterization fixture only
sub_arguments:
  - id: first-leg
    parent: thesis
    statement: The first sub-argument carries half the weight.
    polarity: descriptive
    advanced_by_chapters: [ch-01]
  - id: second-leg
    parent: thesis
    statement: The second sub-argument carries the other half.
    polarity: descriptive
    advanced_by_chapters: [ch-02]
invariants:
  - id: parish-count
    rule: Bermuda has nine traditional parishes.
    formal: |
      contradicts(P, parish_count_canonical) :-
        claims(P, parish_count, N), N != 9.
"""

# Inlined subject/value/implies/supports_nodes on synthetic ledger records.
_LEDGER: tuple[dict, ...] = (
    # D9 orphan (+ one D11 unreachable_supports): supports a node nowhere in
    # the thesis tree.
    {"claim_id": "clm-orphan", "status": "verified", "subject": "source-lost",
     "value": "ok", "supports_nodes": ["floating-leg"]},
    # D10 direct contradiction: B and C share a subject with different values.
    {"claim_id": "clm-b", "status": "verified", "subject": "bmd_usd_rate",
     "value": 1.0, "supports_nodes": ["first-leg"]},
    {"claim_id": "clm-c", "status": "verified", "subject": "bmd_usd_rate",
     "value": 1.5, "supports_nodes": ["second-leg"]},
    # D10 transitive: A implies B, so A transitively contradicts C.
    {"claim_id": "clm-a", "status": "verified", "subject": "peg_policy",
     "value": "fixed", "implies": ["clm-b"], "supports_nodes": ["first-leg"]},
    # D11 invariant_violation: parish_count != 9 violates the authored invariant.
    {"claim_id": "clm-bad-parish", "status": "verified",
     "subject": "parish_count", "value": 7, "supports_nodes": ["first-leg"]},
    # Conforming companion: parish_count == 9 must NOT trip the invariant.
    # NB: it shares subject parish_count with clm-bad-parish (7 != 9), so the
    # pass also emits an intentional direct_contradiction D10 between the two;
    # that pair is expected and recorded in the violating golden.
    {"claim_id": "clm-ok-parish", "status": "verified",
     "subject": "parish_count", "value": 9, "supports_nodes": ["second-leg"]},
)


def build_violating_thesis(tmp_path: Path) -> Path:
    """Build a complete violating workspace under ``tmp_path`` and return it.

    Writes ``thesis/violating.yaml``, compiles it to
    ``.knowledge/thesis-triples.ttl``, and writes ``claims/ledger.jsonl``. The
    resulting workspace, when passed to ``datalog_consistency.run``, yields at
    least one D9 orphan, one D10 (transitive) contradiction, and one D11
    invariant_violation. Deterministic: identical bytes for any ``tmp_path``.
    """
    workspace = Path(tmp_path)
    thesis_dir = workspace / "thesis"
    thesis_dir.mkdir(parents=True, exist_ok=True)
    (thesis_dir / f"{_BOOK_ID}.yaml").write_text(_THESIS_YAML, encoding="utf-8", newline="\n")

    compile_thesis(workspace, _BOOK_ID)

    claims_dir = workspace / "claims"
    claims_dir.mkdir(parents=True, exist_ok=True)
    (claims_dir / "ledger.jsonl").write_text(
        "".join(json.dumps(rec, sort_keys=True) + "\n" for rec in _LEDGER),
        encoding="utf-8",
        newline="\n",
    )
    return workspace
