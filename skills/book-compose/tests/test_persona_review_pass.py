from datetime import datetime, timezone
from pathlib import Path
import yaml

from scripts.persona_review_pass import prepare_packets, aggregate


def _seed(tmp_path: Path) -> Path:
    workspace = tmp_path / "book"
    chapter_dir = workspace / "chapters" / "drafts" / "ch-01"
    chapter_dir.mkdir(parents=True, exist_ok=True)
    (workspace / "CLAUDE.md").write_text("# marker\n", encoding="utf-8")
    (chapter_dir / "draft.md").write_text("# Sample\n\nFirst paragraph.\n", encoding="utf-8")

    contracts = workspace / "chapters" / "contracts"
    contracts.mkdir(parents=True, exist_ok=True)
    (contracts / "ch-01.yaml").write_text(yaml.safe_dump({
        "chapter_id": "ch-01", "title": "Sample",
        "purpose": "purpose long enough to satisfy schema",
        "audience": "senior-engineer", "chapter_type": "reference",
        "evidence_requirements": {"minimum_verified_claims": 0, "max_unresolved_conflicts": 0},
        "acceptance_tests": ["hedge_count == 0"],
        "output_formats": ["markdown"],
    }), encoding="utf-8")
    return workspace


def test_prepare_packets_returns_five(tmp_path):
    workspace = _seed(tmp_path)
    packets = prepare_packets(workspace, "ch-01")
    assert len(packets) == 5


def test_aggregate_returns_aggregated_review(tmp_path):
    workspace = _seed(tmp_path)
    result = aggregate(workspace, "ch-01")
    assert result.severity_counts["critical"] == 0
