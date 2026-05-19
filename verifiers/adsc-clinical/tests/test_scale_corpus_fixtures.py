"""REQ-CORPUS-042: 5 clean + 3 doctored fixtures, each doctored class distinct."""
from __future__ import annotations

from pathlib import Path

from tests.check_fixtures import (
    CLEAN_FIXTURES,
    EXPECTED,
    check_fixture,
    compute_atoms,
    find_defects,
)
from scripts.ingest_ledger import compute_atoms as _ca  # noqa: F401  (re-export)


def test_make_ci_green_on_five_clean_three_doctored(project_root: Path) -> None:
    fixtures = project_root / "fixtures"
    clean_count = sum(1 for n in CLEAN_FIXTURES if (fixtures / n).exists())
    assert clean_count >= 5, f"only {clean_count} clean fixtures present"

    doctored = [
        n for n in EXPECTED if n.startswith("claims_doctored_")
    ]
    assert len(doctored) == 3, f"need exactly 3 doctored fixtures, got {doctored}"

    # Each doctored fixture must fire a distinct defect class.
    classes = []
    for n in doctored:
        exp = EXPECTED[n]
        classes.extend(exp["delta"])
    assert len(set(classes)) == 3, (
        f"doctored fixtures must cover 3 distinct defect classes, got {classes}"
    )

    # Sat/unsat behaviour holds.
    clean_atoms = compute_atoms(fixtures / "claims_clean.jsonl",
                                project_root / "rules" / "predicates.edn")
    baseline = find_defects(clean_atoms)
    for n in CLEAN_FIXTURES:
        path = fixtures / n
        if not path.exists():
            continue
        result = check_fixture(path, None)
        assert result["verdict"] == ":sat", f"{n} → {result['verdict']}, want :sat"
    for n in doctored:
        result = check_fixture(fixtures / n, baseline)
        assert result["verdict"] == ":unsat", f"{n} → {result['verdict']}, want :unsat"
        assert set(result["delta"]) >= set(EXPECTED[n]["delta"]), (
            f"{n} delta {result['delta']} missing {EXPECTED[n]['delta']}"
        )
