# paragraph-weaver Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the deterministic substrate of a goal-directed paragraph-threading skill (`paragraph-weaver`) that reorders a paragraph collection, validates bridges/seams, and gates the result — with the agent-in-the-loop supplying judgment per the suite's `russellian-style` pattern.

**Architecture:** Pure-Python deterministic engine (graph model, entity extraction, cycle detection, feasibility refusal, ordering search, bridge/seam validation, gate scoring, provenance rendering) plus a pluggable `Target` interface. v1 ships one deep target (`argument`) and two interface-compliant shallow stubs (`emotion`, `narrative`). The agent that runs the skill produces goal-specs, role tags, precedence edges, bridges and seam edits as *inputs* to these deterministic functions; the gate scores frozen artifacts so acceptance is reproducible.

**Tech Stack:** Python ≥3.11, stdlib only (no NLP deps in v1), pytest. Skill lives at `skills/paragraph-weaver/`.

**Spec:** `docs/superpowers/specs/2026-05-30-paragraph-weaver-design.md`

---

## File Structure

```
skills/paragraph-weaver/
  pyproject.toml                 # pytest + packaging config
  conftest.py                    # inserts skill root on sys.path
  skill_api.py                   # public surface + API_VERSION
  SKILL.md                       # agent-in-the-loop orchestration doctrine
  engine/
    __init__.py
    graph.py                     # Node, Edge, WeaveGraph, content hashing
    cycles.py                    # find_cycles (Tarjan SCC) on precedence
    feasibility.py               # check_feasibility (the refusal gate)
    order.py                     # topological ordering + objective minimization
    weave.py                     # validate_bridge, validate_seam_edit
    gate.py                      # no_silent_drops, bridge_load_ratio, score_gate
    report.py                    # Segment, render_provenance, render_clean
  targets/
    __init__.py
    base.py                      # Slot, GateResult, Target ABC, registry
    argument.py                  # deep target
    emotion.py                   # shallow stub
    narrative.py                 # shallow stub
  scripts/
    __init__.py
    features.py                  # extract_entities (deterministic keyword proxy)
  assets/
    connectives.json             # allowed discourse-relation set
    target-registry.json         # declared targets + depth
  tests/
    test_scaffold.py
    test_graph.py
    test_features.py
    test_cycles.py
    test_targets_base.py
    test_argument.py
    test_stubs.py
    test_feasibility.py
    test_order.py
    test_weave.py
    test_gate.py
    test_report.py
    test_skill_api.py
    test_end_to_end.py
```

Each module has one responsibility. The agent-driven stages (goal-spec extraction, role tagging, bridge writing, seam editing) are *documented in SKILL.md*, not implemented in Python — Python only owns the deterministic, testable substrate.

---

### Task 1: Skill scaffold

**Files:**
- Create: `skills/paragraph-weaver/pyproject.toml`
- Create: `skills/paragraph-weaver/conftest.py`
- Create: `skills/paragraph-weaver/engine/__init__.py`
- Create: `skills/paragraph-weaver/targets/__init__.py`
- Create: `skills/paragraph-weaver/scripts/__init__.py`
- Test: `skills/paragraph-weaver/tests/test_scaffold.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_scaffold.py
"""Scaffold smoke test: packages import from the skill root."""
from __future__ import annotations


def test_engine_package_importable():
    import engine  # noqa: F401
    import targets  # noqa: F401
    import scripts  # noqa: F401
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest skills/paragraph-weaver/tests/test_scaffold.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'engine'` (conftest/packages not present yet).

- [ ] **Step 3: Create the scaffold files**

```toml
# pyproject.toml
[project]
name = "paragraph-weaver"
version = "0.1.0"
description = "Goal-directed paragraph threading: reorder + bridge + seam-edit toward argument/emotion/narrative"
requires-python = ">=3.11"
license = { text = "MIT" }
dependencies = []

[project.optional-dependencies]
dev = ["pytest>=8.0,<9.0"]
ci = ["pytest>=8.0,<9.0"]

[tool.setuptools]
packages = ["engine", "targets", "scripts"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra -q"

[build-system]
requires = ["setuptools>=61"]
build-backend = "setuptools.build_meta"
```

```python
# conftest.py
import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
```

```python
# engine/__init__.py
```

```python
# targets/__init__.py
```

```python
# scripts/__init__.py
```

(The three `__init__.py` files are empty.)

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest skills/paragraph-weaver/tests/test_scaffold.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/paragraph-weaver/pyproject.toml skills/paragraph-weaver/conftest.py \
  skills/paragraph-weaver/engine/__init__.py skills/paragraph-weaver/targets/__init__.py \
  skills/paragraph-weaver/scripts/__init__.py skills/paragraph-weaver/tests/test_scaffold.py
git commit -m "scaffold(paragraph-weaver): skill package layout + pytest config"
```

---

### Task 2: Graph model with content hashing

**Files:**
- Create: `skills/paragraph-weaver/engine/graph.py`
- Test: `skills/paragraph-weaver/tests/test_graph.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_graph.py
from __future__ import annotations

from engine.graph import Node, Edge, WeaveGraph


def _graph():
    return WeaveGraph(
        nodes=[
            Node(id="p2", text="Second.", entities=("beta",), role="premise", bound_slot="evidence"),
            Node(id="p1", text="First.", entities=("alpha",), role="claim", bound_slot="thesis"),
        ],
        edges=[Edge(src="p1", dst="p2")],
    )


def test_node_lookup():
    g = _graph()
    assert g.node("p1").role == "claim"


def test_json_round_trip_preserves_data():
    g = _graph()
    g2 = WeaveGraph.from_json(g.to_json())
    assert g2.node("p2").entities == ("beta",)
    assert g2.edges[0].src == "p1"


def test_content_hash_is_order_independent_and_stable():
    g = _graph()
    # Reversed node order, same content → identical hash (canonical serialization).
    g_rev = WeaveGraph(nodes=list(reversed(g.nodes)), edges=list(g.edges))
    assert g.content_hash() == g_rev.content_hash()
    # Changing content changes the hash.
    g3 = WeaveGraph(nodes=g.nodes, edges=[Edge(src="p2", dst="p1")])
    assert g3.content_hash() != g.content_hash()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest skills/paragraph-weaver/tests/test_graph.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'engine.graph'`.

- [ ] **Step 3: Write the implementation**

```python
# engine/graph.py
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Literal

Provenance = Literal["py", "agent", "human"]


@dataclass(frozen=True)
class Node:
    id: str
    text: str
    entities: tuple[str, ...] = ()        # features_computed
    role: str | None = None               # features_judged
    rationale: str | None = None          # features_judged justification
    provenance: Provenance = "agent"
    bound_slot: str | None = None
    order_index: int | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "text": self.text,
            "entities": list(self.entities),
            "role": self.role,
            "rationale": self.rationale,
            "provenance": self.provenance,
            "bound_slot": self.bound_slot,
            "order_index": self.order_index,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Node":
        return cls(
            id=d["id"],
            text=d["text"],
            entities=tuple(d.get("entities", [])),
            role=d.get("role"),
            rationale=d.get("rationale"),
            provenance=d.get("provenance", "agent"),
            bound_slot=d.get("bound_slot"),
            order_index=d.get("order_index"),
        )


@dataclass(frozen=True)
class Edge:
    src: str
    dst: str
    kind: Literal["precedence"] = "precedence"
    rationale: str | None = None

    def to_dict(self) -> dict:
        return {"src": self.src, "dst": self.dst, "kind": self.kind, "rationale": self.rationale}

    @classmethod
    def from_dict(cls, d: dict) -> "Edge":
        return cls(src=d["src"], dst=d["dst"], kind=d.get("kind", "precedence"), rationale=d.get("rationale"))


