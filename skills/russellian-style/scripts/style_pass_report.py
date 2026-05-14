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
from .lint_burstiness import lint_burstiness
from .lint_ai_vocabulary import lint_ai_vocabulary
from .lint_concrete_instance_density import lint_concrete_instance_density
from .lint_epistemic_precision import lint_epistemic_precision
from .lint_paragraph_motion import lint_paragraph_motion
from .retrieve_corpus_anchor import retrieve_anchor

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


def _russell_vitality_score(metrics: dict) -> float:
    """Composite advisory score on [0, 1]; higher is better.

    Weights and thresholds are placeholders calibrated empirically in
    the follow-up promotion spec; advisory only in v1.
    """
    pm = metrics["paragraph_motion_score"]
    bf = metrics["burstiness_fano_factor"]
    av = metrics["ai_vocabulary_violations"]
    burst_term = min(bf / 0.7, 1.0)
    av_term = max(0.0, 1.0 - av / 10.0)
    return round(pm * 0.4 + burst_term * 0.3 + av_term * 0.3, 3)


def generate_report_dict(source_path: Path) -> dict:
    """Return the full report as a dict.

    Emits both the existing negative_metrics block and the new
    vitality_metrics block. When a vitality linter fires, attaches one
    matching Russell corpus anchor under corpus_anchors. The existing
    template-based build_report() function is unchanged.
    """
    source_path = Path(source_path)

    hedges = lint_hedges(source_path)
    passives = lint_passive_voice(source_path)
    signal = lint_signal_density(source_path)
    parallel = lint_parallel_structure(source_path)
    rhythm = lint_sentence_rhythm(source_path)
    listicle = lint_listicle_abstract(source_path)

    burst = lint_burstiness(source_path)
    ai_vocab = lint_ai_vocabulary(source_path)
    concrete = lint_concrete_instance_density(source_path)
    episteme = lint_epistemic_precision(source_path)
    motion = lint_paragraph_motion(source_path)

    fano = burst[0]["fano_factor"] if burst else 0.7
    in_band = burst[0]["in_band_proportion"] if burst else 0.0
    if motion:
        pm_score = round(1.0 - motion[0].get("flat_proportion", 0.0), 3)
    else:
        pm_score = 1.0

    vitality_metrics = {
        "burstiness_fano_factor": fano,
        "in_band_proportion": in_band,
        "ai_vocabulary_violations": len(ai_vocab),
        "concrete_instance_density_violations": len(concrete),
        "epistemic_precision_violations": len(episteme),
        "paragraph_motion_score": pm_score,
    }
    vitality_metrics["russell_vitality_score"] = _russell_vitality_score(vitality_metrics)

    negative_metrics = {
        "hedge_count": len(hedges),
        "passive_voice_ratio": _passive_voice_ratio(source_path),
        "modifier_budget_violations": len(signal),
        "parallel_structure_violations": len(parallel),
        "listicle_abstract_count": len(listicle),
        "rhythm_violations": len(rhythm),
    }

    findings: list[dict] = []
    for f in hedges + passives + signal + parallel + rhythm + listicle:
        findings.append({"section": "negative", "finding": f})
    for f in burst + ai_vocab + concrete + episteme + motion:
        findings.append({"section": "vitality", "finding": f})

    corpus_anchors: list[dict] = []
    if motion:
        try:
            anchor = retrieve_anchor(rhetorical_mode="problems", seed=42)
            corpus_anchors.append({
                "for_finding": "paragraph-motion:flat_axiom_stack",
                "anchor": {
                    "corpus_id": anchor.corpus_id,
                    "source_title": anchor.source_title,
                    "rhetorical_move": anchor.rhetorical_move,
                    "calibration_lesson": anchor.calibration_lesson,
                },
            })
        except (LookupError, ValueError):
            pass

    return {
        "path": str(source_path),
        "negative_metrics": negative_metrics,
        "vitality_metrics": vitality_metrics,
        "findings": findings,
        "corpus_anchors": corpus_anchors,
    }


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print("usage: style_pass_report.py <source.md> <out.md>", file=sys.stderr)
        return 2
    write_report(Path(argv[1]), Path(argv[2]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
