# targets/base.py
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from engine.graph import WeaveGraph


@dataclass(frozen=True)
class Slot:
    name: str
    required: bool = False


@dataclass
class GateResult:
    passed: bool
    mechanical: dict
    notes: list = field(default_factory=list)


class Target(ABC):
    """A goal-type adapter. The engine is goal-agnostic and calls only this."""

    name: str
    depth: str          # "deep" | "shallow"
    prose_policy: str   # e.g. "russellian-style" | "none"

    @abstractmethod
    def plan_template(self, goal: dict) -> list[Slot]: ...

    @abstractmethod
    def role_vocabulary(self) -> tuple[str, ...]: ...

    @abstractmethod
    def order_objective(self, seq: list[str], graph: WeaveGraph, goal: dict) -> float: ...

    @abstractmethod
    def gate_hook(self, artifacts: dict) -> GateResult: ...


REGISTRY: dict[str, Target] = {}


def register(target: Target) -> None:
    REGISTRY[target.name] = target


def get_target(name: str) -> Target:
    if name not in REGISTRY:
        raise KeyError(f"unknown target '{name}'; registered: {sorted(REGISTRY)}")
    return REGISTRY[name]
