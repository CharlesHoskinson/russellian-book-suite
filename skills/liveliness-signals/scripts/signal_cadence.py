"""Advisory cadence-corridor scorer: rewards rhythmic variety vs the register CV."""
from __future__ import annotations
from statistics import mean, pstdev


def score(sentences, register, profile) -> dict:
    lengths = [s.n_alpha for s in sentences if s.n_alpha > 0]
    findings: list[dict] = []
    if len(lengths) < 3:
        return {"signal": "cadence", "score": 0.0, "findings": findings}
    mu = mean(lengths)
    cv = pstdev(lengths) / mu if mu else 0.0
    corpus_cv = 0.5
    try:
        corpus_cv = float(profile["registers"][register]["cadence"]["cv"]) or 0.5
    except Exception:
        pass
    if cv < 0.5 * corpus_cv:
        findings.append({"flag": "metronomic", "passage_cv": round(cv, 4), "corpus_cv": round(corpus_cv, 4)})
    elif cv > 2.0 * corpus_cv:
        findings.append({"flag": "erratic", "passage_cv": round(cv, 4), "corpus_cv": round(corpus_cv, 4)})
    # reward peaks at parity with corpus cv, decays away from it
    ratio = cv / corpus_cv if corpus_cv else 0.0
    sc = max(0.0, 1.0 - abs(1.0 - min(ratio, 2.0)))
    return {"signal": "cadence", "score": round(sc, 4), "findings": findings,
            "passage_cv": round(cv, 4), "corpus_cv": round(corpus_cv, 4)}
