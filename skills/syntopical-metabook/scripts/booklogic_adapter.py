"""Python adapter for the CLJS-on-Node booklogic CLI.

Speaks JSON only — the metabook never sees EDN. Booklogic owns the EDN side
via cljs.tools.reader.edn; the JSON projection happens inside booklogic when
called with `--io json`. The Python side uses stdlib json and subprocess.
"""
from __future__ import annotations
import json
import os
import shlex
import subprocess
from dataclasses import dataclass

class BooklogicError(RuntimeError):
    pass

class BooklogicTimeout(BooklogicError):
    pass

class BooklogicSchemaViolation(BooklogicError):
    pass

class BooklogicRuleFailure(BooklogicError):
    pass

@dataclass
class Position:
    claim_id: str
    source_id: str
    stance: str            # printable EDN of the stance s-expression
    rewrite_witness: str

@dataclass
class DisputedQuestion:
    topic: str
    question: str          # canonical EDN-printable phrasing
    positions: list[Position]

@dataclass
class Alternate:
    slug: str
    surface_form: str
    source_id: str
    rewrite_witness: str

@dataclass
class CanonicalConcept:
    slug: str
    alternates: list[Alternate]

@dataclass
class ReachabilityVerdict:
    candidate_id: str
    reachable: bool
    rule_trace: list[str]
    branch_witness: str | None

@dataclass
class BooklogicVersion:
    booklogic_version: str
    api_version: tuple[int, int]
    ruleset_checksum: str

def _bin() -> list[str]:
    # BOOKLOGIC_BIN is a trusted local override; the operator who sets this
    # env var is responsible for ensuring it resolves to an expected booklogic
    # executable. The adapter does not validate the binary.
    raw = os.environ.get("BOOKLOGIC_BIN", "booklogic")
    # shlex.split handles `python booklogic_stub.py` cleanly on POSIX;
    # on Windows the same form works for our cases.
    return shlex.split(raw, posix=(os.name != "nt"))

def _strip_json_string(s):
    """Stub/CLI emit JSON-projected EDN strings as "actual" (with quotes inside the JSON string).
    Unwrap them for Python consumption."""
    if isinstance(s, str) and len(s) >= 2 and s.startswith('"') and s.endswith('"'):
        return s[1:-1]
    return s

def _invoke(subcmd: str, payload: dict | None, timeout_s: int):
    cmd = _bin() + [subcmd, "--io", "json", "--timeout-s", str(timeout_s)]
    try:
        r = subprocess.run(
            cmd,
            input=json.dumps(payload) if payload is not None else "",
            capture_output=True,
            text=True,
            timeout=timeout_s + 5,  # give the CLI a small grace before subprocess timeout fires
        )
    except subprocess.TimeoutExpired as e:
        raise BooklogicTimeout(str(e)) from e
    if r.returncode == 1:
        raise BooklogicSchemaViolation(r.stderr.strip())
    if r.returncode == 2:
        raise BooklogicRuleFailure(r.stderr.strip())
    if r.returncode == 4:
        raise BooklogicTimeout(r.stderr.strip())
    if r.returncode != 0:
        raise BooklogicError(r.stderr.strip() or f"exit {r.returncode}")
    return json.loads(r.stdout) if r.stdout.strip() else None

# ---------- JSON projection: Python objects -> EDN-shaped JSON ----------

def _claim_to_json(c):
    body = getattr(c, "body", "")
    return {
        ":kind": ":claim",
        ":id": f'"{c.id}"',
        ":state": f":{c.state}",
        ":tags": [f'"{t}"' for t in c.tags],
        ":source-id": f'"{c.source_id}"',
        ":predicate": ":asserts",
        ":body": _sexpr_to_json(body),
        ":provenance": {":locator": f'"{getattr(c, "locator", "")}"'},
    }

def _concept_to_json(c):
    return {
        ":kind": ":concept",
        ":slug": f'"{c.slug}"',
        ":title": f'"{getattr(c, "title", "")}"',
        ":surface-forms": [f'"{s}"' for s in getattr(c, "surface_forms", [])],
        ":sources": [f'"{s}"' for s in getattr(c, "sources", [])],
    }

