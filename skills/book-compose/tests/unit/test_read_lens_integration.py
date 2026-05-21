"""Integration test: book-compose.read_lens must successfully parse a lens
file produced by syntopical-metabook.project_lens."""
import pytest

pytestmark = pytest.mark.windows_canary

import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[4]  # repo root

@pytest.fixture
def synthesized_workspace(tmp_path):
    """Build a minimal workspace with all syntopical inputs project_lens needs."""
    ws = tmp_path / "ws"
    chap = ws / "chapters" / "ch-01"
    chap.mkdir(parents=True)
    (chap / "contract.yaml").write_text(
        "id: ch-01\ntitle: Finality\nsummary: ...\ntags: [finality]\n",
        encoding="utf-8")
    (chap / "thesis-tree.yaml").write_text(
        "chapter_id: ch-01\nnodes:\n  - node_id: n1\n    statement: x\n"
        "    tags: [finality]\n    required_evidence_kind: empirical\n"
        "    parent_id: null\n", encoding="utf-8")
    syn = ws / "syntopical"
    (syn / "disputed-questions").mkdir(parents=True)
    (syn / "concepts").mkdir(parents=True)
    (syn / "topic-map.md").write_text(
        "# Topic Map\n\n## n1\n\n| slug | sources | n_verified_claims |\n"
        "|---|---|---|\n| finality | s1 | 2 |\n\n", encoding="utf-8")
    (syn / "disputed-questions" / "finality.md").write_text(
        "# Disputed: finality\n\n| Question | Position | Source | Claim-ID |\n"
        "|---|---|---|---|\n| q | yes | s1 | cl1 |\n", encoding="utf-8")
    (syn / "concepts" / "nakamoto-consensus.md").write_text(
        "# Canonical Concept: nakamoto-consensus\n\n"
        "Alternate finality is mapped here.\n", encoding="utf-8")
    return ws


def test_book_compose_reads_lens_from_project_lens_output(synthesized_workspace):
    # Insert syntopical-metabook skill path so project_lens is importable.
    sm_path = str(ROOT / "skills" / "syntopical-metabook")
    if sm_path not in sys.path:
        sys.path.insert(0, sm_path)

    # Clear any stale 'scripts' cache that might come from the rest of the
    # book-compose test suite (which imports its own scripts.* subpackage).
    for k in list(sys.modules):
        if k == "scripts" or k.startswith("scripts."):
            del sys.modules[k]

    from scripts.lens.project_lens import project_lens  # syntopical-metabook
    out = project_lens(workspace_root=synthesized_workspace, chapter_id="ch-01",
                       source_run_id="run-9-1")
    assert out.exists()

    # Clean up syntopical-metabook path and its 'scripts' module cache before
    # importing book-compose's skill_api, which lives under the same package name.
    if sm_path in sys.path:
        sys.path.remove(sm_path)
    for k in list(sys.modules):
        if k == "scripts" or k.startswith("scripts."):
            del sys.modules[k]

    # Now add book-compose to path so its skill_api is importable.
    bc_path = str(ROOT / "skills" / "book-compose")
    if bc_path not in sys.path:
        sys.path.insert(0, bc_path)

    from skill_api import read_lens, Lens

    lens = read_lens("ch-01", synthesized_workspace)
    assert isinstance(lens, Lens)
    assert lens.chapter_id == "ch-01"
    assert lens.source_run_id == "run-9-1"
    # The four sections must be non-empty (we wrote content for each)
    assert "finality" in lens.topics_md.lower()
    assert lens.disputed_md   # not empty
    assert lens.concepts_md   # not empty
    assert lens.coverage_md   # not empty