@dataclass
class WeaveGraph:
    nodes: list[Node]
    edges: list[Edge] = field(default_factory=list)

    def node(self, node_id: str) -> Node:
        for n in self.nodes:
            if n.id == node_id:
                return n
        raise KeyError(node_id)

    def to_dict(self) -> dict:
        return {
            "nodes": [n.to_dict() for n in sorted(self.nodes, key=lambda n: n.id)],
            "edges": [e.to_dict() for e in sorted(self.edges, key=lambda e: (e.src, e.dst, e.kind))],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, ensure_ascii=False)

    @classmethod
    def from_json(cls, s: str) -> "WeaveGraph":
        d = json.loads(s)
        return cls(
            nodes=[Node.from_dict(n) for n in d["nodes"]],
            edges=[Edge.from_dict(e) for e in d.get("edges", [])],
        )

    def content_hash(self) -> str:
        return hashlib.sha256(self.to_json().encode("utf-8")).hexdigest()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest skills/paragraph-weaver/tests/test_graph.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add skills/paragraph-weaver/engine/graph.py skills/paragraph-weaver/tests/test_graph.py
git commit -m "feat(paragraph-weaver): graph model with canonical content hashing"
```

---

### Task 3: Deterministic entity extraction

**Files:**
- Create: `skills/paragraph-weaver/scripts/features.py`
- Test: `skills/paragraph-weaver/tests/test_features.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_features.py
from __future__ import annotations

from scripts.features import extract_entities


def test_extracts_content_words_lowercased_sorted():
    ents = extract_entities("Snails carry a calcareous Shell.")
    assert ents == ("calcareous", "carry", "shell", "snails")


def test_filters_short_words_and_stopwords():
    ents = extract_entities("The shell is on the foot.")
    # "the", "is", "on" dropped (stopword/short); "shell", "foot" kept.
    assert ents == ("foot", "shell")


def test_filters_discourse_connectives():
    # Connectives must not register as entities, else they poison bridge checks.
    ents = extract_entities("Therefore however moreover the spiral.")
    assert ents == ("spiral",)


def test_is_deterministic():
    text = "A spiral shell grows by a logarithmic rule."
    assert extract_entities(text) == extract_entities(text)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest skills/paragraph-weaver/tests/test_features.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.features'`.

- [ ] **Step 3: Write the implementation**

```python
# scripts/features.py
"""Deterministic entity proxy.

v1 uses a coarse keyword extractor (content words ≥4 chars, minus a stopword and
discourse-connective list) rather than an NLP model, to stay stdlib-only and
fully reproducible. This is an entity *proxy* used for overlap-coherence and for
the bridge entity-subset guard, not a real NER. Replacing it with a pinned NER
model is a v1.5 task; the public signature must not change.
"""
from __future__ import annotations

import re

_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "but", "by", "for",
    "from", "had", "has", "have", "in", "into", "is", "it", "its", "of", "on",
    "or", "that", "the", "their", "them", "they", "this", "to", "was", "were",
    "which", "with", "will", "would", "can", "could", "may", "might", "must",
    "not", "no", "so", "than", "then", "there", "these", "those", "such",
}

# Discourse connectives must never count as entities.
_CONNECTIVES = {
    "therefore", "however", "moreover", "thus", "hence", "because", "although",
    "whereas", "consequently", "furthermore", "nevertheless", "accordingly",
    "similarly", "conversely", "indeed", "also", "next", "finally", "first",
    "second", "third", "while", "when", "where", "here", "yet", "still",
}

_DROP = _STOPWORDS | _CONNECTIVES
_WORD = re.compile(r"[A-Za-z][A-Za-z'-]+")


def extract_entities(text: str) -> tuple[str, ...]:
    """Return a sorted tuple of distinct content-word entities (lowercased)."""
    words = (w.lower() for w in _WORD.findall(text))
    keep = {w for w in words if len(w) >= 4 and w not in _DROP}
    return tuple(sorted(keep))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest skills/paragraph-weaver/tests/test_features.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add skills/paragraph-weaver/scripts/features.py skills/paragraph-weaver/tests/test_features.py
git commit -m "feat(paragraph-weaver): deterministic entity proxy extractor"
```

---

### Task 4: Cycle detection on precedence edges

**Files:**
- Create: `skills/paragraph-weaver/engine/cycles.py`
- Test: `skills/paragraph-weaver/tests/test_cycles.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cycles.py
from __future__ import annotations

from engine.graph import Node, Edge, WeaveGraph
from engine.cycles import find_cycles


def _g(edges):
    nodes = [Node(id=x, text=x) for x in ("a", "b", "c")]
    return WeaveGraph(nodes=nodes, edges=[Edge(src=s, dst=d) for s, d in edges])


def test_acyclic_returns_no_cycles():
    assert find_cycles(_g([("a", "b"), ("b", "c")])) == []


def test_two_cycle_detected():
    cycles = find_cycles(_g([("a", "b"), ("b", "a")]))
    assert len(cycles) == 1
    assert set(cycles[0]) == {"a", "b"}


def test_self_loop_detected():
    cycles = find_cycles(_g([("a", "a")]))
    assert cycles == [["a"]]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest skills/paragraph-weaver/tests/test_cycles.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'engine.cycles'`.

- [ ] **Step 3: Write the implementation**

```python
# engine/cycles.py
"""Tarjan strongly-connected-components cycle detection over precedence edges.

A precedence edge (src -> dst) means src must appear before dst. Any SCC with
more than one node, or any self-loop, is a cycle that makes the precedence
constraint set infeasible. Per the spec, the engine REPORTS cycles for
adjudication rather than crashing; callers demote the weakest edge in the SCC.
"""
from __future__ import annotations

from engine.graph import WeaveGraph


def find_cycles(graph: WeaveGraph) -> list[list[str]]:
    adj: dict[str, list[str]] = {n.id: [] for n in graph.nodes}
    self_loops: list[str] = []
    for e in graph.edges:
        if e.kind != "precedence":
            continue
        if e.src == e.dst:
            self_loops.append(e.src)
            continue
        adj.setdefault(e.src, []).append(e.dst)
        adj.setdefault(e.dst, [])

    index: dict[str, int] = {}
    low: dict[str, int] = {}
    on_stack: dict[str, bool] = {}
    stack: list[str] = []
    counter = [0]
    cycles: list[list[str]] = []

    def strongconnect(v: str) -> None:
        index[v] = low[v] = counter[0]
        counter[0] += 1
        stack.append(v)
        on_stack[v] = True
        for w in adj.get(v, []):
            if w not in index:
                strongconnect(w)
                low[v] = min(low[v], low[w])
            elif on_stack.get(w):
                low[v] = min(low[v], index[w])
        if low[v] == index[v]:
            comp = []
            while True:
                w = stack.pop()
                on_stack[w] = False
                comp.append(w)
                if w == v:
                    break
            if len(comp) > 1:
                cycles.append(sorted(comp))

    for n in graph.nodes:
        if n.id not in index:
            strongconnect(n.id)

    for node_id in self_loops:
        cycles.append([node_id])
    return cycles
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest skills/paragraph-weaver/tests/test_cycles.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add skills/paragraph-weaver/engine/cycles.py skills/paragraph-weaver/tests/test_cycles.py
git commit -m "feat(paragraph-weaver): Tarjan cycle detection on precedence edges"
```

---

### Task 5: Target interface, slots, registry

