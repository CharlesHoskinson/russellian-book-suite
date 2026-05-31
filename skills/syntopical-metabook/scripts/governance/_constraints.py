"""Tolerant reader for constraints.edn (hand-written defconstraint rules).

Handles both on-disk shapes the toolchain uses:
  source   (rules/booklogic/constraints.edn):
    {:forms [(defconstraint NAME :assert ... :track T :on-unsat {...}) ...]}
  compiled (rules/constraints.edn):
    {:version 1 :constraints [{:id "NAME" :assert ... :track T ...} ...]}

Returns constraint-id -> {"track": <str|None>}. Ids are normalized to a
leading-colon form (":NAME"). Regex-based; not a general EDN parser. A file is
one shape or the other, never both, so the two passes do not double-count.
"""
from __future__ import annotations
import re
from pathlib import Path

_TRACK_RE = re.compile(r":track\s+(:[A-Za-z0-9/_.\-]+)")


def _norm_id(raw: str) -> str:
    raw = raw.strip().strip('"')
    return raw if raw.startswith(":") else f":{raw}"


def _track_in(segment: str) -> str | None:
    m = _TRACK_RE.search(segment)
    return m.group(1) if m else None


def load_constraints(path: Path) -> dict[str, dict]:
    path = Path(path)
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    out: dict[str, dict] = {}

    # Compiled shape: maps each carrying :id "NAME".
    compiled = [(m.start(), _norm_id(m.group(1)))
                for m in re.finditer(r':id\s+"([^"]+)"', text)]
    for i, (pos, cid) in enumerate(compiled):
        end = compiled[i + 1][0] if i + 1 < len(compiled) else len(text)
        out[cid] = {"track": _track_in(text[pos:end])}

    # Source shape: (defconstraint NAME ...).
    source = [(m.start(), _norm_id(m.group(1)))
              for m in re.finditer(r"\(defconstraint\s+([A-Za-z0-9:_./\-]+)", text)]
    for i, (pos, cid) in enumerate(source):
        end = source[i + 1][0] if i + 1 < len(source) else len(text)
        out.setdefault(cid, {"track": _track_in(text[pos:end])})

    return out
