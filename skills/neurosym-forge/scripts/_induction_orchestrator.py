"""REQ-INDUCE-050..057: candidate-generation orchestrator.

Main loop for the Tier 6 candidate-generation stage. Mirrors the CLJS
entry point ``induce_theory.cljs`` line-for-line so the framework's
first nbb-driven Python-equivalent stays in sync.

Pipeline:
  1. Load schema (rules/booklogic-schema.edn) and atomspace
     (rules/atomspace.edn).
  2. Run Horn-body mining over the atomspace.
  3. Run Popper-style typed search over the schema.
  4. For each Phase Q semantic cluster, invoke the LLM proposer (Phase V
     when available, else the StubProposer fallback).
  5. Dedup by canonical S-expr form (REQ-INDUCE-052).
  6. Persist the queue to work/induction/candidates.edn with rejection
     reasons retained (REQ-INDUCE-055).

The ranking step (REQ-INDUCE-053) and the budget tracker
(REQ-INDUCE-056) are wired in follow-on commits.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts import _induction_sources as sources
from scripts._edn_reader import Keyword
from scripts._io import read_edn_file, write_edn_file


# ---------------------------------------------------------------------------
# Schema + atomspace loading
# ---------------------------------------------------------------------------


def load_schema(project_root: Path) -> dict[str, Any]:
    schema_path = project_root / "rules" / "booklogic-schema.edn"
    if not schema_path.exists():
        return {Keyword("version"): 1, Keyword("predicates"): {}, Keyword("sorts"): []}
    return read_edn_file(schema_path)


def load_atoms(project_root: Path) -> list[dict[str, Any]]:
    atoms_path = project_root / "rules" / "atomspace.edn"
    if not atoms_path.exists():
        return []
    data = read_edn_file(atoms_path)
    raw = data.get(Keyword("atoms"), [])
    out: list[dict[str, Any]] = []
    for a in raw:
        pred = a.get(Keyword("predicate"))
        subj = a.get(Keyword("subject"))
        out.append(
            {
                "claim_id": a.get(Keyword("claim-id")),
                "document": a.get(Keyword("document")),
                "predicate": pred.name if isinstance(pred, Keyword) else str(pred),
                "subject": subj.name if isinstance(subj, Keyword) else str(subj),
                "value": a.get(Keyword("value")),
            }
        )
    return out


# ---------------------------------------------------------------------------
# Cluster discovery
# ---------------------------------------------------------------------------


def _atom_clusters(atoms: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    """Group atoms by predicate; each predicate is one cluster.

    REQ-INDUCE-051(c): the LLM proposer is invoked once per cluster.
    Tier 7 will replace this with Phase Q-driven embedding clusters;
    for Tier 6 a predicate-grouped cluster is the deterministic
    minimum.
    """
    by_pred: dict[str, list[dict[str, Any]]] = {}
    for a in atoms:
        by_pred.setdefault(a["predicate"], []).append(a)
    return [by_pred[k] for k in sorted(by_pred.keys())]


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def _candidate_to_edn(c: dict[str, Any], cid: str) -> dict[Any, Any]:
    return {
        Keyword("id"): cid,
        Keyword("canonical-form"): c["canonical_form"],
        Keyword("origin"): list(c.get("origin", [])),
        Keyword("cited-atoms"): list(c.get("cited_atoms", [])),
        Keyword("coherence"): c.get("coherence"),
        Keyword("support"): c.get("support"),
        Keyword("literal-count"): c.get("literal_count", 0),
        Keyword("status"): Keyword(c.get("status", "pending")),
        Keyword("rejection-reason"): (
            Keyword(c["rejection_reason"])
            if c.get("rejection_reason")
            else None
        ),
    }


def _persist_queue(
    project_root: Path,
    *,
    survivors: list[dict[str, Any]],
    rejected: list[dict[str, Any]],
    corpus_size: int,
) -> None:
    out_dir = project_root / "work" / "induction"
    out_dir.mkdir(parents=True, exist_ok=True)
    queue: list[dict[Any, Any]] = []
    for i, c in enumerate(survivors):
        queue.append(_candidate_to_edn(c, f"c-{i:03d}"))
    for j, c in enumerate(rejected):
        queue.append(_candidate_to_edn(c, f"r-{j:03d}"))
    payload = {
        Keyword("version"): 1,
        Keyword("generated-at"): datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        Keyword("corpus-size"): corpus_size,
        Keyword("candidates"): queue,
    }
    write_edn_file(out_dir / "candidates.edn", payload)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def run(project_root: Path) -> int:
    """Run the orchestrator end-to-end against ``project_root``.

    Returns 0 on success, non-zero on infrastructural error.
    """
    sources.reset_warnings()
    schema = load_schema(project_root)
    atoms = load_atoms(project_root)

    # Source 1 — Horn-body mining
    horn_cands = sources.horn_mine(atoms, schema)

    # Source 2 — Popper-style typed search
    popper_cands = sources.popper_search(schema)

    # Source 3 — LLM proposer (Phase V or Stub fallback)
    llm_cands: list[dict[str, Any]] = []
    provider = sources.StubProposer()
    for cluster in _atom_clusters(atoms):
        cands = sources.llm_propose(
            schema=schema,
            cluster=cluster,
            provider=provider,
        )
        llm_cands.extend(cands)

    # Dedup with rejection logging (REQ-INDUCE-052, 055)
    all_cands = horn_cands + popper_cands + llm_cands
    survivors, rejected = sources.dedup_with_rejection_log(all_cands)

    _persist_queue(
        project_root,
        survivors=survivors,
        rejected=rejected,
        corpus_size=len(atoms),
    )
    return 0


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: induce_theory <project-root>", file=sys.stderr)
        return 2
    return run(Path(argv[0]))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
