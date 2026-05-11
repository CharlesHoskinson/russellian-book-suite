"""Aggregate the four linters into a single auditable style-pass-report.md."""
from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from .lint_common import iter_sentences, load_markdown
from .lint_hedges import lint_hedges
from .lint_passive_voice import lint_passive_voice
from .lint_signal_density import lint_signal_density
from .lint_parallel_structure import lint_parallel_structure
from .lint_listicle_abstract import lint_listicle_abstract
from .lint_sentence_rhythm import lint_sentence_rhythm

ASSETS = Path(__file__).resolve().parent.parent / "assets"


def _all_findings(path: Path) -> list[dict]:
    return (
        lint_hedges(path)
        + lint_passive_voice(path)
        + lint_signal_density(path)
        + lint_parallel_structure(path)
        + lint_listicle_abstract(path)
        + lint_sentence_rhythm(path)
    )


def _passive_voice_ratio(path: Path) -> float:
    text = load_markdown(path)
    sentences = list(iter_sentences(text))
    if not sentences:
        return 0.0
    passives = lint_passive_voice(path)
    return round(len(passives) / len(sentences), 3)


def _format_findings(findings: list[dict]) -> str:
    blocks: list[str] = []
    for f in findings:
        rule = f["rule"]
        line = f.get("line") or f.get("start_line", "?")
        sentence = f.get("sentence") or f.get("items", [{}])[0].get("item", "")
        detail = ""
        if rule == "no-hedging":
            detail = f"  (term: `{f['term']}`)"
        elif rule == "signal-density":
            detail = f"  (modifier_ratio: {f['modifier_ratio']}, budget: {f['budget']})"
        blocks.append(f"### {rule} - line {line}\n\n> {sentence}\n{detail}\n")
    return "\n".join(blocks) if blocks else "_None._"


def build_report(source_path: Path) -> str:
    template = (ASSETS / "style-pass-report.template.md").read_text(encoding="utf-8")
    findings = _all_findings(source_path)
    counts = Counter(f["rule"] for f in findings)

    rows = "\n".join(f"| {rule} | {count} |" for rule, count in sorted(counts.items())) or "| _none_ | 0 |"

    listicle_count = sum(1 for f in findings if f["rule"] in ("listicle-abstract", "listicle-anaphora"))
    rhythm_count = sum(1 for f in findings if f["rule"] in ("rhythm-uniform-length", "rhythm-repeated-opening"))

    return template.format(
        source_path=str(source_path),
        timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        total_findings=len(findings),
        rule_summary_rows=rows,
        findings_blocks=_format_findings(findings),
        hedge_count=counts.get("no-hedging", 0),
        passive_voice_ratio=_passive_voice_ratio(source_path),
        modifier_violations=counts.get("signal-density", 0),
        parallel_violations=counts.get("parallel-structure", 0),
        listicle_abstract_count=listicle_count,
        rhythm_violations=rhythm_count,
    )


def write_report(source_path: Path, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(build_report(source_path), encoding="utf-8")


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print("usage: style_pass_report.py <source.md> <out.md>", file=sys.stderr)
        return 2
    write_report(Path(argv[1]), Path(argv[2]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
