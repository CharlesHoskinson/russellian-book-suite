"""Stage-4 per-ticket Healer dispatcher (v5.1: one agent per ticket).

v5.0 dispatched one Healer agent per chapter and gave it the full chapter
plus every ticket; in practice these agents stalled at the 600 s subagent
budget when a chapter had many tickets.  v5.1 fixes this by dispatching
one Healer agent per *individual ticket*: each payload is small (< 2 KB),
self-contained, and bounded to 3 iterations.

Workflow:

    python -m scripts.healer <workspace> --prepare
        [--llm-backend {subagent|ollama}] [--model MODEL] [--num-predict N]
        Read sentinel.json, emit one JSON payload per hard-fail ticket
        under ``<workspace>/qa/healer-payloads/<ticket-id>.json``.
        Hard-fail tickets are prepared first; soft-gate tickets are
        skipped (Stage 3 surfaces them for human review).

    python -m scripts.healer <workspace> --apply <patch-result.json>
        Record a patch result on disk, increment the iteration counter,
        refuse to re-emit a payload once it has hit 3 iterations.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

MAX_ITERATIONS = 3
SPAN_BEFORE = 4   # context lines before the offending line
SPAN_AFTER = 6    # context lines after


@dataclass
class HealerPayload:
    """Small (< 2 KB) self-contained packet sent to one Healer agent."""

    ticket_id: str
    chapter: str
    class_: str
    severity: str
    where: str
    detail: str
    fix_hint: str
    chapter_path: str | None
    span: str
    span_start_line: int
    iteration: int
    max_iterations: int = MAX_ITERATIONS
    meta: dict[str, Any] = field(default_factory=dict)


def _chapter_draft_path(workspace: Path, chapter: str) -> Path | None:
    """Locate the source chapter draft for span extraction."""
    if not chapter.startswith("ch-"):
        return None
    p = workspace / "chapters" / "drafts" / chapter / "draft.md"
    return p if p.exists() else None


def _extract_span(text: str, where: str) -> tuple[int, str]:
    """Return ``(start_line, span_text)`` for a ``where`` like 'line 42'.

    Falls back to the first ~10 lines of the chapter when ``where`` cannot
    be parsed (e.g. ``"footnote refs"``, ``"doc-level"``).
    """
    lines = text.splitlines()
    line_no: int | None = None
    if where.startswith("line "):
        try:
            line_no = int(where.split()[1])
        except (IndexError, ValueError):
            line_no = None
    if line_no is None:
        end = min(len(lines), 10)
        return 1, "\n".join(lines[:end])
    idx = max(0, line_no - 1)
    start = max(0, idx - SPAN_BEFORE)
    end = min(len(lines), idx + SPAN_AFTER + 1)
    return start + 1, "\n".join(lines[start:end])


def _state_path(workspace: Path) -> Path:
    """JSON file tracking iteration count per ticket-id (idempotent)."""
    return workspace / "qa" / "healer-state.json"


def _load_state(workspace: Path) -> dict[str, int]:
    path = _state_path(workspace)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _save_state(workspace: Path, state: dict[str, int]) -> None:
    path = _state_path(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def prepare_payloads(workspace: Path) -> list[HealerPayload]:
    """Emit one JSON payload per hard-fail ticket; respect the 3-iter cap."""
    sentinel_path = workspace / "qa" / "sentinel.json"
    if not sentinel_path.exists():
        raise FileNotFoundError(sentinel_path)
    report = json.loads(sentinel_path.read_text(encoding="utf-8"))
    out_dir = workspace / "qa" / "healer-payloads"
    out_dir.mkdir(parents=True, exist_ok=True)
    state = _load_state(workspace)
    out: list[HealerPayload] = []
    for ticket in report.get("hard_fail_tickets", []):
        tid = ticket["ticket_id"]
        iteration = state.get(tid, 0)
        if iteration >= MAX_ITERATIONS:
            continue
        chapter = ticket.get("chapter", "doc")
        draft = _chapter_draft_path(workspace, chapter)
        if draft is not None:
            start_line, span = _extract_span(draft.read_text(encoding="utf-8"),
                                              ticket.get("where", ""))
            chapter_path = str(draft)
        else:
            start_line, span, chapter_path = 0, "", None
        payload = HealerPayload(
            ticket_id=tid,
            chapter=chapter,
            class_=ticket.get("class", "D?"),
            severity=ticket.get("severity", "critical"),
            where=ticket.get("where", ""),
            detail=ticket.get("detail", ""),
            fix_hint=ticket.get("fix_hint", ""),
            chapter_path=chapter_path,
            span=span,
            span_start_line=start_line,
            iteration=iteration + 1,
            meta={"source": ticket.get("source", "")},
        )
        out.append(payload)
        # rename class_ -> class for JSON output
        d = asdict(payload)
        d["class"] = d.pop("class_")
        (out_dir / f"{tid}.json").write_text(json.dumps(d, indent=2), encoding="utf-8")
        state[tid] = iteration + 1
    _save_state(workspace, state)
    return out


def apply_patch_result(workspace: Path, result_path: Path) -> dict[str, Any]:
    """Record a Healer patch result and report convergence status.

    The patch-result JSON is produced by the Healer subagent; this function
    only persists it under ``qa/healer-results/`` and increments the state.
    Re-running with the same result file is idempotent (overwrite).
    """
    payload = json.loads(Path(result_path).read_text(encoding="utf-8"))
    tid = payload.get("ticket_id")
    if not tid:
        raise ValueError(f"patch result missing ticket_id: {result_path}")
    out_dir = workspace / "qa" / "healer-results"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{tid}.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    state = _load_state(workspace)
    iteration = state.get(tid, 1)
    return {"ticket_id": tid, "iteration": iteration,
            "exhausted": iteration >= MAX_ITERATIONS}


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="healer.py",
        description="Stage-4 per-ticket Healer dispatcher.",
    )
    parser.add_argument("workspace", help="Path to the book workspace root.")
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--prepare",
        action="store_true",
        help="Read sentinel.json, emit one JSON payload per hard-fail ticket.",
    )
    mode_group.add_argument(
        "--apply",
        metavar="PATCH_RESULT_JSON",
        help="Record a Healer patch result and increment the iteration counter.",
    )
    parser.add_argument(
        "--llm-backend",
        choices=["subagent", "ollama"],
        default="subagent",
        help=(
            "Backend capability matrix: "
            "subagent — PAYLOAD_ONLY; writes JSON payloads to "
            "<workspace>/qa/healer-payloads/. Does NOT execute the LLM. "
            "The controlling agent consumes payloads via Task-tool dispatch. "
            "ollama — UNSUPPORTED; this stage's outputs are designed for "
            "fresh-context subagent repair. Exits with code 2."
        ),
    )
    parser.add_argument("--model", default="gemma4:31b",
                        help="Ollama model (only used when --llm-backend=ollama).")
    parser.add_argument(
        "--num-predict",
        type=int,
        default=None,
        help="Caps Ollama output tokens (only used when --llm-backend=ollama).",
    )
    args = parser.parse_args(argv[1:])

    workspace = Path(args.workspace).resolve()

    if args.prepare:
        if args.llm_backend == "ollama":
            print(
                "[healer] --llm-backend ollama is unsupported for this stage — "
                "this stage prepares payloads for subagent dispatch only.",
                file=sys.stderr,
            )
            return 2
        payloads = prepare_payloads(workspace)
        print(f"Prepared {len(payloads)} healer payload(s) at "
              f"{workspace / 'qa' / 'healer-payloads'}")
        for p in payloads:
            print(f"  {p.ticket_id} [{p.class_}/{p.severity}] iter {p.iteration}"
                  f"/{p.max_iterations}")
        return 0

    # --apply mode
    info = apply_patch_result(workspace, Path(args.apply))
    print(f"Recorded patch for {info['ticket_id']} "
          f"(iter {info['iteration']}/{MAX_ITERATIONS})"
          + ("  EXHAUSTED" if info["exhausted"] else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
