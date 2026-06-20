"""Normalized contradiction workbench for S4."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from .booklogic_kg import compile_contradiction_workbench_rules
from .cozo_store import CozoStore
from .io_utils import latest_per, read_jsonl
from .project_ledger_cozo import project_ledger
from .workspace import WorkspaceLayout

ASSETS = Path(__file__).resolve().parent.parent / "assets"
KG_SCHEMA = ASSETS / "kg-schema.edn"
WORKBENCH_RULES = ASSETS / "kg-rules" / "contradiction-workbench.edn"


class NLIUnavailable(RuntimeError):
    """Raised by an injected NLI seam when it is offline or unavailable."""


def _sort_dicts(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: json.dumps(row, sort_keys=True, separators=(",", ":")),
    )


def canonical_workbench_result(payload: Any) -> Any:
    """Canonicalize nested rows for result-set equality checks."""
    if isinstance(payload, dict):
        return {key: canonical_workbench_result(payload[key]) for key in sorted(payload)}
    if isinstance(payload, list):
        return sorted(
            (canonical_workbench_result(item) for item in payload),
            key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":")),
        )
    return payload


def _run_rule(store: CozoStore, output: str) -> list[list[Any]]:
    script = compile_contradiction_workbench_rules(
        WORKBENCH_RULES.read_text(encoding="utf-8"),
        KG_SCHEMA,
        output=output,
    )
    return store.query(script)


def _quantity_alerts(rows: list[list[Any]]) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []
    for claim_a, claim_b, subject, predicate, left, right, unit in rows:
        alerts.append(
            {
                "type": "hard-contradiction",
                "rule": "quantity-clash",
                "claim_ids": [claim_a, claim_b],
                "severity": "hard",
                "evidence": {
                    "subject": subject,
                    "predicate": predicate,
                    "left_canonical_value": left,
                    "right_canonical_value": right,
                    "canonical_unit": unit,
                },
            }
        )
    return _sort_dicts(alerts)


def _interval_alerts(rows: list[list[Any]]) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []
    for claim_a, claim_b, subject, predicate, required, ls, le, rs, re in rows:
        alerts.append(
            {
                "type": "interval-inconsistency",
                "rule": "interval-inconsistency",
                "claim_ids": [claim_a, claim_b],
                "severity": "hard",
                "evidence": {
                    "subject": subject,
                    "predicate": predicate,
                    "required_relation": required,
                    "left_interval": [ls, le],
                    "right_interval": [rs, re],
                },
            }
        )
    return _sort_dicts(alerts)


def _candidate_pairs(rows: list[list[Any]]) -> list[list[str]]:
    return sorted([[str(row[0]), str(row[1])] for row in rows])


def _latest_claims(layout: WorkspaceLayout | None) -> dict[str, dict[str, Any]]:
    if layout is None:
        return {}
    return latest_per(read_jsonl(layout.ledger), "claim_id")


def _supersession_alerts(layout: WorkspaceLayout | None) -> list[dict[str, Any]]:
    latest = _latest_claims(layout)
    alerts: list[dict[str, Any]] = []

    def chain_has_cycle(start: str) -> bool:
        seen: set[str] = set()
        cursor = start
        while cursor:
            if cursor in seen:
                return True
            seen.add(cursor)
            target = latest.get(cursor, {}).get("supersedes")
            if not target or target not in latest:
                return False
            cursor = str(target)
        return False

    for claim_id, record in sorted(latest.items()):
        target = record.get("supersedes")
        if not target:
            continue
        target = str(target)
        if target not in latest:
            alerts.append(
                {
                    "type": "supersession-invalid",
                    "rule": "supersession-invalid",
                    "claim_ids": [claim_id, target],
                    "severity": "hard",
                    "evidence": {"kind": "missing-target"},
                }
            )
            continue
        if chain_has_cycle(claim_id):
            alerts.append(
                {
                    "type": "supersession-invalid",
                    "rule": "supersession-invalid",
                    "claim_ids": [claim_id, target],
                    "severity": "hard",
                    "evidence": {"kind": "cycle"},
                }
            )
            continue
        if latest[target].get("status") != "superseded":
            alerts.append(
                {
                    "type": "supersession-stale",
                    "rule": "supersession-stale",
                    "claim_ids": [claim_id, target],
                    "severity": "hard",
                    "evidence": {
                        "kind": "target-still-current",
                        "target_status": latest[target].get("status"),
                    },
                }
            )
    return _sort_dicts(alerts)


def run_symbolic_checks(
    store: CozoStore,
    *,
    layout: WorkspaceLayout | None = None,
) -> dict[str, Any]:
    """Run deterministic symbolic contradiction checks."""
    quantity = _quantity_alerts(_run_rule(store, "quantity-clash"))
    interval = _interval_alerts(_run_rule(store, "interval-inconsistency"))
    supersession = _supersession_alerts(layout)
    alerts = _sort_dicts(quantity + interval + supersession)
    return {
        "symbolic_defects": alerts,
        "contradiction_alerts": alerts,
        "candidate_pairs": _candidate_pairs(_run_rule(store, "candidate-pairs")),
    }


def _resolved_pairs(symbolic: dict[str, Any]) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for alert in symbolic["symbolic_defects"]:
        claim_ids = alert.get("claim_ids", [])
        if len(claim_ids) == 2:
            pairs.add(tuple(sorted(map(str, claim_ids))))
    return pairs


def _nli_payload(
    left: str,
    right: str,
    latest: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    return {
        "left_claim_id": left,
        "right_claim_id": right,
        "left_text": latest.get(left, {}).get("canonical_text", ""),
        "right_text": latest.get(right, {}).get("canonical_text", ""),
    }


def _run_residue(
    symbolic: dict[str, Any],
    latest: dict[str, dict[str, Any]],
    nli_call: Callable[[dict[str, Any]], Any] | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    resolved = _resolved_pairs(symbolic)
    residue_rows: list[dict[str, Any]] = []
    residue_alerts: list[dict[str, Any]] = []
    for left, right in symbolic["candidate_pairs"]:
        pair = tuple(sorted((left, right)))
        if pair in resolved:
            continue
        base = {
            "claim_ids": [left, right],
            "rule": "paraphrastic-residue",
        }
        if nli_call is None:
            residue_rows.append(
                {**base, "status": "unresolved", "reason": "nli-unavailable"}
            )
            continue
        try:
            response = nli_call(_nli_payload(left, right, latest))
        except NLIUnavailable:
            residue_rows.append(
                {**base, "status": "unresolved", "reason": "nli-unavailable"}
            )
            continue
        if isinstance(response, dict):
            status = str(response.get("status", "resolved"))
            row = {**base, "status": status}
            if "confidence" in response:
                row["confidence"] = response["confidence"]
        else:
            status = str(response)
            row = {**base, "status": status}
        residue_rows.append(row)
        if status == "contradiction":
            residue_alerts.append(
                {
                    "type": "paraphrastic-contradiction",
                    "rule": "paraphrastic-residue",
                    "claim_ids": [left, right],
                    "severity": "model",
                    "evidence": {"status": status},
                }
            )
    return _sort_dicts(residue_rows), _sort_dicts(residue_alerts)


def run_contradiction_workbench(
    layout: WorkspaceLayout,
    *,
    nli_call: Callable[[dict[str, Any]], Any] | None = None,
) -> dict[str, Any]:
    """Project a workspace and run symbolic checks plus optional NLI residue."""
    store = CozoStore.in_memory(KG_SCHEMA)
    project_ledger(layout, store)
    symbolic = run_symbolic_checks(store, layout=layout)
    residue, residue_alerts = _run_residue(symbolic, _latest_claims(layout), nli_call)
    alerts = _sort_dicts(symbolic["contradiction_alerts"] + residue_alerts)
    return {
        "symbolic": symbolic,
        "residue": residue,
        "contradiction_alerts": alerts,
    }
