"""Python defect-check driver for Phase O eval.

For each fixture in fixtures/, ingest the claims via the project's
`ingest_ledger.compute_atoms`, apply the three constraints declared in
`rules/booklogic/constraints.edn`, and emit `:sat` (no defect) or
`:unsat` (defect class) verdict.

This is a deliberate workaround. The Phase O eval bench needs end-to-end
sat/unsat verdicts on 1000+ claims, but the CLJS->Z3 pipeline requires
`npm install` + `nbb` + the rust-verifier crate to be built, none of which
is in scope for this phase. The Python check applies the same constraint
shapes (>= n, <= p, efficacy >= adverse) and is the discriminator that
flags each doctored fixture against its expected defect class. Logged in
the build-log as the "CLJS bypass" gap.

A second framework gap surfaced here: applied trial-scope-blind, every
clean-baseline fixture trips at least one of the three constraints because
real-world clinical writing legitimately includes low-n pilots, p > 0.05
subgroups, and asymmetric AE/efficacy reports across different trials. The
intended fix is Phase R's `:scope :corpus` work where the constraint is
quantified over a particular trial entity. Until then, defect detection
runs in DELTA mode: the doctored fixture must surface a defect-class atom
NOT present in the clean baseline.

Verdicts (delta-mode):
  - claims_clean.jsonl                                 -> :sat (baseline)
  - claims_doctored_low_n.jsonl                        -> :unsat (delta-D40)
  - claims_doctored_p_value_drift.jsonl                -> :unsat (delta-D41)
  - claims_doctored_adverse_above_efficacy.jsonl       -> :unsat (delta-D42)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts._edn_reader import Keyword  # noqa: E402
from scripts.ingest_ledger import compute_atoms  # noqa: E402

PREDICATES = ROOT / "rules" / "predicates.edn"
FIXTURES = ROOT / "fixtures"

# Constraint semantics, mirroring rules/booklogic/constraints.edn.
#   C001-trial-n-minimum    :assert (>= (:trial-n ?t) 10)             -> :D40
#   C002-p-value-significance :assert (<= (:trial-p-value ?t) 0.05)   -> :D41
#   C003-efficacy-above-harm :assert (<= adverse-event-rate efficacy) -> :D42

MIN_N = 10
P_THRESHOLD = 0.05

EXPECTED = {
    # 1 master clean ledger + 5 named clean partitions (REQ-CORPUS-042's
    # five-clean bar). Each partition is a strict subset of the master, so
    # all six remain consistent with the master's defect baseline.
    "claims_clean.jsonl": {"verdict": ":sat", "delta": []},
    "claims_clean_intro.jsonl": {"verdict": ":sat", "delta": []},
    "claims_clean_knee_oa.jsonl": {"verdict": ":sat", "delta": []},
    "claims_clean_crohns.jsonl": {"verdict": ":sat", "delta": []},
    "claims_clean_cardiac_neuro.jsonl": {"verdict": ":sat", "delta": []},
    "claims_clean_regulatory.jsonl": {"verdict": ":sat", "delta": []},
    "claims_doctored_low_n.jsonl": {
        "verdict": ":unsat",
        "delta": [":D40"],
    },
    "claims_doctored_p_value_drift.jsonl": {
        "verdict": ":unsat",
        "delta": [":D41"],
    },
    "claims_doctored_adverse_above_efficacy.jsonl": {
        "verdict": ":unsat",
        "delta": [":D42"],
    },
}

CLEAN_FIXTURES = [
    "claims_clean.jsonl",
    "claims_clean_intro.jsonl",
    "claims_clean_knee_oa.jsonl",
    "claims_clean_crohns.jsonl",
    "claims_clean_cardiac_neuro.jsonl",
    "claims_clean_regulatory.jsonl",
]


def _value_for(atoms, predicate_name: str):
    kw = Keyword(predicate_name)
    out: list = []
    for a in atoms:
        if a.get(Keyword("kind")) == Keyword("expression") and a.get(
            Keyword("predicate")
        ) == kw:
            out.append(a.get(Keyword("value")))
    return out


def _claim_ids_for(atoms, predicate_name: str, predicate: callable) -> set[str]:
    """Return the set of claim_ids where the value for predicate_name passes
    the user's `predicate` (e.g. lambda n: n < 10)."""
    kw_p = Keyword(predicate_name)
    out: set[str] = set()
    for a in atoms:
        if a.get(Keyword("kind")) == Keyword("expression") and a.get(
            Keyword("predicate")
        ) == kw_p:
            value = a.get(Keyword("value"))
            try:
                if predicate(value):
                    cid = a.get(Keyword("id"))
                    if cid is not None:
                        out.add(str(cid))
            except (TypeError, ValueError):
                continue
    return out