**Files:**
- Create: `skills/paragraph-weaver/targets/base.py`
- Test: `skills/paragraph-weaver/tests/test_targets_base.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_targets_base.py
from __future__ import annotations

import pytest

from targets.base import Slot, GateResult, Target, register, get_target, REGISTRY


def test_slot_defaults_not_required():
    assert Slot("thesis").required is False
    assert Slot("thesis", required=True).required is True


def test_register_and_get():
    class Dummy(Target):
        name = "dummy"
        depth = "shallow"
        prose_policy = "none"

        def plan_template(self, goal):
            return [Slot("only")]

        def role_vocabulary(self):
            return ("x",)

        def order_objective(self, seq, graph, goal):
            return 0.0

        def gate_hook(self, artifacts):
            return GateResult(passed=True, mechanical={}, notes=[])

    register(Dummy())
    assert get_target("dummy").depth == "shallow"
    REGISTRY.pop("dummy")


def test_get_missing_raises():
    with pytest.raises(KeyError):
        get_target("nope")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest skills/paragraph-weaver/tests/test_targets_base.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'targets.base'`.

- [ ] **Step 3: Write the implementation**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest skills/paragraph-weaver/tests/test_targets_base.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add skills/paragraph-weaver/targets/base.py skills/paragraph-weaver/tests/test_targets_base.py
git commit -m "feat(paragraph-weaver): Target interface, Slot, GateResult, registry"
```

---

### Task 6: Argument target (deep)

**Files:**
- Create: `skills/paragraph-weaver/targets/argument.py`
- Test: `skills/paragraph-weaver/tests/test_argument.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_argument.py
from __future__ import annotations

from engine.graph import Node, WeaveGraph
from targets.argument import ArgumentTarget


def _graph():
    return WeaveGraph(nodes=[
        Node(id="A", text="Thesis.", role="claim", bound_slot="thesis"),
        Node(id="B", text="Evidence.", role="premise", bound_slot="evidence"),
        Node(id="C", text="Conclusion.", role="conclusion", bound_slot="conclusion"),
    ])


def test_plan_template_has_required_thesis_and_conclusion():
    slots = ArgumentTarget().plan_template({})
    by_name = {s.name: s for s in slots}
    assert by_name["thesis"].required and by_name["conclusion"].required
    assert by_name["concession"].required is False


def test_in_slot_order_beats_out_of_order():
    t = ArgumentTarget()
    g = _graph()
    in_order = t.order_objective(["A", "B", "C"], g, {})
    out_order = t.order_objective(["C", "A", "B"], g, {})
    assert in_order < out_order


def test_depth_and_prose_policy():
    t = ArgumentTarget()
    assert t.depth == "deep"
    assert t.prose_policy == "russellian-style"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest skills/paragraph-weaver/tests/test_argument.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'targets.argument'`.

- [ ] **Step 3: Write the implementation**

```python
# targets/argument.py
"""Deep target: thread paragraphs toward a thesis (dispositio order).

order_objective is a soft penalty (lower = better):
  * slot-order conformance — penalize each paragraph whose planned slot rank
    falls before an already-placed higher slot (inversions vs the plan order).
  * edge-loading — penalize a strong paragraph (role claim/conclusion) landing in
    the middle third, per the persuasion-ordering literature (climax/anticlimax,
    never pyramidal). This is a SOFT penalty, never a hard constraint.
"""
from __future__ import annotations

from engine.graph import WeaveGraph
from engine.gate import score_gate
from targets.base import Slot, GateResult, Target, register

_PLAN = [
    Slot("thesis", required=True),
    Slot("evidence", required=True),
    Slot("concession", required=False),
    Slot("rebuttal", required=False),
    Slot("conclusion", required=True),
]
_STRONG_ROLES = {"claim", "conclusion"}


class ArgumentTarget(Target):
    name = "argument"
    depth = "deep"
    prose_policy = "russellian-style"

    def plan_template(self, goal: dict) -> list[Slot]:
        return list(_PLAN)

    def role_vocabulary(self) -> tuple[str, ...]:
        return ("claim", "premise", "warrant", "rebuttal", "conclusion")

    def order_objective(self, seq: list[str], graph: WeaveGraph, goal: dict) -> float:
        nodes = {n.id: n for n in graph.nodes}
        rank = {s.name: i for i, s in enumerate(_PLAN)}
        miss = len(_PLAN)
        penalty = 0.0
        highest = -1
        for nid in seq:
            r = rank.get(nodes[nid].bound_slot, miss)
            if r < highest:
                penalty += 1.0
            highest = max(highest, r)
        length = len(seq)
        for i, nid in enumerate(seq):
            if nodes[nid].role in _STRONG_ROLES and length:
                pos = i / length
                if 1 / 3 <= pos < 2 / 3:
                    penalty += 0.5
        return penalty

    def gate_hook(self, artifacts: dict) -> GateResult:
        return score_gate(artifacts)


register(ArgumentTarget())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest skills/paragraph-weaver/tests/test_argument.py -v`
Expected: PASS (3 tests). (This import pulls in `engine.gate`, built in Task 11; if running tasks out of order, build Task 11 first. In sequence, `engine.gate` does not yet exist — so write a temporary shim is NOT allowed; this task depends on Task 11. **Reorder note:** implement Task 11 before Task 6 if executing strictly top-to-bottom is not possible. The committed order below lists gate before argument.)

> **Dependency:** `targets/argument.py` imports `engine.gate.score_gate`. Execute **Task 11 (gate) before Task 6** — or accept that the argument test fails on the gate import until Task 11 lands. The plan is written so a strict executor builds gate first; see the dependency line in Task 11.

- [ ] **Step 5: Commit**

```bash
git add skills/paragraph-weaver/targets/argument.py skills/paragraph-weaver/tests/test_argument.py
git commit -m "feat(paragraph-weaver): deep argument target with dispositio order objective"
```

---

### Task 7: Shallow stubs (emotion, narrative)

**Files:**
- Create: `skills/paragraph-weaver/targets/emotion.py`
- Create: `skills/paragraph-weaver/targets/narrative.py`
- Test: `skills/paragraph-weaver/tests/test_stubs.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_stubs.py
from __future__ import annotations

from engine.graph import WeaveGraph
from targets.emotion import EmotionTarget
from targets.narrative import NarrativeTarget


def test_emotion_is_shallow_and_warns():
    t = EmotionTarget()
    assert t.depth == "shallow"
    res = t.gate_hook({})
    assert res.passed is True
    assert any("SHALLOW" in n for n in res.notes)


def test_narrative_is_shallow_and_warns():
    t = NarrativeTarget()
    assert t.depth == "shallow"
    res = t.gate_hook({})
    assert any("SHALLOW" in n for n in res.notes)


def test_stub_order_objective_is_trivial():
    t = EmotionTarget()
    assert t.order_objective(["x", "y"], WeaveGraph(nodes=[]), {}) == 0.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest skills/paragraph-weaver/tests/test_stubs.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'targets.emotion'`.

- [ ] **Step 3: Write the implementation**

```python
# targets/emotion.py
"""SHALLOW stub: proves the Target interface for an emotional-arc goal.

v1 carries no valence pipeline; order_objective is trivial and the gate emits a
not-yet-deep warning. The deep valence-curve implementation is a v1.5 task.
"""
from __future__ import annotations

from engine.graph import WeaveGraph
from targets.base import Slot, GateResult, Target, register


class EmotionTarget(Target):
    name = "emotion"
    depth = "shallow"
    prose_policy = "none"

    def plan_template(self, goal: dict) -> list[Slot]:
        return [Slot("establish", required=True), Slot("tension"), Slot("resolve", required=True)]

    def role_vocabulary(self) -> tuple[str, ...]:
        return ("low", "neutral", "high")

    def order_objective(self, seq: list[str], graph: WeaveGraph, goal: dict) -> float:
        return 0.0

    def gate_hook(self, artifacts: dict) -> GateResult:
        return GateResult(passed=True, mechanical={}, notes=["SHALLOW: emotion target is not-yet-deep in v1"])


register(EmotionTarget())
```

```python
# targets/narrative.py
"""SHALLOW stub: proves the Target interface for a story-arc goal.

v1 carries no causal-DAG or tension model; order_objective is trivial and the
gate emits a not-yet-deep warning. The deep implementation is a v2 task.
"""
from __future__ import annotations

