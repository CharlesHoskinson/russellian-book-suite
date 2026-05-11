from pathlib import Path

import yaml

from scripts.toc import build_toc, lookup_chapter


def _seed_contracts(tmp_path: Path) -> Path:
    workspace = tmp_path / "book"
    contracts = workspace / "chapters" / "contracts"
    contracts.mkdir(parents=True)
    for n, title in [(1, "Intro"), (2, "Body"), (3, "Conclusion")]:
        cid = f"ch-{n:02d}"
        contract = {
            "chapter_id": cid, "title": title,
            "purpose": "purpose long enough to pass schema",
            "audience": "senior-engineer", "chapter_type": "reference",
            "evidence_requirements": {"minimum_verified_claims": 0, "max_unresolved_conflicts": 0},
            "acceptance_tests": ["hedge_count == 0"],
            "output_formats": ["markdown"],
        }
        (contracts / f"{cid}.yaml").write_text(yaml.safe_dump(contract), encoding="utf-8")
    return workspace


def test_build_toc_lists_in_order(tmp_path):
    ws = _seed_contracts(tmp_path)
    toc = build_toc(ws)
    assert "1. **Intro**" in toc
    assert "2. **Body**" in toc
    assert "3. **Conclusion**" in toc
    # Verify ordering
    assert toc.index("Intro") < toc.index("Body") < toc.index("Conclusion")


def test_lookup_chapter_returns_number_and_title(tmp_path):
    ws = _seed_contracts(tmp_path)
    n, title = lookup_chapter(ws, "ch-02")
    assert n == 2
    assert title == "Body"
