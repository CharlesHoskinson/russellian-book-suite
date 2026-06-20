"""Project authored design records into the unified KG.

This module implements the deterministic, read-only projectors for the
design-intelligence KG (REQ-KG-048/053). It covers OpenSpec requirements,
authored markdown decisions, operator commands, tests, CI, and exact-evidence
traceability links.
"""
from __future__ import annotations

import ast
import json
import re
import subprocess
from pathlib import Path

import yaml

_REQ_HEADING = re.compile(
    r"^### Requirement: (?P<req>REQ-[A-Z0-9-]+-\d+) (?:-|\u2014) (?P<title>.+?) "
    r"\((?P<pattern>[^)]+)\)\s*$"
)
_SCENARIO_HEADING = re.compile(r"^#### Scenario: (?P<title>.+?)\s*$")
_NEXT_HEADING = re.compile(r"^### ")
_CAPABILITY_RE = re.compile(r"^# Capability: (?P<capability>[A-Za-z0-9_.-]+)\s*$")
_DESIGN_HEADING = re.compile(
    r"^(?:#{1,4}\s+)?(?P<kind>Decision|Risk|Non-goal|Non-Goal|Non goal|Alternative):\s+"
    r"(?P<title>.+?)\s*$"
)
_DESIGN_SECTION = re.compile(
    r"^#{1,4}\s+(?P<section>Decision|Decisions|Design decisions|Risk|Risks|"
    r"Non-goal|Non-goals|Alternative|Alternatives)\s*$",
    re.IGNORECASE,
)
_OPERATOR_HEADING = re.compile(
    r"^(?:#{1,4}\s+)?(?:Operator command|Command):\s+(?P<title>.+?)\s*$",
    re.IGNORECASE,
)
_MARKDOWN_HEADING = re.compile(r"^#{1,6}\s+(?P<title>.+?)\s*$")
_FENCE = re.compile(r"^```(?P<lang>[A-Za-z0-9_-]*)\s*$")
_COMMAND_LANGS = {
    "bash": "bash",
    "sh": "sh",
    "shell": "sh",
    "powershell": "powershell",
    "pwsh": "powershell",
}
_SKIP_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "graphify-out",
    "node_modules",
    "target",
    "venv",
}
_REQ_TOKEN = re.compile(r"REQ(?:[_-][A-Z0-9]+)+[_-]\d+", re.IGNORECASE)
_RUST_TEST_FN = re.compile(r"\bfn\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(")
_CLJS_TEST = re.compile(r"\(deftest\s+([^\s\)]+)")
_BACKTICK_TOKEN = re.compile(r"`([^`]+)`")
_CODE_PATH_SUFFIXES = {".clj", ".cljs", ".py", ".rs", ".yaml", ".yml"}
_TRACEABILITY_MANIFEST_NAMES = {"traceability.json", "design-traceability.json"}
_REVIEWED_TRACE_TARGETS = {
    "decision-constrains-code": "code-path",
    "requirement-implemented-by": "code-path",
    "requirement-covered-by": "test-case",
    "requirement-gated-by": "ci-job",
}
_GIT_SNAPSHOT_CACHE: dict[Path, set[Path] | None] = {}


def _rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _slug(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "untitled"


def _join(lines: list[str]) -> str:
    return " ".join(line.strip() for line in lines if line.strip())


def _read_text_lines(path: Path) -> list[str]:
    try:
        return path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        return path.read_text(encoding="cp1252").splitlines()


def _read_text(path: Path) -> str:
    return "\n".join(_read_text_lines(path))


def _normalise_kind(kind: str) -> str:
    return kind.lower().replace(" ", "-")


def _section_kind(section: str) -> str:
    section = section.lower().replace(" ", "-")
    if section in {"decision", "decisions", "design-decisions"}:
        return "decision"
    if section in {"risk", "risks"}:
        return "risk"
    if section in {"non-goal", "non-goals"}:
        return "non-goal"
    if section in {"alternative", "alternatives"}:
        return "alternative"
    return section


def _markdown_paths(root: Path) -> list[Path]:
    snapshot = _git_snapshot_paths(root)
    if snapshot is not None:
        return sorted(
            root / path
            for path in snapshot
            if path.suffix == ".md"
            and path.parts[:1] in {("docs",), ("openspec",)}
            and not _skip_path(path)
        )
    roots = [root / "docs", root / "openspec"]
    paths: set[Path] = set()
    for base in roots:
        if base.exists():
            paths.update(path for path in base.rglob("*.md") if not _skip_path(path))
    return sorted(paths)


def _skip_path(path: Path) -> bool:
    parts = path.parts
    if set(parts) & _SKIP_DIRS:
        return True
    return any(
        parts[index] == "docs" and parts[index + 1] in {"audits", "eval"}
        for index in range(len(parts) - 1)
    )


def _source_paths(root: Path, suffixes: set[str]) -> list[Path]:
    snapshot = _git_snapshot_paths(root)
    if snapshot is not None:
        return sorted(
            root / path
            for path in snapshot
            if path.suffix in suffixes and not _skip_path(path)
        )
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix in suffixes and not _skip_path(path)
    )


