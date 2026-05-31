# skill_api.py
"""Public surface of the syntopical-metabook skill.

v0.3 exports all five capabilities: acquire, synthesize, lens, gap, govern.
"""
API_VERSION = (0, 3)

# Acquire
from scripts.acquire.expand_seeds import expand_seeds  # noqa: E402
from scripts.acquire.rank_candidates import rank  # noqa: E402
from scripts.acquire.triage import triage  # noqa: E402
from scripts.acquire.veto import apply_veto  # noqa: E402
from scripts.acquire.download_and_ingest import download_and_ingest  # noqa: E402
from scripts.acquire.pipeline import run_acquire  # noqa: E402

# Synthesize
from scripts.synthesize.topic_map import build_topic_map  # noqa: E402
from scripts.synthesize.disputed_questions import build_disputed_questions  # noqa: E402
from scripts.synthesize.concept_reconcile import build_concept_reconciliation  # noqa: E402
from scripts.synthesize.run_synthesize import run_synthesize  # noqa: E402

# Lens
from scripts.lens.project_lens import project_lens  # noqa: E402

# Gap
from scripts.gap.coverage_report import build_coverage_report  # noqa: E402
from scripts.gap.feed_acquire import seed_from_gap_report  # noqa: E402

# Govern
from scripts.governance.build_positions import build_positions  # noqa: E402
from scripts.governance.render_per_rule import render_per_rule  # noqa: E402
from scripts.governance.render_consensus_map import render_consensus_map  # noqa: E402
from scripts.governance.render_adversarial import render_adversarial  # noqa: E402
from scripts.governance.induction_gate import governance_filter, GateDecision  # noqa: E402

__all__ = [
    "API_VERSION",
    "expand_seeds", "rank", "triage", "apply_veto", "download_and_ingest", "run_acquire",
    "build_topic_map", "build_disputed_questions", "build_concept_reconciliation", "run_synthesize",
    "project_lens",
    "build_coverage_report", "seed_from_gap_report",
    "build_positions", "render_per_rule", "render_consensus_map",
    "render_adversarial", "governance_filter", "GateDecision",
]
