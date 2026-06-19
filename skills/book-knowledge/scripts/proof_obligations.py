"""Proof-obligation lifecycle, checker replay, and scientific checks."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Callable, Mapping

import edn_format
import jsonschema

from .io_utils import latest_per, read_jsonl
from .workspace import WorkspaceLayout

ASSETS = Path(__file__).resolve().parent.parent / "assets"
OBLIGATION_SCHEMA = json.loads(
    (ASSETS / "proof-obligation.schema.json").read_text(encoding="utf-8")
)
ARTIFACT_SCHEMA = json.loads(
    (ASSETS / "verification-artifact.schema.json").read_text(encoding="utf-8")
)

CHECKER_KINDS = {"z3", "cvc5", "lean", "units", "stats-report"}


class ProofObligationValidationError(Exception):
    """Raised when a proof-obligation record or transition is invalid."""


Checker = Callable[[dict], dict]


def _kw_name(keyword) -> str:
    return keyword.name


def _load_status_enum(path: Path) -> tuple[frozenset[str], dict[str, set[str]]]:
    try:
        doc = edn_format.loads(path.read_text(encoding="utf-8"))
        states = [_kw_name(s) for s in doc[edn_format.Keyword("states")]]
        raw_transitions = doc[edn_format.Keyword("transitions")]
        items = (
            raw_transitions.dict.items()
            if hasattr(raw_transitions, "dict")
            else raw_transitions.items()
        )
        transitions = {
            _kw_name(src): {_kw_name(dst) for dst in targets}
            for src, targets in items
        }
    except (KeyError, AttributeError, TypeError, edn_format.EDNDecodeError) as exc:
        raise ProofObligationValidationError(
            f"proof-obligation status vocabulary is malformed: {exc!r}"
        ) from exc

    declared = set(states)
    named = set(transitions)
    for targets in transitions.values():
        named |= targets
    stray = named - declared
    if stray:
        raise ProofObligationValidationError(
            f"proof-obligation transition names undeclared statuses: {sorted(stray)}"
        )
    return frozenset(states), transitions


OBLIGATION_STATUSES, VALID_TRANSITIONS = _load_status_enum(
    ASSETS / "proof-obligation-status-enum.edn"
)


def _obligation_path(layout: WorkspaceLayout) -> Path:
    return layout.root / "claims" / "proof-obligations.jsonl"


def _artifact_ledger_path(layout: WorkspaceLayout) -> Path:
    return layout.root / "claims" / "verification-artifacts.jsonl"


def _json_dump(record: dict) -> str:
    return json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n"


def _append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(_json_dump(record))


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _relative_workspace_path(path: Path, layout: WorkspaceLayout) -> str:
    return path.relative_to(layout.root).as_posix()


def validate_proof_obligation(record: dict) -> None:
    """Validate one proof-obligation record against schema and lifecycle rules."""
    if "checker_kind" not in record:
        raise ProofObligationValidationError("proof-obligation missing checker_kind")
    if "status" not in record:
        raise ProofObligationValidationError("proof-obligation missing status")
    try:
        jsonschema.validate(record, OBLIGATION_SCHEMA)
    except jsonschema.ValidationError as exc:
        raise ProofObligationValidationError(str(exc)) from exc


def validate_verification_artifact(record: dict) -> None:
    """Validate one verification-artifact record."""
    try:
        jsonschema.validate(record, ARTIFACT_SCHEMA)
    except jsonschema.ValidationError as exc:
        raise ProofObligationValidationError(str(exc)) from exc


def assert_transition_allowed(old_status: str, new_status: str) -> None:
    allowed = VALID_TRANSITIONS.get(old_status, set())
    if new_status not in allowed:
        raise ProofObligationValidationError(
            f"transition {old_status!r} -> {new_status!r} not allowed; "
            f"valid: {sorted(allowed) or 'none (terminal)'}"
        )


def read_proof_obligations(layout: WorkspaceLayout) -> list[dict]:
    """Read the append-only proof-obligation ledger."""
    return read_jsonl(_obligation_path(layout))


def latest_proof_obligations(layout: WorkspaceLayout) -> dict[str, dict]:
    """Latest-per-id view of proof obligations."""
    return latest_per(read_proof_obligations(layout), "id")


def read_verification_artifacts(layout: WorkspaceLayout) -> list[dict]:
    """Read the append-only verification-artifact ledger."""
    return read_jsonl(_artifact_ledger_path(layout))


def latest_verification_artifacts(layout: WorkspaceLayout) -> dict[str, dict]:
    """Latest-per-id view of verification artifacts."""
    return latest_per(read_verification_artifacts(layout), "id")


def open_pending_obligation(
    layout: WorkspaceLayout,
    *,
    claim_id: str,
    statement: str,
    checker_kind: str,
    assumptions: str = "",
    normal_form: str = "",
) -> dict:
    """Create exactly one pending proof obligation for a claim."""
    obligation_id = f"obl-{claim_id}"
    existing = latest_proof_obligations(layout).get(obligation_id)
    if existing is not None:
        return existing

    record = {
        "id": obligation_id,
        "statement": statement,
        "linked_claim": claim_id,
        "checker_kind": checker_kind,
        "status": "pending",
        "assumptions": assumptions,
        "normal_form": normal_form,
    }
    validate_proof_obligation(record)
    _append_jsonl(_obligation_path(layout), record)
    return record


def waive_obligation(
    layout: WorkspaceLayout,
    obligation_id: str,
    *,
    waiver_reason: str,
) -> dict:
    """Append a waiver row for a pending obligation."""
    latest = latest_proof_obligations(layout).get(obligation_id)
    if latest is None:
        raise ProofObligationValidationError(f"unknown obligation {obligation_id!r}")
    assert_transition_allowed(latest["status"], "waived")
    record = dict(latest)
    record.update({"status": "waived", "waiver_reason": waiver_reason})
    validate_proof_obligation(record)
    _append_jsonl(_obligation_path(layout), record)
    return record


def run_checker(
    layout: WorkspaceLayout,
    obligation_id: str,
    *,
    checker_dispatch: Mapping[str, Checker],
    checked_at: str,
) -> dict:
    """Run an injected checker or replay a discharged obligation from artifact."""
    latest = latest_proof_obligations(layout).get(obligation_id)
    if latest is None:
        raise ProofObligationValidationError(f"unknown obligation {obligation_id!r}")

    if latest.get("status") == "discharged" and latest.get("artifact_path"):
        artifact_path = layout.root / latest["artifact_path"]
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        return {
            "id": latest["id"],
            "status": "discharged",
            "artifact_path": latest["artifact_path"],
            "artifact": artifact,
            "checked_at": latest.get("checked_at"),
            "replayed": True,
        }
    if latest.get("status") == "refuted" and latest.get("countermodel_path"):
        return {
            "id": latest["id"],
            "status": "refuted",
            "countermodel_path": latest["countermodel_path"],
            "checked_at": latest.get("checked_at"),
            "replayed": True,
        }

    checker_kind = latest["checker_kind"]
    checker = checker_dispatch.get(checker_kind)
    if checker is None:
        raise ProofObligationValidationError(f"no checker for kind {checker_kind!r}")

    result = checker(dict(latest))
    status = result.get("status")
    if status == "proved":
        return _record_discharge(layout, latest, result, checked_at)
    if status == "disproved":
        return _record_refutation(layout, latest, result, checked_at)
    raise ProofObligationValidationError(
        f"checker {checker_kind!r} returned unsupported status {status!r}"
    )


def _record_discharge(
    layout: WorkspaceLayout, obligation: dict, result: dict, checked_at: str
) -> dict:
    assert_transition_allowed(obligation["status"], "discharged")
    artifact_path = (
        layout.root / "graph" / "proof-artifacts" / f"{obligation['id']}.json"
    )
    artifact_payload = result.get("artifact", {})
    _write_json(artifact_path, artifact_payload)
    artifact_rel = _relative_workspace_path(artifact_path, layout)

    artifact_record = {
        "id": f"artifact-{obligation['id']}",
        "obligation_id": obligation["id"],
        "artifact_path": artifact_rel,
        "checker_kind": obligation["checker_kind"],
        "checked_at": checked_at,
        "status": "discharged",
    }
    validate_verification_artifact(artifact_record)
    _append_jsonl(_artifact_ledger_path(layout), artifact_record)

    updated = dict(obligation)
    updated.update(
        {
            "status": "discharged",
            "artifact_path": artifact_rel,
            "checked_at": checked_at,
        }
    )
    validate_proof_obligation(updated)
    _append_jsonl(_obligation_path(layout), updated)
    return {
        "id": updated["id"],
        "status": "discharged",
        "artifact_path": artifact_rel,
        "checked_at": checked_at,
        "replayed": False,
    }


def _record_refutation(
    layout: WorkspaceLayout, obligation: dict, result: dict, checked_at: str
) -> dict:
    assert_transition_allowed(obligation["status"], "refuted")
    countermodel_path = (
        layout.root / "graph" / "countermodels" / f"{obligation['id']}.json"
    )
    countermodel = result.get("countermodel", {})
    _write_json(countermodel_path, countermodel)
    countermodel_rel = _relative_workspace_path(countermodel_path, layout)

    updated = dict(obligation)
    updated.update(
        {
            "status": "refuted",
            "countermodel_path": countermodel_rel,
            "checked_at": checked_at,
        }
    )
    validate_proof_obligation(updated)
    _append_jsonl(_obligation_path(layout), updated)
    return {
        "id": updated["id"],
        "status": "refuted",
        "countermodel_path": countermodel_rel,
        "checked_at": checked_at,
        "replayed": False,
    }


_NUMBER_RE = re.compile(r"(?<![\w.])\d+(?:\.\d+)?(?!\w)")
_UNIT_RE = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:%|mg|g|kg|mm|cm|m|km|ms|s|min|h|hr|mol|ml|l)\b",
    re.IGNORECASE,
)
_UNCERTAINTY_RE = re.compile(
    r"(\+/-|\u00b1|\bci\b|\bconfidence interval\b|\bcredible interval\b|\bsd\b|\bse\b)",
    re.IGNORECASE,
)
_STATS_RE = re.compile(
    r"(\bp\s*[<=>]\s*0?\.\d+|\bn\s*=\s*\d+|\bsample\b|\bcohort\b|\b95%\s*ci\b)",
    re.IGNORECASE,
)


def check_scientific_claim(record: dict) -> list[dict]:
    """Return deterministic reporting flags for a scientific claim."""
    claim_id = record.get("claim_id", "")
    text = record.get("canonical_text", "")
    if not _NUMBER_RE.search(text):
        return []

    out: list[dict] = []
    if not _UNIT_RE.search(text):
        out.append(
            {
                "claim_id": claim_id,
                "class": "scientific-claim-missing-units",
                "checker_kind": "units",
                "detail": "numeric scientific claim lacks an explicit unit",
            }
        )
    if not (_UNCERTAINTY_RE.search(text) and _STATS_RE.search(text)):
        out.append(
            {
                "claim_id": claim_id,
                "class": "statistical-claim-underreported",
                "checker_kind": "stats-report",
                "detail": "numeric scientific claim lacks uncertainty or statistical reporting",
            }
        )
    return out