def _candidate_to_json(c):
    return {
        ":kind": ":candidate",
        ":id": f'"{c.id}"',
        ":extracted-concepts": [_concept_to_json(x) for x in getattr(c, "extracted_concepts", [])],
        ":embedding-score": getattr(c, "embedding_score", 0.0),
    }

def _tree_to_json(t):
    return {
        ":kind": ":thesis-tree",
        ":chapter-id": f'"{t.chapter_id}"',
        ":nodes": [_node_to_json(n) for n in getattr(t, "nodes", [])],
    }

def _node_to_json(n):
    return {
        ":kind": ":thesis-node",
        ":node-id": f'"{n.node_id}"',
        ":statement": _sexpr_to_json(n.statement),
        ":tags": [f'"{t}"' for t in n.tags],
        ":required-evidence-kind": f":{n.required_evidence_kind}",
        ":parent-id": f'"{n.parent_id}"' if getattr(n, "parent_id", None) else None,
    }

def _sexpr_to_json(s):
    """Encode an EDN s-expression. For the adapter we accept either nested
    list (treated as an EDN list, projected as {"$list": [...]}) or a string
    (already-printed EDN, projected as a quoted JSON string)."""
    if isinstance(s, list):
        return {"$list": [_sexpr_to_json(x) for x in s]}
    if isinstance(s, str):
        return f'"{s}"'
    return s

# ---------- JSON projection: EDN-shaped JSON -> Python dataclasses ----------

def _dq_from_json(d: dict) -> DisputedQuestion:
    return DisputedQuestion(
        topic=_strip_json_string(d[":topic"]),
        question=json.dumps(d[":question"]),
        positions=[Position(
            claim_id=_strip_json_string(p[":claim-id"]),
            source_id=_strip_json_string(p[":source-id"]),
            stance=json.dumps(p[":stance"]),
            rewrite_witness=_strip_json_string(p[":rewrite-witness"]),
        ) for p in d[":positions"]],
    )

def _cc_from_json(c: dict) -> CanonicalConcept:
    return CanonicalConcept(
        slug=_strip_json_string(c[":slug"]),
        alternates=[Alternate(
            slug=_strip_json_string(a[":slug"]),
            surface_form=_strip_json_string(a[":surface-form"]),
            source_id=_strip_json_string(a[":source-id"]),
            rewrite_witness=_strip_json_string(a[":rewrite-witness"]),
        ) for a in c[":alternates"]],
    )

def _verdict_from_json(v: dict) -> ReachabilityVerdict:
    bw = v.get(":branch-witness")
    return ReachabilityVerdict(
        candidate_id=_strip_json_string(v[":candidate-id"]),
        reachable=v[":reachable"],
        rule_trace=[_strip_json_string(r) for r in v.get(":rule-trace", [])],
        branch_witness=(json.dumps(bw) if bw is not None else None),
    )

# ---------- Public surface ----------

def disputed_questions(claims, timeout_s: int = 60) -> list[DisputedQuestion]:
    payload = {
        ":kind": ":input/disputed-questions",
        ":api-version": [0, 1],
        ":claims": [_claim_to_json(c) for c in claims],
    }
    out = _invoke("disputed-questions", payload, timeout_s) or []
    return [_dq_from_json(d) for d in out]

def reconcile_concepts(concepts, timeout_s: int = 60) -> list[CanonicalConcept]:
    payload = {
        ":kind": ":input/reconcile-concepts",
        ":api-version": [0, 1],
        ":concepts": [_concept_to_json(c) for c in concepts],
    }
    out = _invoke("reconcile-concepts", payload, timeout_s) or []
    return [_cc_from_json(c) for c in out]

def reachable_from_thesis(candidate, thesis_tree, timeout_s: int = 30) -> ReachabilityVerdict:
    payload = {
        ":kind": ":input/reachable-from-thesis",
        ":api-version": [0, 1],
        ":candidate": _candidate_to_json(candidate),
        ":thesis-tree": _tree_to_json(thesis_tree),
    }
    out = _invoke("reachable-from-thesis", payload, timeout_s)
    return _verdict_from_json(out)

def version() -> BooklogicVersion:
    out = _invoke("version", None, timeout_s=10)
    return BooklogicVersion(
        booklogic_version=_strip_json_string(out[":booklogic-version"]),
        api_version=tuple(out[":api-version"]),
        ruleset_checksum=_strip_json_string(out[":ruleset-checksum"]),
    )
