"""Stance derivation: (rule, school) -> :supports | :contradicts | :silent | :extends.

Charter override wins. Otherwise count intersection between the rule's
supporting/contradicting docs and the school's members.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from ._schools import School
from ._config import GovernanceConfig


class Stance(str, Enum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    SILENT = "silent"
    EXTENDS = "extends"


@dataclass(frozen=True)
class RuleEvidence:
    rule_id: str
    supporting_docs: list[str] = field(default_factory=list)
    contradicting_docs: list[str] = field(default_factory=list)
    supporting_atoms: list[str] = field(default_factory=list)
    contradicting_atoms: list[str] = field(default_factory=list)


def derive_stance(
    school: School,
    evidence: RuleEvidence,
    config: GovernanceConfig,
) -> Stance:
    # 1. Charter override first.
    if evidence.rule_id in school.canonical_asserts:
        return Stance.SUPPORTS
    if evidence.rule_id in school.canonical_rejects:
        return Stance.CONTRADICTS

    # 2. Atom-inferred from doc-membership intersection.
    member_set = set(school.members)
    sup = [d for d in evidence.supporting_docs if d in member_set]
    con = [d for d in evidence.contradicting_docs if d in member_set]

    if len(sup) >= config.supports_min_docs and len(con) == 0:
        return Stance.SUPPORTS
    if len(sup) == 0 and len(con) >= config.contradicts_min_docs:
        return Stance.CONTRADICTS
    if len(sup) > 0 and len(con) == 0:
        return Stance.EXTENDS
    return Stance.SILENT