def _workflow_paths(root: Path) -> list[Path]:
    snapshot = _git_snapshot_paths(root)
    if snapshot is not None:
        return sorted(
            root / path
            for path in snapshot
            if path.parts[:2] == (".github", "workflows")
            and path.suffix in {".yml", ".yaml"}
        )
    workflow_dir = root / ".github" / "workflows"
    if not workflow_dir.exists():
        return []
    return sorted(
        path
        for path in workflow_dir.iterdir()
        if path.is_file() and path.suffix in {".yml", ".yaml"}
    )


def _traceability_manifest_paths(root: Path) -> list[Path]:
    snapshot = _git_snapshot_paths(root)
    if snapshot is not None:
        return sorted(
            root / path
            for path in snapshot
            if path.name in _TRACEABILITY_MANIFEST_NAMES
            and path.parts[:1] in {("docs",), ("openspec",)}
            and not _skip_path(path)
        )
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file()
        and path.name in _TRACEABILITY_MANIFEST_NAMES
        and not _skip_path(path)
    )


def _graphify_path(root: Path) -> Path | None:
    for rel in ("graphify/graph.json", "graphify-out/graph.json"):
        candidate = root / rel
        if candidate.exists():
            return candidate
    return None


def _git_snapshot_paths(root: Path) -> set[Path] | None:
    """Return repo-root files from the Git index, or None for non-root fixtures.

    Whole-repo audits must be a function of the Git snapshot, not of random
    untracked local directories. Fixture and temporary roots are intentionally
    filesystem-based because they may not be Git worktree roots.
    """
    root = Path(root).resolve()
    if root in _GIT_SNAPSHOT_CACHE:
        return _GIT_SNAPSHOT_CACHE[root]
    try:
        top = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        _GIT_SNAPSHOT_CACHE[root] = None
        return None
    if Path(top).resolve() != root:
        _GIT_SNAPSHOT_CACHE[root] = None
        return None
    try:
        output = subprocess.run(
            ["git", "-C", str(root), "ls-files", "--cached", "-z"],
            check=True,
            capture_output=True,
            timeout=10,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        _GIT_SNAPSHOT_CACHE[root] = None
        return None
    paths = {
        Path(part.decode("utf-8")).as_posix()
        for part in output.split(b"\0")
        if part
    }
    _GIT_SNAPSHOT_CACHE[root] = {Path(path) for path in paths}
    return _GIT_SNAPSHOT_CACHE[root]


def _normalise_path(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.replace("\\", "/").strip()
    while text.startswith("./"):
        text = text[2:]
    parts = [part for part in text.split("/") if part and part != "."]
    return "/".join(parts) if parts else None


def _code_nodes(root: Path) -> list[dict]:
    path = _graphify_path(root)
    if path is None:
        return []
    doc = json.loads(path.read_text(encoding="utf-8"))
    nodes = doc.get("nodes", [])
    if not isinstance(nodes, list):
        return []
    rows: list[dict] = []
    for node in nodes:
        if not isinstance(node, dict) or not node.get("id"):
            continue
        source_file = _normalise_path(node.get("source_file"))
        rows.append(
            {
                "id": str(node["id"]),
                "label": str(node.get("label") or ""),
                "source_file": source_file or "",
            }
        )
    rows.sort(key=lambda row: row["id"])
    return rows


def _is_module_node(node: dict, source_file: str) -> bool:
    if node["source_file"] != source_file:
        return False
    basename = Path(source_file).name
    label = _normalise_path(node.get("label")) or ""
    return label in {source_file, basename}


def _module_nodes_by_path(nodes: list[dict]) -> dict[str, dict]:
    by_path: dict[str, list[dict]] = {}
    for node in nodes:
        source_file = node.get("source_file") or ""
        if _is_module_node(node, source_file):
            by_path.setdefault(source_file, []).append(node)
    return {
        source_file: matches[0]
        for source_file, matches in by_path.items()
        if len(matches) == 1
    }


def _symbol_aliases(node: dict) -> set[str]:
    aliases = {node["id"]}
    label = node.get("label") or ""
    if label:
        aliases.add(label)
        if label.endswith("()"):
            aliases.add(label[:-2])
    return aliases


def _code_nodes_by_symbol(nodes: list[dict]) -> dict[str, list[dict]]:
    by_symbol: dict[str, list[dict]] = {}
    for node in nodes:
        for alias in _symbol_aliases(node):
            by_symbol.setdefault(alias, []).append(node)
    return {
        symbol: sorted(matches, key=lambda row: row["id"])
        for symbol, matches in by_symbol.items()
    }


def _capability_from_path(path: Path, root: Path) -> str:
    parts = path.relative_to(root).parts
    if len(parts) >= 4 and parts[0] == "openspec" and parts[1] == "specs":
        return parts[2]
    if "specs" in parts:
        idx = parts.index("specs")
        if idx + 1 < len(parts):
            return parts[idx + 1]
    return "unknown"


def _capability_from_text(lines: list[str], fallback: str) -> str:
    for line in lines:
        match = _CAPABILITY_RE.match(line)
        if match:
            return match.group("capability")
    return fallback


def _status_for_path(path: Path, root: Path) -> str:
    parts = path.relative_to(root).parts
    if "archive" in parts:
        return "archived"
    if "changes" in parts:
        return "proposed"
    return "fixture" if "fixtures" in root.parts else "accepted"


def _requirement_body(lines: list[str], start: int) -> str:
    body: list[str] = []
    for line in lines[start:]:
        if _NEXT_HEADING.match(line):
            break
        if not line.strip():
            if body:
                break
            continue
        body.append(line.strip())
    return " ".join(body)


def _scenario_body(title: str, lines: list[str], start: int) -> str:
    body = [title.strip().rstrip(".")]
    for line in lines[start:]:
        if _REQ_HEADING.match(line) or _SCENARIO_HEADING.match(line):
            break
        if line.startswith("### "):
            break
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("- "):
            stripped = stripped[2:].strip()
        stripped = stripped.replace("**", "")
        body.append(stripped)
    return _join(body)


def _spec_paths(root: Path) -> list[Path]:
    snapshot = _git_snapshot_paths(root)
    if snapshot is not None:
        return sorted(
            root / path
            for path in snapshot
            if path.name == "spec.md" and path.parts[:1] == ("openspec",)
        )
    openspec = root / "openspec"
    if not openspec.exists():
        return []
    return sorted(openspec.rglob("spec.md"))


def _design_section(lines: list[str], start: int) -> tuple[str, str, str]:
    status = "documented"
    body: list[str] = []
    rationale: list[str] = []
    in_rationale = False

    for line in lines[start:]:
        if _MARKDOWN_HEADING.match(line):
            break

        stripped = line.strip()
        if not stripped:
            continue

        if stripped.lower().startswith("status:"):
            status = stripped.split(":", 1)[1].strip().lower() or status
            continue

        if stripped.lower().startswith("rationale:"):
            in_rationale = True
            tail = stripped.split(":", 1)[1].strip()
            if tail:
                rationale.append(tail)
            continue

        if in_rationale:
            rationale.append(stripped)
        else:
            body.append(stripped)

    return status, _join(body), _join(rationale)


def _decision_text(title: str, body: str) -> str:
    clean_title = title.strip().rstrip(".")
    if body:
        return f"{clean_title}. {body}"
    return clean_title


def _section_rows(lines: list[str], start: int) -> list[tuple[int, str]]:
    rows: list[tuple[int, str]] = []
    body: list[str] = []

    for offset, line in enumerate(lines[start:], start=start):
        if _MARKDOWN_HEADING.match(line):
            break

        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("- "):
            rows.append((offset + 1, stripped[2:].strip()))
        elif not rows:
            body.append(stripped)

    if rows:
        return rows
    body_text = _join(body)
    return [(start + 1, body_text)] if body_text else []


def _target_from_name(name: str, fallback: str) -> str:
    match = _REQ_TOKEN.search(name)
    if match:
        return match.group(0).replace("_", "-").upper()
    return fallback


def _path_tokens(text: str) -> list[str]:
    tokens = set()
    for token in _BACKTICK_TOKEN.findall(text):
        normalized = _normalise_path(token)
        if normalized and Path(normalized).suffix in _CODE_PATH_SUFFIXES:
            tokens.add(normalized)
    return sorted(tokens)


def _symbol_tokens(text: str) -> list[str]:
    tokens = set()
    for token in _BACKTICK_TOKEN.findall(text):
        if "/" in token or "\\" in token or "." in token:
            continue
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", token):
            tokens.add(token)
    return sorted(tokens)


def _weak_symbol_candidate(symbol: str) -> bool:
    return bool(re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", symbol)) and "_" in symbol


def _weak_symbol_mentions(text: str, exact_symbols: set[str]) -> list[str]:
    found: set[str] = set()
    for match in re.finditer(r"\b[A-Za-z_][A-Za-z0-9_]*\b", text):
        symbol = match.group(0)
        if symbol in exact_symbols:
            continue
        if _weak_symbol_candidate(symbol):
            found.add(symbol)
    return sorted(found)


def _trace_id(kind: str, from_id: str, to_id: str, witness: str) -> str:
    return f"trace:{kind}:{from_id}->{to_id}:{_slug(witness)}"


def _trace_row(
    *,
    kind: str,
    from_id: str,
    to_id: str,
    confidence: float,
    witness: str,
    provenance: str,
    promoted: bool,
    source_path: str,
    source_line: int,
) -> dict:
    return {
        "id": _trace_id(kind, from_id, to_id, witness),
        "from_id": from_id,
        "to_id": to_id,
        "kind": kind,
        "confidence": confidence,
        "witness": witness,
        "provenance": provenance,
        "promoted": promoted,
        "source_path": source_path,
        "source_line": source_line,
    }


def _line_for_manifest_entry(lines: list[str], entry: dict) -> int:
    tokens = [
        str(entry.get("target") or ""),
        str(entry.get("requirement_id") or ""),
        str(entry.get("kind") or ""),
    ]
    for token in tokens:
        if not token:
            continue
        for index, line in enumerate(lines, start=1):
            if token in line:
                return index
    return 1


def _module_path_for_import(module: str) -> str | None:
    if not module or module.startswith("."):
        return None
    return _normalise_path(module.replace(".", "/") + ".py")


def _python_imports(path: Path) -> list[tuple[str, int]]:
    try:
        tree = ast.parse(_read_text(path), filename=str(path))
    except SyntaxError:
        return []
    imports: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imports.append((node.module, node.lineno))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imports.append((alias.name, node.lineno))
    return sorted(set(imports), key=lambda item: (item[1], item[0]))


def _test_row(
    framework: str,
    path: Path,
    root: Path,
    name: str,
    source_line: int,
    node_id: str | None = None,
) -> dict:
    source_path = _rel(path, root)
    id_name = node_id or name
    return {
        "id": f"test-case:{framework}:{source_path}::{id_name}",
        "name": name,
        "framework": framework,
        "target": _target_from_name(name, source_path),
        "source_path": source_path,
        "source_line": source_line,
    }


def _python_test_rows(path: Path, root: Path) -> list[dict]:
    try:
        tree = ast.parse(_read_text(path), filename=str(path))
    except SyntaxError:
        return []

    rows: list[dict] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("test_"):
                rows.append(_test_row("pytest", path, root, node.name, node.lineno))
        elif isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if child.name.startswith("test_"):
                        name = f"{node.name}::{child.name}"
                        rows.append(
                            _test_row(
                                "pytest",
                                path,
                                root,
                                name,
                                child.lineno,
                                node_id=name,
                            )
                        )
    return rows


def _rust_test_rows(path: Path, root: Path) -> list[dict]:
    rows: list[dict] = []
    pending_test = False
    for index, line in enumerate(_read_text_lines(path), start=1):
        stripped = line.strip()
        if stripped == "#[test]" or stripped.startswith("#[tokio::test"):
            pending_test = True
            continue
        if not pending_test:
            continue
        match = _RUST_TEST_FN.search(stripped)
        if match:
            name = match.group(1)
            rows.append(_test_row("cargo", path, root, name, index))
            pending_test = False
        elif stripped and not stripped.startswith("#"):
            pending_test = False
    return rows


def _cljs_test_rows(path: Path, root: Path) -> list[dict]:
    rows: list[dict] = []
    for index, line in enumerate(_read_text_lines(path), start=1):
        match = _CLJS_TEST.search(line)
        if match:
            name = match.group(1)
            framework = "clojure" if path.suffix == ".clj" else "cljs"
            rows.append(_test_row(framework, path, root, name, index))
    return rows


def _load_workflow(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def _workflow_on(data: dict):
    return data.get("on", data.get(True))


def _trigger_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return ",".join(sorted(str(item) for item in value))
    if isinstance(value, dict):
        return ",".join(sorted(str(key) for key in value))
    return str(value)


def _line_for_top_key(lines: list[str], key: str) -> int:
    pattern = re.compile(rf"^{re.escape(key)}:\s*")
    for index, line in enumerate(lines, start=1):
        if pattern.match(line):
            return index
    return 1


def _job_lines(lines: list[str]) -> dict[str, int]:
    jobs: dict[str, int] = {}
    in_jobs = False
    for index, line in enumerate(lines, start=1):
        if line.startswith("jobs:"):
            in_jobs = True
            continue
        if in_jobs and line and not line.startswith(" "):
            break
        if not in_jobs:
            continue
        match = re.match(r"^  ([A-Za-z0-9_-]+):\s*(?:#.*)?$", line)
        if match:
            jobs[match.group(1)] = index
    return jobs


def _normalise_command(command: str) -> str:
    lines = [
        line.strip()
        for line in command.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    return " && ".join(lines)


def _first_job_command(job: dict) -> str:
    steps = job.get("steps") or []
    if not isinstance(steps, list):
        return ""
    for step in steps:
        if isinstance(step, dict) and isinstance(step.get("run"), str):
            return _normalise_command(step["run"])
    return ""


def _as_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _ci_selector(job: dict) -> str:
    parts: list[str] = []
    needs = _as_list(job.get("needs"))
    if needs:
        parts.append(
            "needs="
            + json.dumps([str(need) for need in needs], separators=(",", ":"))
        )
    strategy = job.get("strategy") if isinstance(job.get("strategy"), dict) else {}
    matrix = strategy.get("matrix") if isinstance(strategy, dict) else None
    if matrix:
        parts.append(
            "matrix="
            + json.dumps(matrix, sort_keys=True, separators=(",", ":"))
        )
    if job.get("if"):
        parts.append(f"if={job['if']}")
    return ";".join(parts)


def _ci_required(job_id: str, name: str) -> bool:
    haystack = f"{job_id} {name}".lower()
    return "required" in haystack or job_id == "ci-required"


def extract_openspec_requirements(root: Path) -> list[dict]:
    """Return deterministic ``design-requirement`` rows from OpenSpec specs.

    Rows use schema snake-case keys because ``CozoStore.load`` accepts both
    kebab and snake spellings. ``source_path`` is always relative to ``root``.
    """
    root = Path(root)
    rows: list[dict] = []
    for path in _spec_paths(root):
        lines = _read_text_lines(path)
        capability = _capability_from_text(lines, _capability_from_path(path, root))
        status = _status_for_path(path, root)
        source_path = _rel(path, root)
        for index, line in enumerate(lines):
            match = _REQ_HEADING.match(line)
            if not match:
                continue
            req_id = match.group("req")
            text = _requirement_body(lines, index + 1)
            rows.append(
                {
                    "id": f"openspec:{capability}:{req_id}",
                    "requirement_id": req_id,
                    "capability": capability,
                    "status": status,
                    "text": text,
                    "source_path": source_path,
                    "source_line": index + 1,
                }
            )
    rows.sort(key=lambda row: (row["source_path"], row["source_line"], row["id"]))
    return rows


def extract_openspec_scenarios(root: Path) -> list[dict]:
    """Return deterministic ``design-scenario`` rows from OpenSpec specs."""
    root = Path(root)
    rows: list[dict] = []
    for path in _spec_paths(root):
        lines = _read_text_lines(path)
        capability = _capability_from_text(lines, _capability_from_path(path, root))
        source_path = _rel(path, root)
        current_req_id: str | None = None
        for index, line in enumerate(lines):
            req_match = _REQ_HEADING.match(line)
            if req_match:
                current_req_id = req_match.group("req")
                continue
            scenario_match = _SCENARIO_HEADING.match(line)
            if scenario_match is None or current_req_id is None:
                continue
            title = scenario_match.group("title").strip()
            rows.append(
                {
                    "id": (
                        f"openspec-scenario:{capability}:{current_req_id}:"
                        f"{index + 1}:{_slug(title)}"
                    ),
                    "requirement_id": current_req_id,
                    "capability": capability,
                    "text": _scenario_body(title, lines, index + 1),
                    "source_path": source_path,
                    "source_line": index + 1,
                }
            )
    rows.sort(key=lambda row: (row["source_path"], row["source_line"], row["id"]))
    return rows


def extract_design_decisions(root: Path) -> list[dict]:
    """Return deterministic ``design-decision`` rows from markdown docs."""
    root = Path(root)
    rows: list[dict] = []
    for path in _markdown_paths(root):
        lines = _read_text_lines(path)
        source_path = _rel(path, root)
        for index, line in enumerate(lines):
            match = _DESIGN_HEADING.match(line)
            if match:
                kind = _normalise_kind(match.group("kind"))
                title = match.group("title").strip()
                status, body, rationale = _design_section(lines, index + 1)
                rows.append(
                    {
                        "id": (
                            f"design-doc:{source_path}:{index + 1}:"
                            f"{kind}:{_slug(title)}"
                        ),
                        "kind": kind,
                        "status": status,
                        "text": _decision_text(title, body),
                        "rationale": rationale,
                        "source_path": source_path,
                        "source_line": index + 1,
                    }
                )
                continue

            section = _DESIGN_SECTION.match(line)
            if not section:
                continue
            kind = _section_kind(section.group("section"))
            for source_line, text in _section_rows(lines, index + 1):
                rows.append(
                    {
                        "id": (
                            f"design-doc:{source_path}:{source_line}:"
                            f"{kind}:{_slug(text)}"
                        ),
                        "kind": kind,
                        "status": "documented",
                        "text": text,
                        "rationale": "",
                        "source_path": source_path,
                        "source_line": source_line,
                    }
                )
    rows.sort(key=lambda row: (row["source_path"], row["source_line"], row["id"]))
    return rows


def extract_operator_commands(root: Path) -> list[dict]:
    """Return deterministic ``operator-command`` rows from fenced commands."""
    root = Path(root)
    rows: list[dict] = []
    for path in _markdown_paths(root):
        lines = _read_text_lines(path)
        source_path = _rel(path, root)
        purpose = ""
        fence_shell: str | None = None
        in_fence = False
        for index, line in enumerate(lines):
            operator_heading = _OPERATOR_HEADING.match(line)
            if operator_heading:
                purpose = operator_heading.group("title").strip()
            else:
                markdown_heading = _MARKDOWN_HEADING.match(line)
                if markdown_heading:
                    purpose = markdown_heading.group("title").strip()

            stripped = line.strip()
            fence = _FENCE.match(stripped)
            if fence and not in_fence:
                in_fence = True
                lang = fence.group("lang").lower()
                fence_shell = _COMMAND_LANGS.get(lang)
                continue
            if in_fence and stripped == "```":
                in_fence = False
                fence_shell = None
                continue
            if not in_fence or not fence_shell:
                continue

            command = stripped
            if not command or command.startswith("#"):
                continue
            rows.append(
                {
                    "id": f"operator-command:{source_path}:{index + 1}",
                    "command": command,
                    "shell": fence_shell,
                    "purpose": purpose,
                    "source_path": source_path,
                    "source_line": index + 1,
                }
            )
    rows.sort(key=lambda row: row["id"])
    return rows


def extract_test_cases(root: Path) -> list[dict]:
    """Return deterministic pytest/Rust/cljs ``test-case`` rows."""
    root = Path(root)
    rows: list[dict] = []
    for path in _source_paths(root, {".py", ".rs", ".cljs", ".clj"}):
        rel = _rel(path, root)
        if path.suffix == ".py" and (
            path.name.startswith("test_")
            or path.name.endswith("_test.py")
            or "tests" in path.parts
            or rel.startswith("ci/")
        ):
            rows.extend(_python_test_rows(path, root))
        elif path.suffix == ".rs" and "tests" in path.parts:
            rows.extend(_rust_test_rows(path, root))
        elif path.suffix in {".cljs", ".clj"} and (
            "test" in path.parts or "tests" in path.parts
        ):
            rows.extend(_cljs_test_rows(path, root))
    rows.sort(key=lambda row: (row["source_path"], row["source_line"], row["id"]))
    return rows


def extract_ci_workflows(root: Path) -> list[dict]:
    """Return deterministic ``ci-workflow`` rows from GitHub Actions YAML."""
    root = Path(root)
    rows: list[dict] = []
    for path in _workflow_paths(root):
        lines = _read_text_lines(path)
        data = _load_workflow(path)
        source_path = _rel(path, root)
        rows.append(
            {
                "id": f"ci-workflow:{source_path}",
                "name": str(data.get("name") or path.stem),
                "trigger": _trigger_text(_workflow_on(data)),
                "source_path": source_path,
                "source_line": _line_for_top_key(lines, "name"),
            }
        )
    rows.sort(key=lambda row: row["id"])
    return rows


def extract_ci_jobs(root: Path) -> list[dict]:
    """Return deterministic ``ci-job`` rows from GitHub Actions YAML."""
    root = Path(root)
    rows: list[dict] = []
    for path in _workflow_paths(root):
        lines = _read_text_lines(path)
        source_path = _rel(path, root)
        workflow_id = f"ci-workflow:{source_path}"
        data = _load_workflow(path)
        jobs = data.get("jobs") if isinstance(data.get("jobs"), dict) else {}
        line_by_job = _job_lines(lines)
        for job_id, job in sorted(jobs.items()):
            if not isinstance(job, dict):
                continue
            name = str(job.get("name") or job_id)
            rows.append(
                {
                    "id": f"ci-job:{source_path}:{job_id}",
                    "workflow_id": workflow_id,
                    "name": name,
                    "required": _ci_required(str(job_id), name),
                    "selector": _ci_selector(job),
                    "command": _first_job_command(job),
                    "source_path": source_path,
                    "source_line": line_by_job.get(str(job_id), 1),
                }
            )
    rows.sort(key=lambda row: row["id"])
    return rows


def _design_code_links(
    rows: list[dict],
    *,
    kind: str,
    nodes_by_path: dict[str, dict],
    nodes_by_symbol: dict[str, list[dict]],
) -> list[dict]:
    links: list[dict] = []
    for row in rows:
        text = " ".join(
            str(row.get(part) or "")
            for part in ("requirement_id", "text", "rationale")
        )
        for token in _path_tokens(text):
            node = nodes_by_path.get(token)
            if node is None:
                continue
            links.append(
                _trace_row(
                    kind=kind,
                    from_id=row["id"],
                    to_id=node["id"],
                    confidence=1.0,
                    witness=token,
                    provenance="deterministic:exact-path",
                    promoted=True,
                    source_path=row["source_path"],
                    source_line=row["source_line"],
                )
            )
        exact_symbols = set(_symbol_tokens(text))
        for symbol in sorted(exact_symbols):
            matches = nodes_by_symbol.get(symbol, [])
            if not matches:
                continue
            promoted = len(matches) == 1
            for node in matches:
                links.append(
                    _trace_row(
                        kind=kind,
                        from_id=row["id"],
                        to_id=node["id"],
                        confidence=1.0 if promoted else 0.5,
                        witness=symbol,
                        provenance=(
                            "deterministic:exact-symbol"
                            if promoted
                            else "deterministic:ambiguous-symbol"
                        ),
                        promoted=promoted,
                        source_path=row["source_path"],
                        source_line=row["source_line"],
                    )
                )
        for symbol in _weak_symbol_mentions(text, exact_symbols):
            for node in nodes_by_symbol.get(symbol, []):
                links.append(
                    _trace_row(
                        kind=kind,
                        from_id=row["id"],
                        to_id=node["id"],
                        confidence=0.25,
                        witness=symbol,
                        provenance="deterministic:lexical-symbol",
                        promoted=False,
                        source_path=row["source_path"],
                        source_line=row["source_line"],
                    )
                )
    return links


def _requirement_test_links(
    requirements: list[dict], tests: list[dict]
) -> list[dict]:
    links: list[dict] = []
    requirements_by_id = {row["requirement_id"]: row for row in requirements}
    for test in tests:
        requirement = requirements_by_id.get(test["target"])
        if requirement is None:
            continue
        links.append(
            _trace_row(
                kind="requirement-covered-by",
                from_id=requirement["id"],
                to_id=test["id"],
                confidence=1.0,
                witness=requirement["requirement_id"],
                provenance="deterministic:exact-req-id",
                promoted=True,
                source_path=test["source_path"],
                source_line=test["source_line"],
            )
        )
    return links


def _ci_test_links(
    requirements: list[dict], tests: list[dict], jobs: list[dict]
) -> list[dict]:
    links: list[dict] = []
    requirements_by_id = {row["requirement_id"]: row for row in requirements}
    for job in jobs:
        command = str(job.get("command") or "")
        for test in tests:
            if test["source_path"] not in command:
                continue
            links.append(
                _trace_row(
                    kind="workflow-runs-test",
                    from_id=job["id"],
                    to_id=test["id"],
                    confidence=1.0,
                    witness=test["source_path"],
                    provenance="deterministic:ci-command-invokes-test",
                    promoted=True,
                    source_path=job["source_path"],
                    source_line=job["source_line"],
                )
            )
            requirement = requirements_by_id.get(test["target"])
            if requirement is None:
                continue
            links.append(
                _trace_row(
                    kind="requirement-gated-by",
                    from_id=requirement["id"],
                    to_id=job["id"],
                    confidence=1.0,
                    witness=test["source_path"],
                    provenance="deterministic:ci-command-invokes-test",
                    promoted=True,
                    source_path=job["source_path"],
                    source_line=job["source_line"],
                )
            )
    return links


def _test_code_links(root: Path, tests: list[dict], nodes_by_path: dict[str, dict]) -> list[dict]:
    tests_by_path: dict[str, list[dict]] = {}
    for test in tests:
        tests_by_path.setdefault(test["source_path"], []).append(test)

    links: list[dict] = []
    for source_path, path_tests in sorted(tests_by_path.items()):
        path = root / source_path
        if path.suffix != ".py" or not path.exists():
            continue
        for module, source_line in _python_imports(path):
            module_path = _module_path_for_import(module)
            if module_path is None:
                continue
            node = nodes_by_path.get(module_path)
            if node is None:
                continue
            for test in path_tests:
                links.append(
                    _trace_row(
                        kind="test-exercises-code",
                        from_id=test["id"],
                        to_id=node["id"],
                        confidence=1.0,
                        witness=module,
                        provenance="deterministic:python-import",
                        promoted=True,
                        source_path=source_path,
                        source_line=source_line,
                    )
                )
    return links


def _requirement_key(row: dict) -> tuple[str, str, str]:
    return (
        str(row.get("capability") or ""),
        str(row.get("requirement_id") or ""),
        str(row.get("source_path") or ""),
    )


def _decision_key(row: dict) -> tuple[str, int]:
    return (
        str(row.get("source_path") or ""),
        int(row.get("source_line") or 0),
    )


def _manifest_requirement(
    entry: dict, requirements_by_key: dict[tuple[str, str, str], dict]
) -> dict:
    source_path = _normalise_path(entry.get("requirement_source")) or ""
    key = (
        str(entry.get("capability") or ""),
        str(entry.get("requirement_id") or ""),
        source_path,
    )
    requirement = requirements_by_key.get(key)
    if requirement is None:
        raise ValueError(
            "traceability manifest references unknown requirement "
            f"{key[1]} in {key[2] or '<missing source>'}"
        )
    return requirement


def _manifest_decision(
    entry: dict, decisions_by_key: dict[tuple[str, int], dict]
) -> dict:
    source_path = _normalise_path(entry.get("decision_source")) or ""
    try:
        source_line = int(entry.get("decision_line") or 0)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "traceability manifest decision_line must be an integer"
        ) from exc
    key = (source_path, source_line)
    decision = decisions_by_key.get(key)
    if decision is None:
        raise ValueError(
            "traceability manifest references unknown design decision "
            f"{source_path or '<missing source>'}:{source_line or '<missing line>'}"
        )
    return decision


def _manifest_source(
    entry: dict,
    *,
    requirements_by_key: dict[tuple[str, str, str], dict],
    decisions_by_key: dict[tuple[str, int], dict],
) -> dict:
    has_requirement = any(
        entry.get(key) is not None
        for key in ("capability", "requirement_id", "requirement_source")
    )
    has_decision = any(
        entry.get(key) is not None
        for key in ("decision_source", "decision_line")
    )
    if has_requirement and has_decision:
        raise ValueError(
            "traceability manifest link must reference either a requirement "
            "or a design decision, not both"
        )
    if has_decision:
        return _manifest_decision(entry, decisions_by_key)
    return _manifest_requirement(entry, requirements_by_key)


def _test_selectors(tests: list[dict]) -> dict[str, dict]:
    selectors: dict[str, dict] = {}
    for test in tests:
        selectors[test["id"]] = test
        selectors[f"{test['source_path']}::{test['name']}"] = test
    return selectors


def _ci_job_selectors(jobs: list[dict]) -> dict[str, dict]:
    selectors: dict[str, dict] = {}
    for job in jobs:
        selectors[job["id"]] = job
        selectors[f"{job['source_path']}:{job['id'].rsplit(':', 1)[-1]}"] = job
    return selectors


def _reviewed_code_target(
    target: str,
    *,
    root: Path,
    nodes: list[dict],
    nodes_by_path: dict[str, dict],
) -> str:
    normalized = _normalise_path(target) or target.strip()
    for node in nodes:
        if node["id"] == normalized:
            return node["id"]
    module_node = nodes_by_path.get(normalized)
    if module_node is not None:
        return module_node["id"]
    source_matches = [node for node in nodes if node.get("source_file") == normalized]
    if len(source_matches) == 1:
        return source_matches[0]["id"]
    if not (root / normalized).is_file():
        raise ValueError(
            f"traceability manifest references unknown code path {normalized}"
        )
    return normalized


def _reviewed_target_id(
    entry: dict,
    *,
    tests_by_selector: dict[str, dict],
    jobs_by_selector: dict[str, dict],
    root: Path,
    nodes: list[dict],
    nodes_by_path: dict[str, dict],
) -> str:
    kind = str(entry.get("kind") or "")
    target = str(entry.get("target") or "").strip()
    expected_type = _REVIEWED_TRACE_TARGETS.get(kind)
    if expected_type is None:
        raise ValueError(f"unsupported reviewed traceability kind: {kind}")
    target_type = str(entry.get("target_type") or expected_type)
    if target_type != expected_type:
        raise ValueError(
            f"reviewed traceability kind {kind} expects target_type "
            f"{expected_type}, got {target_type}"
        )

    if expected_type == "code-path":
        return _reviewed_code_target(
            target,
            root=root,
            nodes=nodes,
            nodes_by_path=nodes_by_path,
        )
    if expected_type == "test-case":
        test = tests_by_selector.get(target)
        if test is None:
            raise ValueError(
                f"traceability manifest references unknown test case {target}"
            )
        return test["id"]
    if expected_type == "ci-job":
        job = jobs_by_selector.get(target)
        if job is None:
            raise ValueError(f"traceability manifest references unknown CI job {target}")
        return job["id"]
    raise AssertionError(expected_type)


def _reviewed_traceability_links(
    root: Path,
    *,
    requirements: list[dict],
    decisions: list[dict],
    tests: list[dict],
    jobs: list[dict],
    nodes: list[dict],
    nodes_by_path: dict[str, dict],
) -> list[dict]:
    requirements_by_key = {
        _requirement_key(requirement): requirement for requirement in requirements
    }
    decisions_by_key = {_decision_key(decision): decision for decision in decisions}
    tests_by_selector = _test_selectors(tests)
    jobs_by_selector = _ci_job_selectors(jobs)
    links: list[dict] = []

    for path in _traceability_manifest_paths(root):
        source_path = _rel(path, root)
        lines = _read_text_lines(path)
        try:
            manifest = json.loads("\n".join(lines))
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid traceability manifest {source_path}") from exc
        if manifest.get("version") != 1:
            raise ValueError(f"unsupported traceability manifest version {source_path}")
        entries = manifest.get("links")
        if not isinstance(entries, list):
            raise ValueError(f"traceability manifest has no links list {source_path}")

        for entry in entries:
            if not isinstance(entry, dict):
                raise ValueError(f"traceability manifest link is not an object {source_path}")
            source = _manifest_source(
                entry,
                requirements_by_key=requirements_by_key,
                decisions_by_key=decisions_by_key,
            )
            target = str(entry.get("target") or "").strip()
            if not target:
                raise ValueError("traceability manifest link has no target")
            links.append(
                _trace_row(
                    kind=str(entry.get("kind") or ""),
                    from_id=source["id"],
                    to_id=_reviewed_target_id(
                        entry,
                        tests_by_selector=tests_by_selector,
                        jobs_by_selector=jobs_by_selector,
                        root=root,
                        nodes=nodes,
                        nodes_by_path=nodes_by_path,
                    ),
                    confidence=1.0,
                    witness=str(entry.get("witness") or target),
                    provenance="reviewed:traceability-manifest",
                    promoted=True,
                    source_path=source_path,
                    source_line=_line_for_manifest_entry(lines, entry),
                )
            )
    return links


def extract_traceability_links(root: Path) -> list[dict]:
    """Return deterministic evidence-first ``traceability-link`` rows."""
    root = Path(root)
    requirements = extract_openspec_requirements(root)
    decisions = extract_design_decisions(root)
    tests = extract_test_cases(root)
    jobs = extract_ci_jobs(root)
    nodes = _code_nodes(root)
    nodes_by_path = _module_nodes_by_path(nodes)
    nodes_by_symbol = _code_nodes_by_symbol(nodes)

    rows: list[dict] = []
    rows.extend(
        _design_code_links(
            requirements,
            kind="requirement-implemented-by",
            nodes_by_path=nodes_by_path,
            nodes_by_symbol=nodes_by_symbol,
        )
    )
    rows.extend(
        _design_code_links(
            decisions,
            kind="decision-constrains-code",
            nodes_by_path=nodes_by_path,
            nodes_by_symbol=nodes_by_symbol,
        )
    )
    rows.extend(_requirement_test_links(requirements, tests))
    rows.extend(_ci_test_links(requirements, tests, jobs))
    rows.extend(_test_code_links(root, tests, nodes_by_path))
    rows.extend(
        _reviewed_traceability_links(
            root,
            requirements=requirements,
            decisions=decisions,
            tests=tests,
            jobs=jobs,
            nodes=nodes,
            nodes_by_path=nodes_by_path,
        )
    )
    rows.sort(key=lambda row: row["id"])
    return rows


def extract_design_kg_snapshot(root: Path) -> dict[str, list[dict]]:
    """Return a canonical design-intelligence snapshot for golden tests."""
    return {
        "design-requirement": extract_openspec_requirements(root),
        "design-scenario": extract_openspec_scenarios(root),
        "design-decision": extract_design_decisions(root),
        "operator-command": extract_operator_commands(root),
        "test-case": extract_test_cases(root),
        "ci-workflow": extract_ci_workflows(root),
        "ci-job": extract_ci_jobs(root),
    }


def project_design_requirements(root: Path, store) -> None:
    """Load OpenSpec requirement and scenario rows."""
    store.load("design-requirement", extract_openspec_requirements(root))
    store.load("design-scenario", extract_openspec_scenarios(root))


def project_design_docs(root: Path, store) -> None:
    """Load markdown design decisions and operator commands."""
    store.load("design-decision", extract_design_decisions(root))
    store.load("operator-command", extract_operator_commands(root))


def project_tests_and_ci(root: Path, store) -> None:
    """Load test-case, ci-workflow, and ci-job rows."""
    store.load("test-case", extract_test_cases(root))
    store.load("ci-workflow", extract_ci_workflows(root))
    store.load("ci-job", extract_ci_jobs(root))


def project_traceability_links(root: Path, store) -> None:
    """Load deterministic traceability-link rows."""
    store.load("traceability-link", extract_traceability_links(root))
