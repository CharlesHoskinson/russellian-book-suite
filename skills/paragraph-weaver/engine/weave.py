"""Bridge and seam-edit validation (deterministic guards).

validate_bridge enforces the closed-vocabulary discipline: a bridge may name only
entities present in the two flanking paragraphs (no invented content) and must
assert one relation from assets/connectives.json. validate_seam_edit enforces
that a seam edit preserves each paragraph's load-bearing tokens (so a "light"
edit cannot delete the entity that bound the paragraph). Body-contradiction
checking is deferred to v1.5 (needs NLI) and is agent-judged in v1.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from scripts.features import extract_entities

_ASSET = Path(__file__).resolve().parents[1] / "assets" / "connectives.json"


def load_relations() -> set[str]:
    return set(json.loads(_ASSET.read_text(encoding="utf-8"))["relations"])


@dataclass
class BridgeValidation:
    ok: bool
    reasons: list[str] = field(default_factory=list)


@dataclass
class SeamValidation:
    ok: bool
    missing: list[str] = field(default_factory=list)


def validate_bridge(
    bridge_text: str,
    left_entities: tuple[str, ...],
    right_entities: tuple[str, ...],
    relation: str,
    allowed_relations: set[str] | None = None,
) -> BridgeValidation:
    allowed = allowed_relations if allowed_relations is not None else load_relations()
    reasons: list[str] = []
    if relation not in allowed:
        reasons.append(f"relation '{relation}' not in allowed set {sorted(allowed)}")
    flanking = set(left_entities) | set(right_entities)
    new = set(extract_entities(bridge_text)) - flanking
    if new:
        reasons.append(f"bridge introduces entities absent from neighbours: {sorted(new)}")
    return BridgeValidation(ok=not reasons, reasons=reasons)


def validate_seam_edit(edited_sentence: str, load_bearing_tokens: list[str]) -> SeamValidation:
    low = edited_sentence.lower()
    missing = [t for t in load_bearing_tokens if t.lower() not in low]
    return SeamValidation(ok=not missing, missing=missing)
