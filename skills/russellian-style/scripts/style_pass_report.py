"""Aggregate the four linters into a single auditable style-pass-report.md."""
from __future__ import annotations

import re
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
from .lint_concrete_instance_density import lint_concrete_instance_density, _concrete_count
from .lint_epistemic_precision import lint_epistemic_precision
from .lint_paragraph_motion import lint_paragraph_motion, classify_paragraph
from .lint_ai_staccato import lint_ai_staccato
from .retrieve_corpus_anchor import retrieve_anchor
from .score_russell_delta import score_file as _russell_delta_score_file

_CONCESSION_TURN_RE = re.compile(
    r"\b(But|However|Yet|Still|Nevertheless|Even so|It is true that)\b",
    re.IGNORECASE,
)

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


def _sentence_length_fano(path: Path) -> float:
    from statistics import mean, pvariance
    text = load_markdown(path)
    lengths = [len(s.text.split()) for s in iter_sentences(text)]
    if len(lengths) < 2:
        return 0.0
    mu = mean(lengths)
    if mu == 0:
        return 0.0
    return round(pvariance(lengths) / mu, 3)


def _concrete_instance_count(text: str) -> int:
    """Absolute concrete-instance count using NER-enabled spaCy pipeline."""
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    return sum(_concrete_count(p) for p in paras)


def _positive_checks(source_path: Path, motion_finds: list[dict], concrete_finds: list[dict],
                     staccato_finds: list[dict]) -> dict:
    import math
    text = load_markdown(source_path)
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    shapes = [classify_paragraph(p) for p in paras] if paras else []
    if shapes:
        counts: dict[str, int] = {}
        for s in shapes:
            counts[s] = counts.get(s, 0) + 1
        total = len(shapes)
        entropy = 0.0
        for k in counts.values():
            p = k / total
            entropy -= p * math.log2(p)
        max_entropy = math.log2(len(counts)) if len(counts) > 1 else 1.0
        diversity = round(entropy / max_entropy, 3) if max_entropy > 0 else 0.0
    else:
        diversity = 0.0
    concession = sum(len(_CONCESSION_TURN_RE.findall(p)) for p in paras)
    rep_rate = 0.0
    para_count = max(len(paras), 1)
    for f in staccato_finds:
        if f.get("rule") == "negation-affirmation-template":
            rep_rate = round(f.get("match_count", 0) / para_count, 3)
            break
    return {
        "sentence_length_fano": _sentence_length_fano(source_path),
        "paragraph_shape_diversity": diversity,
        "concession_turn_count": concession,
        "concrete_instance_count": _concrete_instance_count(text),
        "template_repetition_rate": rep_rate,
    }


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
    staccato = lint_ai_staccato(source_path)
    for f in burst + ai_vocab + concrete + episteme + motion + staccato:
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

    russell_delta = _russell_delta_score_file(source_path)

    return {
        "path": str(source_path),
        "negative_metrics": negative_metrics,
        "vitality_metrics": vitality_metrics,
        "positive_checks": _positive_checks(source_path, motion, concrete, staccato),
        "findings": findings,
        "corpus_anchors": corpus_anchors,
        "russell_delta": russell_delta,
    }


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print("usage: style_pass_report.py <source.md> <out.md>", file=sys.stderr)
        return 2
    write_report(Path(argv[1]), Path(argv[2]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
