"""Generate Russell-voice paragraphs and compare them to original Russell.

Advisory eval stage. Generation uses an injected LLM callable (no live calls).
Comparison uses the Russell-Delta scorer and the russellian-style linter battery.
"""
from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Callable, Optional

from scripts.system_prompt_loader import load as load_prompt, VALID_MODES
from scripts.liveness import npvi, liveness_summary

DEFAULT_N = 30
DEFAULT_MODE = "technical-exposition"


def build_generation_prompt(topic: str, mode: str, n: int) -> str:
    contract = load_prompt(mode)
    return (
        f"{contract}\n\n"
        f"# Task\n"
        f"Write {n} paragraphs on the following topic, observing the contract above. "
        f"Topic: {topic}\n"
        f"Output only the prose: no headings, no preamble, no numbering."
    )


def generate_paragraphs(topic: str, mode: str = DEFAULT_MODE, n: int = DEFAULT_N,
                        *, llm_call: Callable[[str], str]) -> str:
    if mode not in VALID_MODES:
        raise ValueError(f"unknown mode: {mode!r}; valid: {sorted(VALID_MODES)}")
    return llm_call(build_generation_prompt(topic, mode, n))


from scripts.score_russell_delta import score as _delta_score, load_profile, PROFILE_PATH


def _linters() -> dict:
    # Lazy import: each linter imports lint_common, which does `import spacy` at module
    # load (and spaCy's deps may be absent). Keep this module import-safe; the linters
    # load only when evaluate() actually runs.
    from scripts.lint_hedges import lint_hedges
    from scripts.lint_passive_voice import lint_passive_voice
    from scripts.lint_signal_density import lint_signal_density
    from scripts.lint_parallel_structure import lint_parallel_structure
    from scripts.lint_listicle_abstract import lint_listicle_abstract
    from scripts.lint_sentence_rhythm import lint_sentence_rhythm
    from scripts.lint_burstiness import lint_burstiness
    from scripts.lint_chassis_uniformity import lint_chassis_uniformity
    from scripts.lint_ai_vocabulary import lint_ai_vocabulary
    from scripts.lint_ai_staccato import lint_ai_staccato
    from scripts.lint_concrete_instance_density import lint_concrete_instance_density
    from scripts.lint_epistemic_precision import lint_epistemic_precision
    from scripts.lint_humanity_token_closers import lint_humanity_token_closers
    from scripts.lint_ornament import lint_ornament
    from scripts.lint_paragraph_motion import lint_paragraph_motion
    return {
        "hedges": lint_hedges,
        "passive_voice": lint_passive_voice,
        "signal_density": lint_signal_density,
        "parallel_structure": lint_parallel_structure,
        "listicle_abstract": lint_listicle_abstract,
        "sentence_rhythm": lint_sentence_rhythm,
        "burstiness": lint_burstiness,
        "chassis_uniformity": lint_chassis_uniformity,
        "ai_vocabulary": lint_ai_vocabulary,
        "ai_staccato": lint_ai_staccato,
        "concrete_instance_density": lint_concrete_instance_density,
        "epistemic_precision": lint_epistemic_precision,
        "humanity_token_closers": lint_humanity_token_closers,
        "ornament": lint_ornament,
        "paragraph_motion": lint_paragraph_motion,
    }


def _motion_variety(text: str) -> float:
    """Distinct paragraph shapes / total paragraphs, via lint_paragraph_motion's
    stdlib classifier (no spaCy)."""
    from scripts.lint_paragraph_motion import classify_paragraph
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not paras:
        return 0.0
    shapes = {classify_paragraph(p) for p in paras}
    return round(len(shapes) / len(paras), 3)