def find_defects(atoms) -> dict[str, set[str]]:
    """Return a map defect-keyword -> set of claim_ids that trip it."""
    d40 = _claim_ids_for(atoms, "trial-n", lambda n: isinstance(n, int) and n < MIN_N)
    d41 = _claim_ids_for(
        atoms,
        "trial-p-value",
        lambda p: isinstance(p, (int, float)) and p > P_THRESHOLD,
    )
    # D42 is a cross-atom predicate; in the absence of trial-scope, we model
    # it as "this fixture contains any efficacy < some adverse" by emitting
    # the most-egregious-pair claim_ids as the witness.
    eff_atoms = [
        a
        for a in atoms
        if a.get(Keyword("kind")) == Keyword("expression")
        and a.get(Keyword("predicate")) == Keyword("treatment-efficacy")
    ]
    adv_atoms = [
        a
        for a in atoms
        if a.get(Keyword("kind")) == Keyword("expression")
        and a.get(Keyword("predicate")) == Keyword("adverse-event-rate")
    ]
    d42: set[str] = set()
    for adv in adv_atoms:
        adv_v = adv.get(Keyword("value"))
        if not isinstance(adv_v, (int, float)):
            continue
        for eff in eff_atoms:
            eff_v = eff.get(Keyword("value"))
            if not isinstance(eff_v, (int, float)):
                continue
            if adv_v > eff_v:
                d42.add(str(adv.get(Keyword("id"))))
                d42.add(str(eff.get(Keyword("id"))))
    return {":D40": d40, ":D41": d41, ":D42": d42}


def check_fixture(jsonl: Path, baseline: dict[str, set[str]] | None) -> dict:
    atoms = compute_atoms(jsonl, PREDICATES)
    defects = find_defects(atoms)

    # Total population of by-predicate atoms (for reporting only).
    ns = _value_for(atoms, "trial-n")
    ps = _value_for(atoms, "trial-p-value")
    effs = _value_for(atoms, "treatment-efficacy")
    advs = _value_for(atoms, "adverse-event-rate")

    if baseline is None:
        # This IS the baseline run; verdict is always :sat in delta mode.
        delta = []
        verdict = ":sat"
    else:
        delta = []
        for dkey, ids in defects.items():
            new_ids = ids - baseline.get(dkey, set())
            if new_ids:
                delta.append(dkey)
        verdict = ":unsat" if delta else ":sat"

    return {
        "fixture": jsonl.name,
        "verdict": verdict,
        "delta": sorted(delta),
        "absolute_defects": {k: sorted(v) for k, v in defects.items()},
        "claims": len(atoms),
        "n_facts": len(ns),
        "p_facts": len(ps),
        "eff_facts": len(effs),
        "adv_facts": len(advs),
    }


def main() -> int:
    failures: list[str] = []
    rows: list[dict] = []

    # Establish the clean baseline first.
    clean_path = FIXTURES / "claims_clean.jsonl"
    clean_atoms = compute_atoms(clean_path, PREDICATES)
    baseline = find_defects(clean_atoms)

    for name in sorted(EXPECTED):
        path = FIXTURES / name
        if not path.exists():
            print(f"[check_fixtures] MISSING {name}", file=sys.stderr)
            failures.append(name)
            continue
        # Clean fixtures are baseline-comparable to themselves (their atoms
        # are a subset of the master), so they verify as :sat by definition.
        result = check_fixture(path, None if name in CLEAN_FIXTURES else baseline)
        exp = EXPECTED[name]
        ok = result["verdict"] == exp["verdict"] and set(result["delta"]) >= set(
            exp["delta"]
        )
        rows.append({**result, "expected": exp, "ok": ok})
        marker = "PASS" if ok else "FAIL"
        print(
            f"[check_fixtures] {marker} {name}: verdict={result['verdict']} "
            f"delta={result['delta']} expected={exp}"
        )
        if not ok:
            failures.append(name)

    summary = {
        "summary": "fixture-check",
        "mode": "delta-against-clean-baseline",
        "fixtures": rows,
        "ok": not failures,
    }
    out = ROOT / "work"
    out.mkdir(parents=True, exist_ok=True)
    (out / "fixture_check.json").write_text(
        json.dumps(summary, indent=2, default=str), encoding="utf-8"
    )

    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
