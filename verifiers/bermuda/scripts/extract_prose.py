"""Walk chapter drafts and extract Pass A prose facts."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Callable, Optional

from scripts.prose_patterns import extract_pass_a

LlmCall = Callable[[str], str]

LLM_PROMPT_TEMPLATE = """You are extracting numeric and named-entity facts from a non-fiction chapter.

For each verifiable claim of the form "subject has/is value", emit a JSON object:

  {{"predicate": ":snake-case-predicate", "subject": ":SubjectName", "value": <int|string|bool>}}

Return ONLY a JSON array, no prose. If no claims, return [].

Chapter text:
---
{text}
---
"""


def extract_chapter(draft_path: Path) -> list[dict]:
    text = draft_path.read_text(encoding="utf-8")
    return extract_pass_a(text, source_file=str(draft_path.name))


def extract_pass_b(text: str, source_file: str,
                   llm_call: LlmCall) -> list[dict]:
    """LLM-driven extraction. Caller injects the LLM callable."""
    prompt = LLM_PROMPT_TEMPLATE.format(text=text)
    try:
        raw = llm_call(prompt)
        parsed = json.loads(raw)
    except Exception:
        return []
    if not isinstance(parsed, list):
        return []
    out = []
    for i, item in enumerate(parsed):
        if not isinstance(item, dict):
            continue
        if "predicate" not in item or "subject" not in item or "value" not in item:
            continue
        out.append({
            "kind": "expression",
            "sort": ":formula",
            "predicate": item["predicate"],
            "subject": item["subject"],
            "value": item["value"],
            "id": f"prose-{Path(source_file).stem}-llm-{i + 1:03d}",
            "source": {"file": source_file, "line": 0},
            "confidence": 0.6,
            "extractor": "llm",
        })
    return out


def extract_release(bundles_dir: Path, out_path: Path,
                    llm_call: Optional[LlmCall] = None) -> int:
    """Walk chapter-bundles/*/draft.md. Pass A always runs;
    Pass B runs only when llm_call is provided."""
    all_atoms: list[dict] = []
    for ch_dir in sorted(bundles_dir.iterdir()):
        if not ch_dir.is_dir():
            continue
        draft = ch_dir / "draft.md"
        if not draft.exists():
            continue
        text = draft.read_text(encoding="utf-8")
        source = f"{ch_dir.name}/draft.md"
        all_atoms.extend(extract_pass_a(text, source_file=source))
        if llm_call is not None:
            all_atoms.extend(extract_pass_b(text, source_file=source,
                                            llm_call=llm_call))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps({"version": 1, "atoms": all_atoms}, indent=2, sort_keys=True),
        encoding="utf-8", newline="\n",
    )
    return len(all_atoms)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundles", required=True,
                    help="Path to chapter-bundles/ (one dir per chapter, each with draft.md)")
    ap.add_argument("--out", default="work/prose-facts.edn")
    args = ap.parse_args(argv)
    n = extract_release(Path(args.bundles), Path(args.out))
    print(f"extracted {n} prose atoms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