from engine.graph import WeaveGraph
from targets.base import Slot, GateResult, Target, register


class NarrativeTarget(Target):
    name = "narrative"
    depth = "shallow"
    prose_policy = "none"

    def plan_template(self, goal: dict) -> list[Slot]:
        return [
            Slot("exposition", required=True),
            Slot("rising"),
            Slot("climax", required=True),
            Slot("falling"),
            Slot("close", required=True),
        ]

    def role_vocabulary(self) -> tuple[str, ...]:
        return ("setup", "develop", "turn", "resolve")

    def order_objective(self, seq: list[str], graph: WeaveGraph, goal: dict) -> float:
        return 0.0

    def gate_hook(self, artifacts: dict) -> GateResult:
        return GateResult(passed=True, mechanical={}, notes=["SHALLOW: narrative target is not-yet-deep in v1"])


register(NarrativeTarget())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest skills/paragraph-weaver/tests/test_stubs.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add skills/paragraph-weaver/targets/emotion.py skills/paragraph-weaver/targets/narrative.py \
  skills/paragraph-weaver/tests/test_stubs.py
git commit -m "feat(paragraph-weaver): emotion + narrative shallow stub targets"
```

---

### Task 8: Feasibility gate (the refusal)

**Files:**
- Create: `skills/paragraph-weaver/engine/feasibility.py`
- Test: `skills/paragraph-weaver/tests/test_feasibility.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_feasibility.py
from __future__ import annotations

from engine.graph import Node, WeaveGraph
from engine.feasibility import check_feasibility
from targets.base import Slot


_SLOTS = [Slot("thesis", required=True), Slot("evidence", required=True), Slot("aside")]


def test_passes_when_required_slots_filled_and_connected():
    g = WeaveGraph(nodes=[
        Node(id="A", text="x", entities=("shell",), bound_slot="thesis"),
        Node(id="B", text="y", entities=("shell", "foot"), bound_slot="evidence"),
    ])
    res = check_feasibility(g, _SLOTS)
    assert res.ok and res.reasons == []


def test_refuses_when_required_slot_unfilled():
    g = WeaveGraph(nodes=[Node(id="A", text="x", entities=("shell",), bound_slot="thesis")])
    res = check_feasibility(g, _SLOTS)
    assert not res.ok
    assert any("evidence" in r for r in res.reasons)


def test_refuses_when_entity_graph_disconnected():
    g = WeaveGraph(nodes=[
        Node(id="A", text="x", entities=("shell",), bound_slot="thesis"),
        Node(id="B", text="y", entities=("planet",), bound_slot="evidence"),
    ])
    res = check_feasibility(g, _SLOTS)
    assert not res.ok
    assert any("disconnected" in r for r in res.reasons)


def test_refuses_when_too_many_unbound():
    g = WeaveGraph(nodes=[
        Node(id="A", text="x", entities=("shell",), bound_slot="thesis"),
        Node(id="B", text="y", entities=("shell",), bound_slot="evidence"),
        Node(id="C", text="z", entities=("shell",), bound_slot=None),
        Node(id="D", text="w", entities=("shell",), bound_slot=None),
        Node(id="E", text="v", entities=("shell",), bound_slot=None),
    ])
    res = check_feasibility(g, _SLOTS, max_unbound_fraction=0.5)
    assert not res.ok
    assert any("unbound" in r for r in res.reasons)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest skills/paragraph-weaver/tests/test_feasibility.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'engine.feasibility'`.

- [ ] **Step 3: Write the implementation**

```python
# engine/feasibility.py
"""Feasibility gate: the engine's ability to refuse.

Run AFTER bind, BEFORE order. If required slots are unfilled, too many paragraphs
are off-goal, or the entity graph is disconnected, the engine stops and emits a
diagnosis instead of threading garbage.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from engine.graph import WeaveGraph


@dataclass
class FeasibilityResult:
    ok: bool
    reasons: list[str] = field(default_factory=list)


def _connected(graph: WeaveGraph) -> bool:
    ids = [n.id for n in graph.nodes]
    if len(ids) <= 1:
        return True
    parent = {i: i for i in ids}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        parent[find(a)] = find(b)

    by_entity: dict[str, list[str]] = {}
    for n in graph.nodes:
        for e in n.entities:
            by_entity.setdefault(e, []).append(n.id)
    for members in by_entity.values():
        for other in members[1:]:
            union(members[0], other)
    roots = {find(i) for i in ids}
    return len(roots) == 1


def check_feasibility(
    graph: WeaveGraph,
    slots,
    *,
    max_unbound_fraction: float = 0.5,
    require_connected: bool = True,
) -> FeasibilityResult:
    reasons: list[str] = []

    bound = {n.bound_slot for n in graph.nodes if n.bound_slot}
    for slot in slots:
        if getattr(slot, "required", False) and slot.name not in bound:
            reasons.append(f"required slot '{slot.name}' unfilled")

    total = len(graph.nodes)
    if total:
        unbound = sum(1 for n in graph.nodes if not n.bound_slot)
        frac = unbound / total
        if frac > max_unbound_fraction:
            reasons.append(f"too many unbound (off-goal) paragraphs: {unbound}/{total} > {max_unbound_fraction:.0%}")

    if require_connected and not _connected(graph):
        reasons.append("entity graph is disconnected (no shared-entity path between some paragraphs)")

    return FeasibilityResult(ok=not reasons, reasons=reasons)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest skills/paragraph-weaver/tests/test_feasibility.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add skills/paragraph-weaver/engine/feasibility.py skills/paragraph-weaver/tests/test_feasibility.py
git commit -m "feat(paragraph-weaver): feasibility refusal gate (slots, connectivity, off-goal)"
```

---

### Task 9: Ordering search

**Files:**
- Create: `skills/paragraph-weaver/engine/order.py`
- Test: `skills/paragraph-weaver/tests/test_order.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_order.py
from __future__ import annotations

from engine.graph import Node, Edge, WeaveGraph
from engine.order import all_topological_orders, order_paragraphs


def _g(edges):
    nodes = [Node(id=x, text=x) for x in ("a", "b", "c")]
    return WeaveGraph(nodes=nodes, edges=[Edge(src=s, dst=d) for s, d in edges])


def test_topological_orders_respect_precedence():
    orders = all_topological_orders(["a", "b", "c"], [Edge(src="a", dst="b")])
    for o in orders:
        assert o.index("a") < o.index("b")
    # No order may violate the single precedence edge.
    assert ["b", "a", "c"] not in orders


def test_order_paragraphs_minimizes_objective_subject_to_precedence():
    g = _g([("a", "b")])  # a before b is hard.

    # Objective prefers c first; ties broken by lexical order via stable min.
    def objective(seq):
        return 0.0 if seq[0] == "c" else 1.0

    result = order_paragraphs(g, objective)
    assert result[0] == "c"
    assert result.index("a") < result.index("b")


def test_large_graph_falls_back_to_single_topo_order():
    nodes = [Node(id=str(i), text=str(i)) for i in range(12)]
    g = WeaveGraph(nodes=nodes, edges=[])
    result = order_paragraphs(g, lambda seq: 0.0, max_exact=9)
    assert sorted(result) == sorted(n.id for n in nodes)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest skills/paragraph-weaver/tests/test_order.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'engine.order'`.

- [ ] **Step 3: Write the implementation**

```python
# engine/order.py
"""Ordering search.

Exactly one HARD constraint: validated-acyclic precedence (src before dst). The
target's order_objective supplies SOFT penalties (slot order, edge-loading). At
demo scale (<= max_exact nodes) we enumerate every linear extension of the
precedence DAG and pick the objective-minimizing one. Above that we fall back to
one deterministic topological order to stay tractable.

