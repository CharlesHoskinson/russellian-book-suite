"""positions.edn writer and reader.

Writer is byte-deterministic: rows are sorted by (rule_id, school) before
emit; whitespace and key order are fixed.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from ._stance import Stance
from ._schools import _read_edn_map


@dataclass(frozen=True)
class Position:
    rule_id: str
    rule_form: str
    source: str               # "induced" | "defconstraint"
    school: str
    stance: Stance
    supporting_atoms: list[str] = field(default_factory=list)
    supporting_docs: list[str] = field(default_factory=list)
    contradicting_atoms: list[str] = field(default_factory=list)
    contradicting_docs: list[str] = field(default_factory=list)
    declared_by_charter: bool = False
    induction_prov: str = ""


def _edn_str(s: str) -> str:
    """Emit an EDN double-quoted string with backslash escaping."""
    escaped = s.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _emit_vec(items: list[str]) -> str:
    if not items:
        return "[]"
    return "[" + " ".join(_edn_str(s) for s in items) + "]"


def _emit_position(p: Position) -> str:
    return (
        "  {:rule-id      " + _edn_str(p.rule_id) + "\n"
        "   :rule-form    " + _edn_str(p.rule_form) + "\n"
        "   :source       :" + p.source + "\n"
        "   :school       :" + p.school + "\n"
        "   :stance       :" + p.stance.value + "\n"
        "   :supporting-atoms    " + _emit_vec(p.supporting_atoms) + "\n"
        "   :supporting-docs     " + _emit_vec(p.supporting_docs) + "\n"
        "   :contradicting-atoms " + _emit_vec(p.contradicting_atoms) + "\n"
        "   :contradicting-docs  " + _emit_vec(p.contradicting_docs) + "\n"
        "   :declared-by-charter " + ("true" if p.declared_by_charter else "false") + "\n"
        "   :induction-prov      " + _edn_str(p.induction_prov) + "}"
    )


def write_positions(path: Path, positions: list[Position],
                    generated_at: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    sorted_positions = sorted(positions, key=lambda p: (p.rule_id, p.school), reverse=True)
    body = ",\n".join(_emit_position(p) for p in sorted_positions)
    text = (
        "{:version 1\n"
        f" :generated-at \"{generated_at}\"\n"
        " :positions\n"
        " [" + body.lstrip() + "]}\n"
    )
    path.write_text(text, encoding="utf-8", newline="\n")


def read_positions(path: Path) -> list[Position]:
    """Parse positions.edn back into Position dataclasses.

    Tolerant of the writer's output format. Not a general EDN parser.
    """
    text = path.read_text(encoding="utf-8")
    # Strip outer map and find :positions vector
    start = text.index(":positions")
    bracket = text.index("[", start)
    depth = 0
    vec = ""
    for j, ch in enumerate(text[bracket:], start=bracket):
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                vec = text[bracket + 1:j]
                break
    rows: list[Position] = []
    i = 0
    while i < len(vec):
        if vec[i].isspace() or vec[i] == ",":
            i += 1
            continue
        if vec[i] != "{":
            break
        depth = 0
        for j, ch in enumerate(vec[i:], start=i):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    rows.append(_parse_position_map(vec[i:j + 1]))
                    i = j + 1
                    break
        else:
            break
    return rows


def _parse_position_map(text: str) -> Position:
    data = _read_edn_map(text)
    src = data["source"]
    if isinstance(src, str) and src.startswith(":"):
        src = src[1:]
    sch = data["school"]
    if isinstance(sch, str) and sch.startswith(":"):
        sch = sch[1:]
    st = data["stance"]
    if isinstance(st, str) and st.startswith(":"):
        st = st[1:]
    declared = data.get("declared-by-charter", False)
    if isinstance(declared, str):
        declared = declared == "true"
    return Position(
        rule_id=str(data["rule-id"]),
        rule_form=str(data["rule-form"]),
        source=str(src),
        school=str(sch),
        stance=Stance(str(st)),
        supporting_atoms=list(data.get("supporting-atoms", [])),
        supporting_docs=list(data.get("supporting-docs", [])),
        contradicting_atoms=list(data.get("contradicting-atoms", [])),
        contradicting_docs=list(data.get("contradicting-docs", [])),
        declared_by_charter=bool(declared),
        induction_prov=str(data.get("induction-prov", "")),
    )
