#!/usr/bin/env python3
"""REQ-EVAL-050..055: onboarding benchmark harness.

Runs a fresh-agent eval against a doc bundle plus a domain prompt,
captures milestones (extract-passed, ci-passed), tool-call counts,
and doc gaps. Designed to support multiple agent backends:

- ``stub``         deterministic in-process simulator (CI signal)
- ``claude-code``  subprocess wrapper (TODO: wire in follow-up)
- ``codex``        subprocess wrapper (TODO: wire in follow-up)

The stub backend lets CI exercise the harness pathway without an LLM
runtime dependency. The regression gate at the bottom is bypassed for
stub runs.
"""
from __future__ import annotations

import argparse
import csv
import datetime
import subprocess
import sys
import time
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SKILL_ROOT.parent.parent
DOC_BUNDLE: list[Path] = [
    SKILL_ROOT / "SKILL.md",
    SKILL_ROOT / "SUPPORT_MATRIX.md",
    REPO_ROOT / "docs" / "booklogic-dsl-reference.md",
    *sorted((SKILL_ROOT / "references").rglob("*.md")),
]


def _utcnow_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _utcnow_stamp() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")


def assemble_doc_bundle() -> str:
    """Concatenate every doc-bundle file, skipping missing ones quietly."""
    parts: list[str] = []
    for path in DOC_BUNDLE:
        if path.exists():
            parts.append(f"## {path.relative_to(REPO_ROOT)}\n\n{path.read_text(encoding='utf-8')}")
    return "\n\n---\n\n".join(parts)


def detect_doc_gaps(agent_log_dir: Path) -> list[str]:
    """REQ-EVAL-052: placeholder; real implementation lands in the next commit."""
    _ = agent_log_dir
    return []


def run_agent(
    prompt_path: Path,
    backend: str,
    workspace: Path,
    timeout_seconds: int = 1800,
) -> dict:
    """Run one agent attempt; return milestone + tool-call data.

    The shape of the returned dict matches the CSV schema in
    ``design.md``. For ``stub`` we simulate a deterministic success in
    well under a second. For ``claude-code`` and ``codex`` we record a
    ``TODO`` outcome and leave the subprocess wiring to a follow-up.
    """
    workspace.mkdir(parents=True, exist_ok=True)
    prompt_text = prompt_path.read_text(encoding="utf-8")
    doc_bundle = assemble_doc_bundle()
    (workspace / "doc-bundle.md").write_text(doc_bundle, encoding="utf-8")
    (workspace / "domain-spec.md").write_text(prompt_text, encoding="utf-8")
    log_dir = workspace / "logs"
    log_dir.mkdir(exist_ok=True)
    start = time.monotonic()
    result: dict = {
        "prompt": prompt_path.stem,
        "backend": backend,
        "started_at": _utcnow_iso(),
        "extract_passed_at": "",
        "ci_passed_at": "",
        "tool_calls": 0,
        "errors": 0,
        "outcome": "PENDING",
        "wall_time_seconds": 0.0,
        "doc_gaps": "",
    }
    try:
        if backend == "stub":
            # Deterministic success path: short sleep to keep wall-time non-zero.
            time.sleep(0.01)
            result["extract_passed_at"] = round(time.monotonic() - start, 4)
            result["ci_passed_at"] = round(time.monotonic() - start, 4)
            result["tool_calls"] = 12
            result["errors"] = 0
            result["outcome"] = "SUCCESS"
        elif backend == "claude-code":
            # Real-backend wiring intentionally deferred to a follow-up
            # change; the harness shape is what's under test here.
            _todo_real_backend_run(prompt_path, workspace, timeout_seconds)
            result["outcome"] = "TODO_real_backend_not_implemented"
        elif backend == "codex":
            _todo_real_backend_run(prompt_path, workspace, timeout_seconds)
            result["outcome"] = "TODO_real_backend_not_implemented"
        else:
            raise ValueError(f"unknown backend: {backend!r}")
    except subprocess.TimeoutExpired:
        # REQ-EVAL-053: record timeout, keep harness moving.
        if result["extract_passed_at"]:
            result["outcome"] = "TIMEOUT_ci"
        else:
            result["outcome"] = "TIMEOUT_extract"
    result["wall_time_seconds"] = round(time.monotonic() - start, 4)
    result["doc_gaps"] = ";".join(detect_doc_gaps(log_dir))
    return result


def _todo_real_backend_run(prompt_path: Path, workspace: Path, timeout_seconds: int) -> None:
    """Placeholder for real-backend wiring (claude-code, codex).

    The shape of the eventual implementation:

        subprocess.run(
            [backend_cli, "--input", str(workspace / "domain-spec.md")],
            cwd=workspace, timeout=timeout_seconds, check=False,
            stdout=(workspace / "logs" / "agent.log").open("wb"),
        )

    For now we no-op so the harness still produces a row.
    """
    _ = (prompt_path, workspace, timeout_seconds)


def write_csv(results: list[dict], out_path: Path) -> None:
    if not results:
        out_path.write_text("", encoding="utf-8")
        return
    with out_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--prompts",
        type=Path,
        default=Path(__file__).resolve().parent / "prompts",
        help="directory of *.md prompt files",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).resolve().parent / "runs",
        help="directory to write per-run workspaces and CSVs into",
    )
    ap.add_argument(
        "--backend",
        default="stub",
        choices=["stub", "claude-code", "codex"],
    )
    ap.add_argument(
        "--timeout-seconds",
        type=int,
        default=1800,
        help="per-prompt agent invocation timeout",
    )
    args = ap.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)
    stamp = _utcnow_stamp()
    results: list[dict] = []
    prompts = sorted(args.prompts.glob("*.md"))
    if not prompts:
        print(f"no prompts found under {args.prompts}", file=sys.stderr)
        return 2
    for prompt_path in prompts:
        workspace = args.out / stamp / prompt_path.stem
        r = run_agent(prompt_path, args.backend, workspace, args.timeout_seconds)
        results.append(r)
    csv_path = args.out / f"{stamp}.csv"
    write_csv(results, csv_path)
    print(f"wrote {csv_path}", file=sys.stderr)
    # REQ-EVAL-055: regression gate on non-stub backends only.
    reach_ci = sum(1 for r in results if r["outcome"] == "SUCCESS")
    reach_rate = reach_ci / max(len(results), 1)
    if args.backend != "stub" and reach_rate < 0.80:
        print(
            f"REGRESSION: ci-reach rate {reach_rate:.0%} below 80% threshold",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
