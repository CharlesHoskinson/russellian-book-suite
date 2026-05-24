"""Stage 4 of the review-revise-validate cycle.

Two phases:
- Phase A (revise): dispatch the reviser persona once per cluster via gemma4:31b; parse JSON.
- Phase B (apply): exact-match string replacement of original->revised in chapter.

Satisfies REQ-REVISE-001 (cycle runs end-to-end) and REQ-REVISE-002 (apply
failures halt the pipeline with a clear error).
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
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


@dataclass
class InstructionCluster:
    cluster_id: str  # e.g. "C01"
    body_md: str     # the whole cluster section verbatim (from "## Cluster ..." through next "## " or EOF)


def _parse_clusters(instructions_md: str) -> list[InstructionCluster]:
    """Split a revision-instructions markdown into per-cluster blocks.

    The 'Unanchored findings' section (if present) is NOT included — that's
    treated separately (currently skipped; future iteration may dispatch it
    as a single 'guidance' call).
    """
    clusters: list[InstructionCluster] = []
    # Match "## Cluster CNN (...)" headers; capture the cluster id and the
    # body that follows up to the next "## " header.
    pattern = re.compile(
        r"^##\s+Cluster\s+(C\d+)\b(?P<body>.*?)(?=\n##\s+|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    for m in pattern.finditer(instructions_md):
        cluster_id = m.group(1)
        # Include the heading line in the body for the reviser's context
        heading_start = m.start()
        full_block = instructions_md[heading_start:m.end()].rstrip()
        clusters.append(InstructionCluster(cluster_id=cluster_id, body_md=full_block))
    return clusters


import argparse
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
    """Run Phase A (per-cluster dispatch) and Phase B (apply all revisions)."""
    output_dir.mkdir(parents=True, exist_ok=True)
    skill_root = _skill_root()
    template_path = skill_root / "assets" / "reviser-prompt-template.md"
    persona_path = skill_root / "personas" / "reviser.md"

    chapter_md = chapter_path.read_text(encoding="utf-8")
    instructions_md = instructions_path.read_text(encoding="utf-8")

    clusters = _parse_clusters(instructions_md)
    if not clusters:
        print("[revise] no clusters in instructions; nothing to do", file=sys.stderr)
        # Still write an empty revisions.json + identity-copy revised-chapter.md
        (output_dir / "revisions.json").write_text(
            json.dumps({"revisions": [], "unresolved": []}, indent=2), encoding="utf-8")
        (output_dir / "revised-chapter.md").write_text(chapter_md, encoding="utf-8")
        return

    print(f"[revise] dispatching {len(clusters)} cluster(s) one at a time", file=sys.stderr)

    aggregated_revisions: list[dict] = []
    aggregated_unresolved: list[dict] = []
    raw_responses: list[str] = []  # for diagnostic capture

    persona_body = persona_path.read_text(encoding="utf-8").split("---", 2)[2].strip()

    for i, cluster in enumerate(clusters, start=1):
        print(f"[revise] cluster {i}/{len(clusters)}: {cluster.cluster_id}", file=sys.stderr)
        slots = {
            "persona_body": persona_body,
            "display_name": "Reviser",
            "role": "targeted-paragraph-rewriter",
            "persona_id": "reviser",
            "chapter_id": chapter_id,
            "chapter_md": chapter_md,
            "revision_instructions": cluster.body_md,  # ONLY this cluster
            "output_path": str(output_dir / f"raw-{cluster.cluster_id}.md"),
        }
        raw_response_path = output_dir / f"raw-{cluster.cluster_id}.md"
        try:
            run_persona_via_ollama(
                persona_id="reviser",
                template_path=template_path,
                persona_path=persona_path,
                slots=slots,
                output_path=raw_response_path,
                model=model,
            )
            raw_response = raw_response_path.read_text(encoding="utf-8")
            raw_responses.append(f"=== {cluster.cluster_id} ===\n{raw_response}")

            try:
                obj = _extract_json_object(raw_response)
            except ValueError as e:
                print(f"[revise] cluster {cluster.cluster_id}: JSON parse failed — {e}; skipping",
                      file=sys.stderr)
                aggregated_unresolved.append({
                    "cluster_id": cluster.cluster_id,
                    "reason": f"reviser produced invalid JSON: {e}",
                })
                continue

            # Per cluster, the reviser returns {"revisions": [...], "unresolved": [...]}
            cluster_revs = obj.get("revisions", [])
            cluster_unres = obj.get("unresolved", [])
            # Stamp cluster_id on each revision (in case the model forgot)
            for r in cluster_revs:
                r.setdefault("cluster_id", cluster.cluster_id)
            aggregated_revisions.extend(cluster_revs)
            aggregated_unresolved.extend(cluster_unres)
            print(f"[revise] cluster {cluster.cluster_id}: {len(cluster_revs)} revision(s), "
                  f"{len(cluster_unres)} unresolved", file=sys.stderr)

        except Exception as e:
            print(f"[revise] cluster {cluster.cluster_id}: dispatch FAILED — {e}; skipping",
                  file=sys.stderr)
            aggregated_unresolved.append({
                "cluster_id": cluster.cluster_id,
                "reason": f"reviser dispatch failed: {e}",
            })

    # Write the aggregated revisions.json + concatenated raw responses
    revisions_obj = {"revisions": aggregated_revisions, "unresolved": aggregated_unresolved}
    (output_dir / "revisions.json").write_text(
        json.dumps(revisions_obj, indent=2, ensure_ascii=False), encoding="utf-8")
    (output_dir / "revisions-raw-response.md").write_text(
        "\n\n".join(raw_responses), encoding="utf-8")

    # Phase B: apply (may raise ApplyError)
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
        print(f"[revise] APPLY FAILED — {e}", file=sys.stderr)
        print(f"[revise] failures written to {failures_path}", file=sys.stderr)
        raise

    print(f"[revise] dispatched {len(clusters)} clusters; "
          f"{len(aggregated_revisions)} revisions applied; "
          f"{len(aggregated_unresolved)} unresolved; "
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