def _signals(text: str, profile: dict) -> dict:
    delta = _delta_score(text, profile)
    n_words = delta["n_words"]
    fd, name = tempfile.mkstemp(suffix=".md")
    os.close(fd)
    path = Path(name)
    try:
        path.write_text(text, encoding="utf-8")
        linters = {}
        for lname, fn in _linters().items():
            count = len(fn(path))
            per_1000 = round(count / n_words * 1000, 3) if n_words else 0.0
            linters[lname] = {"count": count, "per_1000": per_1000}
    finally:
        path.unlink(missing_ok=True)
    motion_variety = _motion_variety(text)
    concrete_per_1000 = linters.get("concrete_instance_density", {}).get("per_1000", 0.0)
    ornament_per_1000 = linters.get("ornament", {}).get("per_1000", 0.0)
    liveness = liveness_summary(npvi(text), motion_variety, concrete_per_1000, ornament_per_1000)
    return {"russell_delta": delta, "n_words": n_words, "linters": linters, "liveness": liveness}


def evaluate(generated_text: str, russell_baseline_text: Optional[str] = None,
             profile_path: Path = PROFILE_PATH) -> dict:
    profile = load_profile(profile_path)
    report = {"generated": _signals(generated_text, profile), "baseline": None}
    if russell_baseline_text is not None:
        report["baseline"] = _signals(russell_baseline_text, profile)
    return report


def run(topic: str, mode: str = DEFAULT_MODE, n: int = DEFAULT_N, *,
        llm_call: Callable[[str], str], russell_baseline_path: Optional[str] = None) -> dict:
    text = generate_paragraphs(topic, mode, n, llm_call=llm_call)
    baseline_text = None
    if russell_baseline_path:
        baseline_text = Path(russell_baseline_path).read_text(encoding="utf-8", errors="replace")
    report = evaluate(text, baseline_text)
    report["meta"] = {"topic": topic, "mode": mode, "n_requested": n}
    report["generated_text"] = text
    return report


def _delta_line(sig: dict) -> str:
    d = sig["russell_delta"]
    return (f"metric={d['metric']} delta={d['delta']} verdict={d['verdict']} "
            f"(band p50={d['band']['p50']} p90={d['band']['p90']}) words={sig['n_words']}")


def _liveness_line(sig: dict) -> str:
    lv = sig["liveness"]
    c = lv["components"]
    return (f"liveness={lv['liveness']:.2f} (cadence={c['cadence']:.2f} "
            f"motion={c['motion']:.2f} concreteness={c['concreteness']:.2f} "
            f"ornament_penalty={c['ornament_penalty']:.2f})")


def write_report(report: dict, out_path) -> None:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    meta = report.get("meta", {})
    gen = report["generated"]
    base = report.get("baseline")
    lines = [
        "# Voice-eval report",
        "",
        f"- topic: {meta.get('topic')}",
        f"- mode: {meta.get('mode')}",
        f"- paragraphs requested: {meta.get('n_requested')}",
        "",
        "## Russell-Delta",
        "",
        f"- generated: {_delta_line(gen)}",
    ]
    if base:
        lines.append(f"- russell baseline: {_delta_line(base)}")
    lines += ["", "## Liveness (advisory telemetry — not a verdict)", "",
              f"- generated: {_liveness_line(gen)}"]
    if base:
        lines.append(f"- russell baseline: {_liveness_line(base)}")
    lines += ["", "## Linter densities (per 1,000 words)", "",
              "| linter | generated | russell baseline |", "|---|---:|---:|"]
    for lname in gen["linters"]:
        g = gen["linters"][lname]["per_1000"]
        b = base["linters"][lname]["per_1000"] if base else "-"
        lines.append(f"| {lname} | {g} | {b} |")
    lines += ["", "## Generated prose", "", report.get("generated_text", "")]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: voice_eval.py <generated.md> [russell_baseline.md] [out.md]", file=sys.stderr)
        return 2
    generated = Path(argv[1]).read_text(encoding="utf-8", errors="replace")
    baseline = Path(argv[2]).read_text(encoding="utf-8", errors="replace") if len(argv) > 2 else None
    report = evaluate(generated, baseline)
    report["meta"] = {"topic": "(cli)", "mode": "(cli)", "n_requested": "(cli)"}
    report["generated_text"] = generated
    if len(argv) > 3:
        write_report(report, argv[3])
        print(f"wrote {argv[3]}")
    else:
        print(json.dumps({k: v for k, v in report.items() if k != "generated_text"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
