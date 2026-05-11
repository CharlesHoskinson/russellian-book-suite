from datetime import datetime, timezone
from pathlib import Path
import shutil

from scripts.workspace import init_workspace, WorkspaceLayout
from scripts.ingest_pdf import ingest_pdf
from scripts.ledger import append_claim
from scripts.verify_claim import verify_claim
from scripts.project_graph import project_graph
from scripts.validate_shacl import validate_shacl
from scripts.run_competency_queries import run_competency_queries
from scripts.wiki_index_regen import wiki_index_regen

ASSETS = Path(__file__).resolve().parent.parent / "assets"


def _claim(cid: str, locator: str) -> dict:
    return {
        "claim_id": cid,
        "canonical_text": f"Claim canonical text for {cid}",
        "status": "proposed",
        "claim_type": "fact",
        "confidence": 0.9,
        "source_spans": [{"doc_id": "small", "page_index": 1, "locator_text": locator}],
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def test_full_ingest_to_release_gate(tmp_path):
    workspace = init_workspace(tmp_path / "book")
    layout = WorkspaceLayout(workspace)
    shutil.copy(ASSETS / "shapes.ttl", layout.shapes)

    ingest_pdf(Path("tests/fixtures/small.pdf"), workspace)

    append_claim(layout, _claim("clm-2026-000001", "three components"))
    append_claim(layout, _claim("clm-2026-000002", "PROV-O models"))
    append_claim(layout, _claim("clm-2026-000003", "definitely-not-in-source-text"))

    r1 = verify_claim(layout, "clm-2026-000001")
    r2 = verify_claim(layout, "clm-2026-000002")
    r3 = verify_claim(layout, "clm-2026-000003")
    assert r1.ok is True
    assert r2.ok is True
    assert r3.ok is False

    project_graph(layout)
    wiki_index_regen(layout)

    shacl = validate_shacl(layout)
    assert shacl.conforms is True, shacl.text

    findings = run_competency_queries(layout)
    assert findings["unsupported_claims"] == []