Precondition: the graph's precedence edges are acyclic (callers run
engine.cycles.find_cycles first and resolve cycles). A cyclic graph yields no
topological order and raises ValueError.
"""
from __future__ import annotations

from typing import Callable

from engine.graph import Edge, WeaveGraph


def all_topological_orders(node_ids: list[str], edges: list[Edge]) -> list[list[str]]:
    preds: dict[str, set[str]] = {n: set() for n in node_ids}
    for e in edges:
        if e.kind == "precedence" and e.src != e.dst:
            preds.setdefault(e.dst, set()).add(e.src)
            preds.setdefault(e.src, set())
    results: list[list[str]] = []

    def backtrack(order: list[str], remaining: set[str]) -> None:
        if not remaining:
            results.append(list(order))
            return
        placed = set(order)
        for n in sorted(remaining):
            if preds.get(n, set()) <= placed:
                order.append(n)
                backtrack(order, remaining - {n})
                order.pop()

    backtrack([], set(node_ids))
    return results


def _single_topo_order(node_ids: list[str], edges: list[Edge]) -> list[str]:
    preds: dict[str, set[str]] = {n: set() for n in node_ids}
    for e in edges:
        if e.kind == "precedence" and e.src != e.dst:
            preds.setdefault(e.dst, set()).add(e.src)
            preds.setdefault(e.src, set())
    order: list[str] = []
    remaining = set(node_ids)
    while remaining:
        ready = sorted(n for n in remaining if preds.get(n, set()) <= set(order))
        if not ready:
            raise ValueError("precedence edges are cyclic; resolve cycles before ordering")
        order.append(ready[0])
        remaining.discard(ready[0])
    return order


def order_paragraphs(
    graph: WeaveGraph,
    objective: Callable[[list[str]], float],
    *,
    max_exact: int = 9,
) -> list[str]:
    node_ids = [n.id for n in graph.nodes]
    if len(node_ids) <= max_exact:
        orders = all_topological_orders(node_ids, graph.edges)
        if not orders:
            raise ValueError("precedence edges are cyclic; resolve cycles before ordering")
        return min(orders, key=objective)
    return _single_topo_order(node_ids, graph.edges)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest skills/paragraph-weaver/tests/test_order.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add skills/paragraph-weaver/engine/order.py skills/paragraph-weaver/tests/test_order.py
git commit -m "feat(paragraph-weaver): precedence-constrained ordering search"
```

---

### Task 10: Bridge & seam validation

**Files:**
- Create: `skills/paragraph-weaver/engine/weave.py`
- Create: `skills/paragraph-weaver/assets/connectives.json`
- Test: `skills/paragraph-weaver/tests/test_weave.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_weave.py
from __future__ import annotations

from engine.weave import validate_bridge, validate_seam_edit, load_relations


def test_relations_load_from_asset():
    rels = load_relations()
    assert "contrast" in rels and "elaboration" in rels


def test_bridge_ok_when_entities_subset_and_relation_allowed():
    res = validate_bridge(
        "This shell is a spiral.",
        left_entities=("shell", "snails"),
        right_entities=("shell", "spiral"),
        relation="elaboration",
    )
    assert res.ok, res.reasons


def test_bridge_rejected_for_new_entity():
    res = validate_bridge(
        "Therefore octopuses exist.",
        left_entities=("shell",),
        right_entities=("spiral",),
        relation="contrast",
    )
    assert not res.ok
    assert any("octopuses" in r for r in res.reasons)


def test_bridge_rejected_for_unknown_relation():
    res = validate_bridge(
        "This shell is a spiral.",
        left_entities=("shell",),
        right_entities=("spiral",),
        relation="teleportation",
    )
    assert not res.ok
    assert any("relation" in r for r in res.reasons)


def test_seam_edit_ok_when_load_bearing_tokens_survive():
    res = validate_seam_edit("It hardens into a calcareous shell.", load_bearing_tokens=["shell"])
    assert res.ok and res.missing == []


def test_seam_edit_rejected_when_token_deleted():
    res = validate_seam_edit("It simply hardens.", load_bearing_tokens=["shell"])
    assert not res.ok
    assert res.missing == ["shell"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest skills/paragraph-weaver/tests/test_weave.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'engine.weave'`.

- [ ] **Step 3: Write the asset and implementation**

```json
// assets/connectives.json
{
  "relations": [
    "contrast",
    "elaboration",
    "sequence",
    "concession",
    "evidence-of",
    "cause",
    "result",
    "restatement"
  ]
}
```

```python
# engine/weave.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest skills/paragraph-weaver/tests/test_weave.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add skills/paragraph-weaver/engine/weave.py skills/paragraph-weaver/assets/connectives.json \
  skills/paragraph-weaver/tests/test_weave.py
git commit -m "feat(paragraph-weaver): closed-vocabulary bridge + seam-edit validation"
```

---

### Task 11: Gate scoring over frozen artifacts

> **Dependency note:** `targets/argument.py` (Task 6) imports `score_gate` from here. If executing strictly in number order, this task's code must exist before Task 6's test passes. Executors using subagent-driven development: build Task 11 immediately before Task 6, or treat the Task 6 gate-import failure as expected until this lands.

**Files:**
- Create: `skills/paragraph-weaver/engine/gate.py`
- Test: `skills/paragraph-weaver/tests/test_gate.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_gate.py
from __future__ import annotations

from engine.gate import no_silent_drops, bridge_load_ratio, score_gate


def test_no_silent_drops_detects_missing():
    ok, reasons = no_silent_drops(["a", "b", "c"], ["a", "b"])
    assert not ok
    assert any("c" in r for r in reasons)


def test_no_silent_drops_passes_on_equal_sets():
    ok, reasons = no_silent_drops(["a", "b"], ["b", "a"])
    assert ok and reasons == []


def test_bridge_load_ratio():
    assert bridge_load_ratio(900, 100) == 0.1


def test_score_gate_passes_clean_artifacts():
    artifacts = {
        "input_ids": ["a", "b"],
        "output_ids": ["a", "b"],
        "source_chars": 900,
        "bridge_chars": 100,
        "bridge_validity": [True, True],
    }
    res = score_gate(artifacts)
    assert res.passed
    assert res.mechanical["no_silent_drops"] is True


def test_score_gate_fails_on_drop_and_overload():
    artifacts = {
        "input_ids": ["a", "b", "c"],
        "output_ids": ["a"],
        "source_chars": 100,
        "bridge_chars": 900,
        "bridge_validity": [False],
    }
    res = score_gate(artifacts)
    assert not res.passed
    assert res.mechanical["bridge_load_ok"] is False


def test_score_gate_is_deterministic():
    artifacts = {
        "input_ids": ["a"],
        "output_ids": ["a"],
        "source_chars": 50,
        "bridge_chars": 0,
        "bridge_validity": [],
    }
    a = score_gate(artifacts)
    b = score_gate(artifacts)
    assert (a.passed, a.mechanical, a.notes) == (b.passed, b.mechanical, b.notes)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest skills/paragraph-weaver/tests/test_gate.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'engine.gate'`.

- [ ] **Step 3: Write the implementation**

```python
# engine/gate.py
"""Acceptance gate: a pure function of FROZEN artifacts.

