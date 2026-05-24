"""Tests for run_cycle orchestrator — mocks subprocess invocations."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scripts.run_cycle import run_cycle


def test_run_cycle_stage1_invokes_book_review_with_correct_args(tmp_path):
    """Stage 1 subprocess-invokes book-review review_pass with expected args."""
    chapter = tmp_path / "ch.md"
    chapter.write_text("...", encoding="utf-8")
    workspace = tmp_path / "ws"

    with patch("scripts.run_cycle.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout=b"", stderr=b"")
        with patch("scripts.run_cycle._parse_critical_count", return_value=0):
            # Force early-exit on zero Critical findings (REQ-REVISE-007)
            run_cycle(
                chapter_id="ch-01",
                draft_path=chapter,
                workspace_dir=workspace,
                model="gemma4:31b",
            )
        # First call should be book-review review_pass
        first_call_args = mock_run.call_args_list[0].args[0]
        joined = " ".join(str(a) for a in first_call_args)
        assert "review_pass" in joined
        assert "--chapter-id" in first_call_args
        assert "ch-01" in first_call_args
        assert "--llm-backend" in first_call_args
        assert "ollama" in first_call_args


def test_run_cycle_stages_5_and_6_invoked_when_critical_present(tmp_path):
    """When Critical > 0, all 6 stages invoke; cycle-report.md is written."""
    chapter = tmp_path / "ch.md"
    chapter.write_text("Paragraph one with a listicle abstract.\n", encoding="utf-8")
    workspace = tmp_path / "ws"

    def fake_subprocess(cmd, *args, **kwargs):
        cmd_str = " ".join(str(c) for c in cmd)
        if "review_pass" in cmd_str:
            out_idx = cmd.index("--output-dir") + 1
            out_dir = Path(cmd[out_idx])
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "persona-review-gottlieb.md").write_text(
                "---\npersona: gottlieb\nverdict: NEEDS_WORK\n---\n## Critical findings\n- a thing\n",
                encoding="utf-8",
            )
        elif "aggregate_reviews" in cmd_str:
            out_idx = cmd.index("--output") + 1
            out = Path(cmd[out_idx])
            critical = 2 if "before" in str(out) else 1
            out.write_text(
                f"# Persona Review - ch-01\n\n## Severity counts\n- Critical: {critical}\n",
                encoding="utf-8",
            )
        return MagicMock(returncode=0, stdout=b"", stderr=b"")

    with patch("scripts.run_cycle.subprocess.run", side_effect=fake_subprocess), \
         patch("scripts.run_cycle._stage3_synthesize") as mock_synth, \
         patch("scripts.run_cycle._stage4_revise") as mock_revise:
        def revise_side_effect(*, chapter_path, instructions_path, output_dir, chapter_id, model):
            (output_dir / "revised-chapter.md").write_text(
                "Paragraph one argues the point.\n", encoding="utf-8")
        mock_revise.side_effect = revise_side_effect

        rc = run_cycle(
            chapter_id="ch-01",
            draft_path=chapter,
            workspace_dir=workspace,
            model="gemma4:31b",
        )

    assert rc == 0
    assert mock_synth.called
    assert mock_revise.called
    cycle_report = workspace / "cycle-report.md"
    assert cycle_report.exists()
    report_text = cycle_report.read_text(encoding="utf-8")
    assert "Critical" in report_text
    # Critical dropped 2 -> 1 -> forward
    assert "moved the chapter forward" in report_text or "(-1)" in report_text


def test_run_cycle_invokes_claim_validation_when_workspace_has_ledger(tmp_path):
    """When workspace has claims/ledger.jsonl, book-knowledge claim validation runs."""
    chapter = tmp_path / "ch.md"
    chapter.write_text("Paragraph one.\n", encoding="utf-8")
    workspace = tmp_path / "ws"
    claims = tmp_path / "claims"
    claims.mkdir()
    (claims / "ledger.jsonl").write_text('{"id": "c1"}\n', encoding="utf-8")

    def fake_subprocess(cmd, *args, **kwargs):
        cmd_str = " ".join(str(c) for c in cmd)
        if "review_pass" in cmd_str:
            out_idx = cmd.index("--output-dir") + 1
            Path(cmd[out_idx]).mkdir(parents=True, exist_ok=True)
            (Path(cmd[out_idx]) / "persona-review-gottlieb.md").write_text(
                "---\npersona: gottlieb\n---\n", encoding="utf-8")
        elif "aggregate_reviews" in cmd_str:
            out_idx = cmd.index("--output") + 1
            critical = 2 if "before" in str(cmd[out_idx]) else 0
            Path(cmd[out_idx]).write_text(
                f"## Severity counts\n- Critical: {critical}\n", encoding="utf-8")
        elif "claim_validator" in cmd_str:
            return MagicMock(returncode=0, stdout="validated 3 claims\n", stderr="")
        return MagicMock(returncode=0, stdout=b"", stderr=b"")

    with patch("scripts.run_cycle.subprocess.run", side_effect=fake_subprocess), \
         patch("scripts.run_cycle._stage3_synthesize"), \
         patch("scripts.run_cycle._stage4_revise") as mock_revise:
        def revise_side_effect(*, chapter_path, output_dir, **kwargs):
            (output_dir / "revised-chapter.md").write_text("revised.\n", encoding="utf-8")
        mock_revise.side_effect = revise_side_effect

        rc = run_cycle(
            chapter_id="ch-01",
            draft_path=chapter,
            workspace_dir=workspace,
            model="gemma4:31b",
        )

    assert rc == 0
    cycle_report = (workspace / "cycle-report.md").read_text(encoding="utf-8")
    assert "Post-apply claim validation" in cycle_report
    assert "validated 3 claims" in cycle_report
