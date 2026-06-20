"""Tests for the live KG prose eval gate (REQ-EVAL-008..013)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.eval_metrics import FAMILIES
from scripts.live_eval_gate import score_live_build, write_live_build_report


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
        newline="\n",
    )


def _hash_tree(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _make_build(
    tmp_path: Path,
    *,
    chapters: tuple[str, ...] = ("ch-01",),
    gold_for: set[str] | None = None,
    low_recall: set[str] | None = None,
) -> Path:
    root = tmp_path / "live-build"
    gold_chapters = set(chapters) if gold_for is None else set(gold_for)
    low_recall_chapters = low_recall or set()
    ledger_rows: list[dict] = []

    for chapter_id in chapters:
        claim_id = f"clm-{chapter_id}-001"
        span_id = f"span-{chapter_id}-001"
        assertion_id = f"wa-{chapter_id}-001"
        fact_id = f"fact-{chapter_id}-001"
        chapter_dir = root / "chapters" / "drafts" / chapter_id

        ledger_rows.append(
            {
                "claim_id": claim_id,
                "canonical_text": f"{chapter_id} claim-first prose is measurable.",
                "status": "verified",
            }
        )
        _write_json(
            chapter_dir / "chapter-retrieval-bundle.json",
            {
                "schema": "chapter-retrieval-bundle/v1",
                "chapter-id": chapter_id,
                "load-bearing-claims": [
                    {
                        "claim-id": claim_id,
                        "status": "verified",
                        "text": f"{chapter_id} claim-first prose is measurable.",
                        "source-span-ids": [span_id],
                    },
                    {
                        "claim-id": f"clm-{chapter_id}-002",
                        "status": "verified",
                        "text": f"{chapter_id} has a second selected claim.",
                        "source-span-ids": [f"span-{chapter_id}-002"],
                    },
                ],
                "source-span-anchors": [
                    {
                        "claim-id": claim_id,
                        "span-id": span_id,
                        "doc-id": f"doc-{chapter_id}",
                        "locator-text": f"{chapter_id} claim-first prose is measurable.",
                    }
                ],
                "code-links": {},
                "warnings": [],
                "contradiction-alerts": [],
                "proof-traces": [],
            },
        )
        (chapter_dir / "draft.md").write_text(
            f"{chapter_id} claim-first prose is measurable.\n",
            encoding="utf-8",
            newline="\n",
        )
        _write_jsonl(
            chapter_dir / "writer-assertions.jsonl",
            [
                {
                    "id": assertion_id,
                    "asserts_claim": [claim_id],
                    "cites_span": [span_id],
                    "sentence_text": f"{chapter_id} claim-first prose is measurable.",
                    "citation_check_status": "full",
                }
            ],
        )
        _write_jsonl(
            chapter_dir / "draft-atomic-facts.jsonl",
            [
                {
                    "id": fact_id,
                    "text": f"{chapter_id} claim-first prose is measurable.",
                    "claim_id": claim_id,
                    "novel_draft_claim": None,
                }
            ],
        )

        if chapter_id in gold_chapters:
            required_span_ids = [span_id]
            if chapter_id in low_recall_chapters:
                required_span_ids.append(f"missing-{span_id}")
            _write_json(
                root / "eval-gold" / chapter_id / "attribution-spans.json",
                {
                    "schema": "kg-prose-attribution-gold/v1",
                    "sentences": [
                        {
                            "assertion_id": assertion_id,
                            "required_span_ids": required_span_ids,
                        }
                    ],
                },
            )

    _write_jsonl(root / "claims" / "ledger.jsonl", ledger_rows)
    return root


def test_live_eval_runs_over_real_build(tmp_path: Path) -> None:
    """REQ-EVAL-008: live eval scores a real build-shaped snapshot."""
    build_root = _make_build(tmp_path)
    report_path = write_live_build_report(build_root, tmp_path / "report.json")

    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert report["schema"] == "kg-prose-live-build-report/v1"
    chapter = report["chapters"]["ch-01"]
    assert set(chapter["metrics"]["families"]) == set(FAMILIES)
    assert chapter["side-products"]["prose_character_count"] > 0
    assert chapter["side-products"]["writer_assertion_count"] == 1


def test_build_report_per_chapter_and_aggregate(tmp_path: Path) -> None:
    """REQ-EVAL-009: report carries per-chapter and aggregate families."""
    build_root = _make_build(tmp_path, chapters=("ch-01", "ch-02"))

    report = score_live_build(build_root)

    assert set(report["chapters"]) == {"ch-01", "ch-02"}
    for chapter in report["chapters"].values():
        assert set(chapter["metrics"]["families"]) == set(FAMILIES)
    assert set(report["aggregate"]["families"]) == set(FAMILIES)
    assert report["aggregate"]["families"]["attribution"]["chapter_count"] == 2
    assert report["aggregate"]["families"]["factuality"]["atomic_fact_count"] == 2


def test_comparative_metric_reports_delta(tmp_path: Path) -> None:
    """REQ-EVAL-010: declared live comparative records both arms and delta."""
    build_root = _make_build(tmp_path)
    config = {
        "comparatives": {
            "ch-01": {
                "claim-first-vs-flat": {
                    "control_flat_claims": ["flat-control-claim"]
                }
            }
        }
    }

    report = score_live_build(build_root, config=config)
    comparison = report["chapters"]["ch-01"]["metrics"]["comparatives"][
        "claim-first-vs-flat"
    ]

    assert comparison["treatment"]["arm"] == "claim-first-bundle"
    assert comparison["control"]["arm"] == "flat-claim-list"
    assert comparison["delta"] == 1
    assert report["aggregate"]["comparatives"]["claim-first-vs-flat"]["delta"] == 1
    assert score_live_build(build_root)["aggregate"]["comparatives"] == {}


def test_absent_gold_reports_unscored(tmp_path: Path) -> None:
    """REQ-EVAL-011: absent gold is unscored and excluded from aggregate."""
    build_root = _make_build(
        tmp_path,
        chapters=("ch-01", "ch-02"),
        gold_for={"ch-01"},
    )

    report = score_live_build(build_root)
    ch01_attribution = report["chapters"]["ch-01"]["metrics"]["families"][
        "attribution"
    ]
    ch02_attribution = report["chapters"]["ch-02"]["metrics"]["families"][
        "attribution"
    ]
    aggregate = report["aggregate"]["families"]["attribution"]

    assert ch01_attribution["status"] == "scored"
    assert ch02_attribution["status"] == "unscored"
    assert "score" not in ch02_attribution
    assert aggregate["scored_chapter_count"] == 1
    assert aggregate["unscored_chapter_count"] == 1
    assert aggregate["counts"]["gold_spans"] == 1


def test_advisory_default_and_gated_subset(tmp_path: Path) -> None:
    """REQ-EVAL-012: live eval is advisory until a baselined gate is configured."""
    build_root = _make_build(tmp_path, low_recall={"ch-01"})

    advisory = score_live_build(build_root)
    unbaselined = score_live_build(
        build_root,
        config={
            "gating": {
                "metrics": {
                    "attribution.recall": {
                        "threshold": 0.75,
                        "operator": ">=",
                        "baselined": False,
                    }
                }
            }
        },
    )
    gated = score_live_build(
        build_root,
        config={
            "gating": {
                "metrics": {
                    "attribution.recall": {
                        "threshold": 0.75,
                        "operator": ">=",
                        "baselined": True,
                    }
                }
            }
        },
    )

    assert advisory["gating"]["mode"] == "advisory"
    assert advisory["gating"]["status"] == "pass"
    assert unbaselined["gating"]["mode"] == "advisory"
    assert unbaselined["gating"]["status"] == "pass"
    assert gated["aggregate"]["families"]["attribution"]["macro"]["recall"] == 0.5
    assert gated["gating"]["mode"] == "gating"
    assert gated["gating"]["status"] == "fail"
    assert gated["gating"]["failures"][0]["metric"] == "attribution.recall"


def test_read_only_and_deterministic(tmp_path: Path) -> None:
    """REQ-EVAL-013: scoring is read-only and reproducible."""
    build_root = _make_build(tmp_path)

    before = _hash_tree(build_root)
    first = score_live_build(build_root)
    middle = _hash_tree(build_root)
    second = score_live_build(build_root)
    after = _hash_tree(build_root)

    assert before == middle == after
    assert first == second