Non-determinism lives only in artifact *production* (agent stages). score_gate
re-scores the same artifact dict identically, so a PASS is reproducible. v1 gates
on mechanical, deterministic checks only; coherence and goal-attainment are
agent-judged and recorded in the report, not gated numerically (no calibrated
threshold ships in v1).
"""
from __future__ import annotations

from targets.base import GateResult

DEFAULT_BRIDGE_LOAD_CAP = 0.35


def no_silent_drops(input_ids: list[str], output_ids: list[str]) -> tuple[bool, list[str]]:
    missing = sorted(set(input_ids) - set(output_ids))
    extra = sorted(set(output_ids) - set(input_ids))
    reasons: list[str] = []
    if missing:
        reasons.append(f"dropped paragraphs not in output: {missing}")
    if extra:
        reasons.append(f"output contains unexpected ids: {extra}")
    return (not reasons, reasons)


def bridge_load_ratio(source_chars: int, bridge_chars: int) -> float:
    total = source_chars + bridge_chars
    return 0.0 if total == 0 else bridge_chars / total


def score_gate(artifacts: dict) -> GateResult:
    mechanical: dict = {}
    notes: list[str] = []

    ok_drops, drop_reasons = no_silent_drops(artifacts["input_ids"], artifacts["output_ids"])
    mechanical["no_silent_drops"] = ok_drops
    notes.extend(drop_reasons)

    cap = artifacts.get("bridge_load_cap", DEFAULT_BRIDGE_LOAD_CAP)
    ratio = bridge_load_ratio(artifacts.get("source_chars", 0), artifacts.get("bridge_chars", 0))
    mechanical["bridge_load_ratio"] = ratio
    mechanical["bridge_load_ok"] = ratio <= cap
    if ratio > cap:
        notes.append(f"bridge-load {ratio:.2f} exceeds cap {cap:.2f}")

    validity = artifacts.get("bridge_validity", [])
    mechanical["bridges_grounded"] = all(validity)
    if not all(validity):
        notes.append("one or more bridges failed the entity-subset / relation guard")

    passed = ok_drops and mechanical["bridge_load_ok"] and mechanical["bridges_grounded"]
    return GateResult(passed=passed, mechanical=mechanical, notes=notes)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest skills/paragraph-weaver/tests/test_gate.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add skills/paragraph-weaver/engine/gate.py skills/paragraph-weaver/tests/test_gate.py
git commit -m "feat(paragraph-weaver): deterministic gate scoring over frozen artifacts"
```

---

### Task 12: Provenance rendering

**Files:**
- Create: `skills/paragraph-weaver/engine/report.py`
- Test: `skills/paragraph-weaver/tests/test_report.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_report.py
from __future__ import annotations

from engine.report import Segment, render_provenance, render_clean


def _segments():
    return [
        Segment(kind="source", text="Snails carry a shell."),
        Segment(kind="bridge", text="This shell is a spiral."),
        Segment(kind="seam", text="The spiral grows."),
    ]


def test_provenance_marks_bridge_and_seam():
    md = render_provenance(_segments())
    assert "<!-- bridge -->" in md
    assert "<!-- seam -->" in md
    assert "Snails carry a shell." in md


def test_clean_has_no_marks():
    md = render_clean(_segments())
    assert "<!--" not in md
    assert md.count("\n\n") == 2  # three segments joined by blank lines
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest skills/paragraph-weaver/tests/test_report.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'engine.report'`.

- [ ] **Step 3: Write the implementation**

```python
# engine/report.py
"""Provenance-aware rendering.

The marked render is the default output so the user can see which words are
theirs (source), which are lightly edited (seam), and which are generated
(bridge). Both renders are produced from the same Segment list so marks cannot
drift from the text.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

SegmentKind = Literal["source", "seam", "bridge"]

_MARK = {"source": "", "seam": "<!-- seam -->", "bridge": "<!-- bridge -->"}


@dataclass
class Segment:
    kind: SegmentKind
    text: str


def render_provenance(segments: list[Segment]) -> str:
    parts = []
    for s in segments:
        prefix = _MARK[s.kind]
        parts.append(f"{prefix}{s.text}" if prefix else s.text)
    return "\n\n".join(parts)


def render_clean(segments: list[Segment]) -> str:
    return "\n\n".join(s.text for s in segments)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest skills/paragraph-weaver/tests/test_report.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add skills/paragraph-weaver/engine/report.py skills/paragraph-weaver/tests/test_report.py
git commit -m "feat(paragraph-weaver): provenance + clean rendering from one segment list"
```

---

### Task 13: Public surface (`skill_api.py`) and target registry asset

**Files:**
- Create: `skills/paragraph-weaver/skill_api.py`
- Create: `skills/paragraph-weaver/assets/target-registry.json`
- Test: `skills/paragraph-weaver/tests/test_skill_api.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_skill_api.py
from __future__ import annotations

import skill_api


def test_api_version():
    assert skill_api.API_VERSION == (0, 1)


def test_three_targets_registered():
    names = set(skill_api.REGISTRY)
    assert {"argument", "emotion", "narrative"} <= names


def test_argument_is_deep_others_shallow():
    assert skill_api.get_target("argument").depth == "deep"
    assert skill_api.get_target("emotion").depth == "shallow"
    assert skill_api.get_target("narrative").depth == "shallow"


def test_core_callables_exposed():
    for name in ("extract_entities", "find_cycles", "check_feasibility",
                 "order_paragraphs", "validate_bridge", "validate_seam_edit",
                 "score_gate", "render_provenance", "WeaveGraph"):
        assert hasattr(skill_api, name), name
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest skills/paragraph-weaver/tests/test_skill_api.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'skill_api'`.

- [ ] **Step 3: Write the asset and implementation**

```json
// assets/target-registry.json
{
  "targets": [
    {"name": "argument", "depth": "deep", "prose_policy": "russellian-style"},
    {"name": "emotion", "depth": "shallow", "prose_policy": "none"},
    {"name": "narrative", "depth": "shallow", "prose_policy": "none"}
  ]
}
```

```python
# skill_api.py
"""Public surface for paragraph-weaver.

Importing this module registers the three v1 targets and re-exports the
deterministic engine functions. The agent that runs the skill (see SKILL.md)
calls these to assemble, validate, order, and gate a thread; it supplies the
generative inputs (goal-spec, role tags, precedence edges, bridges, seam edits).
"""
from __future__ import annotations

API_VERSION = (0, 1)

# Register targets (import side effects populate the registry).
import targets.argument  # noqa: F401,E402
import targets.emotion  # noqa: F401,E402
import targets.narrative  # noqa: F401,E402

from targets.base import REGISTRY, Slot, GateResult, Target, get_target, register  # noqa: E402
from engine.graph import Node, Edge, WeaveGraph  # noqa: E402
from engine.cycles import find_cycles  # noqa: E402
from engine.feasibility import check_feasibility, FeasibilityResult  # noqa: E402
from engine.order import order_paragraphs, all_topological_orders  # noqa: E402
from engine.weave import (  # noqa: E402
    validate_bridge, validate_seam_edit, load_relations,
    BridgeValidation, SeamValidation,
)
from engine.gate import no_silent_drops, bridge_load_ratio, score_gate  # noqa: E402
from engine.report import Segment, render_provenance, render_clean  # noqa: E402
from scripts.features import extract_entities  # noqa: E402

