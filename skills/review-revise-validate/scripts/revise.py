"""Stage 4 of the review-revise-validate cycle.

Two phases:
- Phase A (revise): dispatch the reviser persona via gemma4:31b; parse JSON.
- Phase B (apply): exact-match string replacement of original->revised in chapter.

Satisfies REQ-REVISE-001 (cycle runs end-to-end) and REQ-REVISE-002 (apply
failures halt the pipeline with a clear error).
"""
from __future__ import annotations

import json
import re
from pathlib import Path


_FENCED_JSON_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)
_BARE_OBJECT_RE = re.compile(r"(\{[\s\S]*\})", re.DOTALL)


def _extract_json_object(response: str) -> dict:
    """Extract a JSON object from an LLM response, tolerating code fences."""
    fenced = _FENCED_JSON_RE.search(response)
    if fenced:
        candidate = fenced.group(1)
    else:
        bare = _BARE_OBJECT_RE.search(response)
        if not bare:
            raise ValueError("no JSON object found in response")
        candidate = bare.group(1)
    try:
        return json.loads(candidate)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON parse failed: {e}") from e


class ApplyError(Exception):
    """Raised when one or more revisions cannot be applied verbatim."""
    def __init__(self, message: str, failures: list[dict]) -> None:
        super().__init__(message)
        self.failures = failures


def apply_revisions(
    *,
    chapter_path: Path,
    revisions_obj: dict,
    output_path: Path,
) -> None:
    """Apply paragraph-level rewrites; write revised chapter to output_path.

    Raises ApplyError if any `original` doesn't appear verbatim in the chapter.
    All-or-nothing: on failure, output_path is not written.
    """
    chapter_text = chapter_path.read_text(encoding="utf-8")
    revisions = revisions_obj.get("revisions", [])

    failures: list[dict] = []
    for entry in revisions:
        original = entry.get("original", "")
        if original not in chapter_text:
            failures.append({
                "cluster_id": entry.get("cluster_id", "(unknown)"),
                "original_snippet": original[:100],
                "reason": "verbatim match not found in chapter",
            })

    if failures:
        raise ApplyError(
            f"{len(failures)} revision(s) could not be applied: "
            f"{', '.join(f['cluster_id'] for f in failures)}",
            failures=failures,
        )

    revised = chapter_text
    for entry in revisions:
        revised = revised.replace(entry["original"], entry["revised"], 1)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(revised, encoding="utf-8")


import argparse
import sys
from llm_infra.persona_dispatch import run_persona_via_ollama


def _skill_root() -> Path:
    """Resolve this skill's root, where personas/ and assets/ live."""
    return Path(__file__).resolve().parent.parent


def run_revise(
    *,
    chapter_path: Path,
    instructions_path: Path,
    output_dir: Path,
    chapter_id: str,
    model: str = "gemma4:31b",
) -> None:
    """Run Phase A (dispatch reviser) and Phase B (apply revisions) end-to-end."""
    output_dir.mkdir(parents=True, exist_ok=True)
    skill_root = _skill_root()
    template_path = skill_root / "assets" / "reviser-prompt-template.md"
    persona_path = skill_root / "personas" / "reviser.md"

    chapter_md = chapter_path.read_text(encoding="utf-8")
    revision_instructions = instructions_path.read_text(encoding="utf-8")

    slots = {
        "persona_body": persona_path.read_text(encoding="utf-8").split("---", 2)[2].strip(),
        "display_name": "Reviser",
        "role": "targeted-paragraph-rewriter",
        "persona_id": "reviser",
        "chapter_id": chapter_id,
        "chapter_md": chapter_md,
        "revision_instructions": revision_instructions,
        "output_path": str(output_dir / "revisions-raw-response.md"),
    }

    raw_response_path = output_dir / "revisions-raw-response.md"
    result = run_persona_via_ollama(
        persona_id="reviser",
        template_path=template_path,
        persona_path=persona_path,
        slots=slots,
        output_path=raw_response_path,
        model=model,
    )
    raw_response = raw_response_path.read_text(encoding="utf-8")

    revisions_obj = _extract_json_object(raw_response)
    revisions_json_path = output_dir / "revisions.json"
    revisions_json_path.write_text(
        json.dumps(revisions_obj, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    revised_chapter_path = output_dir / "revised-chapter.md"
    try:
        apply_revisions(
            chapter_path=chapter_path,
            revisions_obj=revisions_obj,
            output_path=revised_chapter_path,
        )
    except ApplyError as e:
        failures_path = output_dir / "revisions-apply-failures.json"
        failures_path.write_text(
            json.dumps({"failures": e.failures}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"[revise] APPLY FAILED -- {e}", file=sys.stderr)
        print(f"[revise] failures written to {failures_path}", file=sys.stderr)
        raise

    print(f"[revise] {result.elapsed_seconds:.1f}s; "
          f"{len(revisions_obj.get('revisions', []))} revisions applied; "
          f"-> {revised_chapter_path}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chapter", type=Path, required=True)
    parser.add_argument("--instructions", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--chapter-id", type=str, required=True)
    parser.add_argument("--model", default="gemma4:31b")
    args = parser.parse_args(argv)

    try:
        run_revise(
            chapter_path=args.chapter,
            instructions_path=args.instructions,
            output_dir=args.output_dir,
            chapter_id=args.chapter_id,
            model=args.model,
        )
    except ApplyError:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
