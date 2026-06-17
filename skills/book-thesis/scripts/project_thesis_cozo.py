"""Project a thesis YAML spine into the shared Cozo store (REQ-KG-016, P3.1).

`project_thesis(workspace, store, book_id=None)` reads ``thesis/<book-id>.yaml``
and loads its root thesis node, sub-arguments, and invariants into
book-knowledge's ``thesis-node`` / ``sub-argument`` / ``invariant`` relations.
This is the EDN-front/Cozo-back counterpart of :mod:`compile_thesis` (the RDF/TTL
emit), which stays in parallel and is NOT replaced; the P3.2 D9-D11 consistency
pass runs over the rows this loads.

The YAML is read-only (never reopened for writing). The projection is
deterministic: ids are the authored slugs (unique within a thesis), so no hashing
is needed and re-projection upserts identical rows.

Mapping to ``kg-schema.edn`` (mirrors compile_thesis's triple shape):
  - the ``thesis:`` block -> one ``thesis-node`` row keyed ``"thesis"`` (the
    canonical root id a sub-argument's ``parent`` joins; compile_thesis maps the
    literal parent ``thesis`` to its single :Thesis node).
  - each ``sub_arguments[]`` entry -> a ``sub-argument`` row; ``parent`` defaults
    to / normalizes the literal ``thesis`` to the root id.
  - each ``invariants[]`` entry -> an ``invariant`` row carrying ``rule`` /
    ``formal`` plus the machine-readable ``subject`` + ``pinned-value`` /
    ``forbidden-value`` parsed from ``formal`` (reusing compile_thesis's parser,
    the single source of that parse), for the P3.2 D11 check.

Out of P3.1 scope (deliberately not loaded): a sub-argument's
``required_evidence`` / ``advanced_by_chapters`` (the relational form of
compile_thesis's ``requiresEvidence`` / ``advancedBy``). The schema declares an
``:advanced-by`` relation but the D9-D11 pass still feeds those via the RDF/TTL
path; a Cozo-side projection of them is a follow-on if P3.2 needs the join.

The store is built by the caller (via the P3.0 sibling bridge) so this module
stays a pure loader and never imports book-knowledge directly.
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

# Reuse compile_thesis's authored-formal parser so the Cozo invariant rows carry
# the SAME (subject, op, literal) compile_thesis emits as RDF — one parse, no drift.
from compile_thesis import _parse_invariant_formal  # noqa: E402

# Canonical root thesis-node id. compile_thesis maps a sub-argument's parent
# ``thesis`` (case-insensitive) to its single :Thesis node; we key the root row
# the same so ``sub-argument.parent`` joins ``thesis-node.id``.
_ROOT_ID = "thesis"


def _book_id(workspace: Path, book_id: str | None) -> str:
    """Return the book id, inferring it from the single ``thesis/*.yaml`` if absent.

    ``thesis/schema.yaml`` (the spec doc) and ``thesis/claim-facts.yaml`` (the
    structured claim-fact sidecar) are excluded from inference. If the book id is
    ambiguous (zero or several candidates), the caller must pass it.
    """
    if book_id is not None:
        return book_id
    thesis_dir = workspace / "thesis"
    candidates = [
        p.stem
        for p in sorted(thesis_dir.glob("*.yaml"))
        if p.stem not in {"schema", "claim-facts"}
    ]
    if len(candidates) != 1:
        raise ValueError(
            f"cannot infer book_id from {thesis_dir}: candidates={candidates}; "
            f"pass book_id explicitly"
        )
    return candidates[0]


def _clean(value) -> str | None:
    """Stripped string, or None when absent/blank (so load stores a null cell)."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def project_thesis(workspace: Path, store, book_id: str | None = None) -> None:
    """Load ``thesis/<book-id>.yaml``'s spine into ``store`` (read-only on the YAML).

    Loads one ``thesis-node`` row, one ``sub-argument`` row per ``sub_arguments[]``
    entry, and one ``invariant`` row per ``invariants[]`` entry. ``store`` is a
    book-knowledge ``CozoStore`` (built by the caller via the P3.0 sibling bridge).
    """
    workspace = Path(workspace)
    bid = _book_id(workspace, book_id)
    spec = yaml.safe_load(
        (workspace / "thesis" / f"{bid}.yaml").read_text(encoding="utf-8")
    )
    if not isinstance(spec, dict):
        raise ValueError(f"thesis/{bid}.yaml: expected a mapping at top level")

    thesis = spec.get("thesis") or {}
    thesis_row = {
        "id": _ROOT_ID,
        "statement": (thesis.get("statement") or "").strip(),
        "polarity": _clean(thesis.get("polarity")),
        "scope": _clean(thesis.get("scope")),
    }

    sub_rows: list[dict] = []
    for sub in spec.get("sub_arguments") or []:
        if "id" not in sub:
            raise ValueError(f"sub_argument missing id: {sub!r}")
        parent = (str(sub.get("parent") or "thesis")).strip()
        if parent.lower() == "thesis":
            parent = _ROOT_ID
        sub_rows.append({
            "id": str(sub["id"]).strip(),
            "statement": _clean(sub.get("statement")),
            "polarity": _clean(sub.get("polarity")),
            "parent": parent,
        })

    inv_rows: list[dict] = []
    for inv in spec.get("invariants") or []:
        if "id" not in inv:
            raise ValueError(f"invariant missing id: {inv!r}")
        row: dict = {
            "id": str(inv["id"]).strip(),
            "rule": _clean(inv.get("rule")),
        }
        formal = (inv.get("formal") or "").strip()
        if formal:
            row["formal"] = formal
            parsed = _parse_invariant_formal(formal)
            if parsed is not None:
                subject, op, lit = parsed
                row["subject"] = subject
                # `op` is the comparison that SIGNALS a violation. For the
                # `!= lit` form a claim violates when its value != lit, so lit is
                # the PINNED canonical value (claims MUST equal it). For the
                # `== lit` form a claim violates when its value == lit, so lit is
                # the FORBIDDEN value (claims MUST NOT equal it). Mirrors
                # compile_thesis's invariantPinnedValue/invariantForbiddenValue.
                row["pinned-value" if op == "!=" else "forbidden-value"] = lit
        inv_rows.append(row)

    store.load("thesis-node", [thesis_row])
    store.load("sub-argument", sub_rows)
    store.load("invariant", inv_rows)


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(
            "usage: project_thesis_cozo.py <workspace-dir> [book-id]",
            file=sys.stderr,
        )
        return 2
    from sibling_skills import book_knowledge_root, load_book_knowledge_module

    cozo_store = load_book_knowledge_module("cozo_store")
    schema = book_knowledge_root() / "assets" / "kg-schema.edn"
    store = cozo_store.CozoStore.in_memory(schema_path=schema)
    book_id = argv[2] if len(argv) > 2 else None
    project_thesis(Path(argv[1]), store, book_id)
    print("projected thesis spine into cozo store")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