__all__ = [
    "API_VERSION",
    "REGISTRY", "Slot", "GateResult", "Target", "get_target", "register",
    "Node", "Edge", "WeaveGraph",
    "find_cycles",
    "check_feasibility", "FeasibilityResult",
    "order_paragraphs", "all_topological_orders",
    "validate_bridge", "validate_seam_edit", "load_relations",
    "BridgeValidation", "SeamValidation",
    "no_silent_drops", "bridge_load_ratio", "score_gate",
    "Segment", "render_provenance", "render_clean",
    "extract_entities",
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest skills/paragraph-weaver/tests/test_skill_api.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add skills/paragraph-weaver/skill_api.py skills/paragraph-weaver/assets/target-registry.json \
  skills/paragraph-weaver/tests/test_skill_api.py
git commit -m "feat(paragraph-weaver): public skill_api surface + target registry asset"
```

---

### Task 14: SKILL.md — agent-in-the-loop doctrine

**Files:**
- Create: `skills/paragraph-weaver/SKILL.md`
- Test: `skills/paragraph-weaver/tests/test_skill_doc.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_skill_doc.py
from __future__ import annotations

from pathlib import Path

DOC = Path(__file__).resolve().parents[1] / "SKILL.md"


def test_skill_doc_exists():
    assert DOC.is_file()


def test_skill_doc_covers_required_sections():
    text = DOC.read_text(encoding="utf-8")
    for needed in (
        "PLAN", "BIND", "FEASIBILITY", "ORDER", "WEAVE", "REVISE",
        "provenance", "argument", "emotion", "narrative",
        "russellian-style", "book-thesis", "book-review",
    ):
        assert needed in text, f"SKILL.md missing: {needed}"


def test_skill_doc_has_frontmatter_name():
    text = DOC.read_text(encoding="utf-8")
    assert text.lstrip().startswith("---")
    assert "name: paragraph-weaver" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest skills/paragraph-weaver/tests/test_skill_doc.py -v`
Expected: FAIL — `assert DOC.is_file()` is False.

- [ ] **Step 3: Write SKILL.md**

```markdown
---
name: paragraph-weaver
description: Thread a collection of existing paragraphs toward a goal (argument, emotion, or narrative) by reordering them, writing bridges, and lightly editing seams. Use when the user has paragraphs and a goal and wants them assembled into a coherent, goal-directed whole. Bodies stay immutable. Do NOT use for drafting from scratch (no source paragraphs), for sentence-grain prose discipline (use russellian-style), or for thesis/consistency checking (use book-thesis).
---

# paragraph-weaver

You thread an existing paragraph collection toward a typed goal. You do not draft
from scratch and you do not rewrite paragraph bodies — you reorder, write bridges
between paragraphs, and lightly edit the first/last sentence (seams).

The deterministic substrate lives in `skill_api.py`; you supply judgment. Confine
your non-determinism to *producing* artifacts. The gate scores frozen artifacts,
so a PASS is reproducible.

## Operating doctrine

1. Bodies are immutable. Only a paragraph's first/last sentence may be seam-edited;
   new bridge text may be inserted between paragraphs.
2. Every bridge draws entities only from its two flanking paragraphs and asserts
   one relation from `assets/connectives.json`. Run `validate_bridge`; if it fails,
   rewrite the bridge or emit a structural GAP — never invent content.
3. Prefer an enthymeme (no bridge) when the relation between two paragraphs is
   already inferable. Bridge only where the link would otherwise be missed.
4. The engine may refuse. If `check_feasibility` returns `ok=False`, stop and emit
   the diagnosis — do not thread off-goal material into a confident-looking whole.
5. Report failing gates; never dress a failure as success.

## Pipeline (call the scripts; you provide the judged inputs)

1. **PLAN** — Read the paragraphs and the user's one-line goal. Choose a target
   (`argument` | `emotion` | `narrative`). Write the goal-spec to `weave.goal.md`
   and echo it for the user to approve before weaving. `plan_template(goal)` gives
   the ordered slots.
2. **BIND** — For each paragraph compute entities with `extract_entities`, tag its
   role (target `role_vocabulary`), and assign it to a slot. Propose precedence
   edges (src must precede dst) with a one-line rationale each. Assemble a
   `WeaveGraph`. Run `find_cycles`; if any cycle is reported, demote its weakest
   edge to a note and record it — do not crash.
3. **FEASIBILITY** — Run `check_feasibility`. On refusal, stop and emit the reasons.
4. **ORDER** — Call `order_paragraphs(graph, lambda seq: target.order_objective(seq, graph, goal))`.
   The only hard constraint is acyclic precedence; slot order and edge-loading are
   soft penalties.
5. **WEAVE** — For each adjacent pair, decide whether a bridge is needed. If so,
   write one and check it with `validate_bridge`. For any seam edit, freeze the
   paragraph's load-bearing tokens and check the edit with `validate_seam_edit`;
   on failure, revert to the original sentence. Build the `Segment` list
   (source / seam / bridge).
6. **REVISE** — Score with the target's `gate_hook` over the frozen artifacts. If
   below target, request a `book-review` persona critique (advisory/soft — do not
   re-harden persona criticals), apply localized fixes, and re-score. Bound the
   loop; keep the best-scoring version; on give-up emit it marked `PROVISIONAL`
   with the unmet gate reasons. Unfilled required slots are reported as GAPS,
   never filled by a bridge.

## Output

Default to the **provenance-marked** render (`render_provenance`) so the user sees
source vs. seam vs. bridge. Offer the clean render (`render_clean`) only after they
approve. Always write `weave-report.md`: gate result, artifact hashes, bind map,
ordering rationale, every seam edit and bridge, GAPS, an `## Off-goal (unthreaded)`
appendix listing any unbound paragraphs, and the bridge-load ratio.

## Degenerate inputs

- One paragraph: nothing to weave; return it unchanged with a note.
- Two paragraphs: weave, but flag "single seam — relation asserted, not triangulated."
- `--plan-only`: stop after ORDER; emit the bind map and GAPS for approval before
  any generation.

## Targets and composition

- `argument` (deep) — threads toward a thesis (dispositio slots). In a book
  workspace it sequences over `book-thesis`'s structure and does **not** recompute
  contradictions (book-thesis owns those); standalone it extracts its own thesis.
  Its terminal prose stage is **`russellian-style`** (run last, owns final prose).
- `emotion`, `narrative` (shallow stubs) — implement the interface to prove
  pluggability; their objectives are trivial in v1 and their gates emit a
  not-yet-deep warning. They do **not** route to `russellian-style` (which refuses
  their persuasive/story genre); their `prose_policy` is `none` in v1.
- `book-review` personas are consumed as advisory only. Declare position in the
  pipeline so you never double-run review when your caller already will.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest skills/paragraph-weaver/tests/test_skill_doc.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add skills/paragraph-weaver/SKILL.md skills/paragraph-weaver/tests/test_skill_doc.py
git commit -m "docs(paragraph-weaver): SKILL.md agent-in-the-loop orchestration doctrine"
```

---

### Task 15: End-to-end acceptance test (snail paragraphs → argument)

This is the spec's acceptance test: drive the full deterministic pipeline with a
fixture that stands in for the agent's judged outputs (roles, slots, edges,
bridges), and assert a coherent threaded artifact with no silent drops and a
passing gate.

**Files:**
- Create: `skills/paragraph-weaver/tests/test_end_to_end.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_end_to_end.py
"""End-to-end: thread five argument paragraphs (snail-essay shape) toward a thesis.

The roles/slots/edges/bridges below stand in for the agent's judged outputs so the
deterministic pipeline can be exercised reproducibly.
"""
from __future__ import annotations

import skill_api as api


def _build_graph():
    paras = [
        ("p_thesis", "The snail rewards exact attention.", "claim", "thesis"),
        ("p_shell", "Its shell is a logarithmic spiral set by a single gene.", "premise", "evidence"),
        ("p_mucus", "Its slime is glue and lubricant at once, and costly to make.", "premise", "evidence"),
        ("p_concession", "The snail looks simple and slow.", "rebuttal", "concession"),
        ("p_close", "Nothing in nature is humble except our knowledge of it.", "conclusion", "conclusion"),
    ]
    nodes = [
        api.Node(id=i, text=t, entities=api.extract_entities(t), role=r, bound_slot=s)
        for (i, t, r, s) in paras
    ]
    # Precedence: thesis before its evidence; evidence before the close.
    edges = [
        api.Edge(src="p_thesis", dst="p_shell"),
        api.Edge(src="p_thesis", dst="p_mucus"),
        api.Edge(src="p_shell", dst="p_close"),
        api.Edge(src="p_mucus", dst="p_close"),
        api.Edge(src="p_concession", dst="p_close"),
    ]
    return api.WeaveGraph(nodes=nodes, edges=edges)


def test_pipeline_threads_all_paragraphs_and_passes_gate():
    target = api.get_target("argument")
    goal = {"thesis": "The snail rewards exact attention."}
    graph = _build_graph()

    # 1. No cycles.
    assert api.find_cycles(graph) == []

    # 2. Feasible.
    feasible = api.check_feasibility(graph, target.plan_template(goal))
    assert feasible.ok, feasible.reasons

    # 3. Order (hard precedence + soft dispositio objective).
    order = api.order_paragraphs(graph, lambda seq: target.order_objective(seq, graph, goal))
    assert order[0] == "p_thesis"
    assert order.index("p_shell") < order.index("p_close")
    assert order[-1] == "p_close"

    # 4. One validated bridge between thesis and the first evidence paragraph.
    left = graph.node(order[0])
    right = graph.node(order[1])
    bridge_text = "This attention is what the shell repays."
    bridge = api.validate_bridge(
        bridge_text, left.entities, right.entities, relation="evidence-of"
    )
    # Bridge reuses only flanking vocabulary; "attention"/"shell" appear in neighbours.
    assert bridge.ok, bridge.reasons

    # 5. Assemble segments in order, inserting the bridge after the thesis.
    segments = []
    for pos, nid in enumerate(order):
        segments.append(api.Segment(kind="source", text=graph.node(nid).text))
        if pos == 0:
            segments.append(api.Segment(kind="bridge", text=bridge_text))
    marked = api.render_provenance(segments)
    assert "<!-- bridge -->" in marked

    # 6. Gate over frozen artifacts.
    source_chars = sum(len(graph.node(nid).text) for nid in order)
    artifacts = {
        "input_ids": [n.id for n in graph.nodes],
        "output_ids": order,
        "source_chars": source_chars,
        "bridge_chars": len(bridge_text),
        "bridge_validity": [bridge.ok],
    }
    result = target.gate_hook(artifacts)
    assert result.passed, result.notes
    assert result.mechanical["no_silent_drops"] is True
```

- [ ] **Step 2: Run test to verify it fails (then passes)**

Run: `pytest skills/paragraph-weaver/tests/test_end_to_end.py -v`
Expected: With Tasks 1–14 complete, this PASSES on first run. If any sub-assertion fails (e.g. the bridge reuses a non-flanking word), adjust ONLY the fixture bridge text to reuse flanking vocabulary — do not change engine code to make the demo pass.

> Note on the bridge fixture: `validate_bridge` rejects any content word absent from the two flanking paragraphs. `"This attention is what the shell repays."` uses `attention` (from the thesis) and `shell` (from the evidence); `repays` is a new content word and WILL be flagged. **Before running, set the bridge text to reuse only flanking words**, e.g. `"This attention the shell rewards."` (all of `attention`, `shell`, `rewards` appear in the thesis/evidence paragraphs). Confirm with a quick check that `extract_entities(bridge_text)` ⊆ `left.entities | right.entities`.

- [ ] **Step 3: Run the full suite**

Run: `pytest skills/paragraph-weaver -v`
Expected: PASS (all tests across all modules)

- [ ] **Step 4: Commit**

```bash
git add skills/paragraph-weaver/tests/test_end_to_end.py
git commit -m "test(paragraph-weaver): end-to-end argument-threading acceptance test"
```

---

### Task 16: Wire into the suite (CI + references)

**Files:**
- Create: `skills/paragraph-weaver/references/engine-doctrine.md`
- Create: `skills/paragraph-weaver/references/target-authoring.md`
- Modify: repo CI workflow that runs per-skill pytest (find via `git grep -l "skills/" .github/workflows`)

- [ ] **Step 1: Write the reference docs**

```markdown
<!-- references/engine-doctrine.md -->
# Engine doctrine

- Non-determinism is confined to artifact *production*. The gate is a pure
  function of frozen, content-hashed artifacts (`engine.gate.score_gate`).
- One hard ordering constraint: acyclic precedence. Slot order and edge-loading
  are soft penalties in the target's `order_objective`.
- Cycles are reported, never fatal: demote the weakest edge in a reported SCC.
- Bridges use a closed vocabulary (`assets/connectives.json`) and may name only
  entities present in their two flanking paragraphs.
- Seam edits must preserve a paragraph's load-bearing tokens.
- Deferred to v1.5: NLI bridge soft-check, seam-level entity-grid coherence,
  calibrated coherence/goal-attainment thresholds, NER replacing the keyword proxy.
```

```markdown
<!-- references/target-authoring.md -->
# Authoring a new target

Implement `targets.base.Target` and `register()` an instance:

- `plan_template(goal) -> [Slot]` — ordered slots; mark required ones.
- `role_vocabulary() -> tuple[str, ...]` — the role tags BIND may assign.
- `order_objective(seq, graph, goal) -> float` — SOFT penalties only (lower is
  better); never encode hard constraints here (precedence is the engine's job).
- `gate_hook(artifacts) -> GateResult` — deep targets delegate to
  `engine.gate.score_gate`; shallow stubs return a not-yet-deep warning.
- `prose_policy` — `"russellian-style"` only if the genre is non-persuasive;
  otherwise `"none"`.
```

- [ ] **Step 2: Locate and read the CI workflow**

Run: `git grep -l "pytest" .github/workflows`
Read the matched workflow. If it iterates skills by directory, no edit is needed
(the new skill is picked up automatically). If skills are enumerated explicitly,
add `paragraph-weaver` to that list, matching the existing pattern exactly.

- [ ] **Step 3: Run the full skill suite once more**

Run: `pytest skills/paragraph-weaver -q`
Expected: PASS, no warnings about missing files.

- [ ] **Step 4: Commit**

```bash
git add skills/paragraph-weaver/references/engine-doctrine.md \
  skills/paragraph-weaver/references/target-authoring.md
# include the workflow file only if you modified it:
# git add .github/workflows/<file>.yml
git commit -m "docs(paragraph-weaver): engine + target-authoring references; CI wiring"
```

---

## Self-Review

**Spec coverage** — every spec section maps to a task:
- Target interface (§3) → Tasks 5–7.
- Determinism model / frozen-artifact gate (§4) → Tasks 2 (hashing), 11 (gate).
- IR: graph + provenance (§5) → Tasks 2, 12.
- Pipeline PLAN/BIND/FEASIBILITY/ORDER/WEAVE/REVISE (§6) → Tasks 8, 9, 10, 14 (REVISE is agent-orchestrated, documented in SKILL.md; its deterministic hooks are gate + validators).
- Gate (§7) → Task 11; feasibility refusal → Task 8.
- Integration boundaries / genre policy (§8) → Task 14 (SKILL.md doctrine) + `prose_policy` in Tasks 6–7.
- Provenance & trust (§9) → Task 12.
- File layout (§10) → Tasks 1, 16.
- Acceptance demo (§11) → Task 15.
- Deferral list (§12) → recorded in `references/engine-doctrine.md` (Task 16).

**Placeholder scan** — no TBD/TODO; every code step shows complete code; the one fixture caveat (bridge vocabulary) is spelled out with the exact replacement string.

**Type consistency** — `GateResult` is defined once (Task 5) and reused by `engine.gate` (Task 11) and the targets. `Node`/`Edge`/`WeaveGraph` signatures are stable from Task 2 onward. `validate_bridge`/`validate_seam_edit`/`score_gate`/`order_paragraphs` signatures match between definition, `skill_api` re-export (Task 13), and the e2e test (Task 15). The one cross-task dependency (`targets/argument.py` → `engine.gate.score_gate`) is called out in Tasks 6 and 11 with explicit build-order guidance.

**Known v1 limitations (intentional, per spec):** entity extraction is a keyword proxy (not NER); bridge fidelity is entity-subset + relation-set (not NLI); coherence/goal-attainment are agent-judged, not numerically gated. All are recorded for v1.5.
