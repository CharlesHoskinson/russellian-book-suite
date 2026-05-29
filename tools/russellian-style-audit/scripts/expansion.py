"""Run one expansion batch and (conditionally) append to the russellian-style index.

Wraps the build-russell-corpus pipeline stages with the live LLM caller. The
operator_gate decision determines whether the verified entries are appended.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import yaml

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_BUILD_TOOL = _REPO_ROOT / "tools" / "build-russell-corpus"


def _load_build_module(name: str, *, register_as: str | None = None):
    """Load a module from the build-russell-corpus scripts dir by name.

    If register_as is given, the module is inserted into sys.modules under that
    key so that intra-package imports (``from scripts.corpus_io import ...``)
    resolve correctly when the audit's own ``scripts`` package is already on
    sys.modules.
    """
    key = register_as or f"build_corpus_{name}"
    if key in sys.modules:
        return sys.modules[key]
    spec = importlib.util.spec_from_file_location(
        key,
        _BUILD_TOOL / "scripts" / f"{name}.py",
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[key] = module
    spec.loader.exec_module(module)
    return module


# Load corpus_io first and register as scripts.corpus_io so downstream
# build-corpus modules find it when they do ``from scripts.corpus_io import …``.
_load_build_module("corpus_io", register_as="scripts.corpus_io")

_extract_candidates_mod = _load_build_module("extract_candidates")
_sentinel_mod = _load_build_module("sentinel")
_cross_check_mod = _load_build_module("cross_check")
_audit_sample_mod = _load_build_module("audit_sample")
_append_to_index_mod = _load_build_module("append_to_index")
_live_llm_mod = _load_build_module("live_llm")

extract_candidates = _extract_candidates_mod.extract_candidates
run_sentinel_batch = _sentinel_mod.run_sentinel_batch
run_cross_check_batch = _cross_check_mod.run_cross_check_batch
sample_audit = _audit_sample_mod.sample_audit
evaluate_audit_decisions = _audit_sample_mod.evaluate_audit_decisions
append_verified_to_index = _append_to_index_mod.append_verified_to_index
regenerate_corpus_map = _append_to_index_mod.regenerate_corpus_map
extract_llm = _live_llm_mod.extract_llm
cross_check_llm = _live_llm_mod.cross_check_llm


_RUSSELLIAN_STYLE_ROOT = _REPO_ROOT / "skills" / "russellian-style"
_INDEX_PATH = _RUSSELLIAN_STYLE_ROOT / "assets" / "russell-corpus" / "index.json"
_CORPUS_MAP_PATH = _RUSSELLIAN_STYLE_ROOT / "references" / "russell-corpus-map.md"
_BUILD_TOOL_ASSETS = _BUILD_TOOL / "assets"


def run_expansion_batch(
    *,
    batch_id: str,
    source_id: str,
    source_path: Path,
    n: int,
    run_dir: Path,
    operator_decision_fn,  # callable returning "halt" | list[str]
    promote: bool = False,
) -> dict:
    """Run the full expansion pipeline. Returns a dict with counts and appended-bool.

    operator_decision_fn is called once with (audit_sample_path, n_sample, n_verified)
    after the audit sample is written.

    By default (promote=False) an accepted batch is *staged* into the batch's run_dir
    and the committed russellian-style corpus assets are left untouched — a tool/audit
    run must not silently rewrite shipped skill assets. Pass promote=True to perform the
    in-place append into the canonical index + corpus map (finding
    expansion-writes-real-corpus-bypassing-runs).
    """
    run_dir.mkdir(parents=True, exist_ok=True)
    candidates_path = run_dir / "candidates.jsonl"
    verified_path = run_dir / "verified.jsonl"
    rejected_path = run_dir / "rejected.jsonl"
    sample_path = run_dir / "audit" / "sample.md"

    # Stage 1 — extract
    allow_data = yaml.safe_load((_BUILD_TOOL_ASSETS / "pd-allow-list.yaml").read_text(encoding="utf-8"))
    source_url = next(e["url"] for e in allow_data["allowed"] if e["source_id"] == source_id)

    extract_candidates(
        source_path=source_path,
        source_id=source_id,
        source_url=source_url,
        vocabulary_path=_BUILD_TOOL_ASSETS / "vocabulary.json",
        prompt_path=_BUILD_TOOL_ASSETS / "extractor-prompt.md",
        out_path=candidates_path,
        n=n,
        llm_call=extract_llm,
    )
    n_candidates = sum(1 for _ in candidates_path.read_text(encoding="utf-8").splitlines() if _.strip()) if candidates_path.exists() else 0

    # Stage 2 — sentinel
    run_sentinel_batch(
        candidates_path=candidates_path,
        source_cache_dir=source_path.parent,
        allow_list_path=_BUILD_TOOL_ASSETS / "pd-allow-list.yaml",
        vocabulary_path=_BUILD_TOOL_ASSETS / "vocabulary.json",
        generic_phrases_path=_BUILD_TOOL_ASSETS / "generic-phrases.yaml",
        existing_index_path=_INDEX_PATH,
        run_dir=run_dir,
    )
    n_passed = sum(1 for _ in (run_dir / "passed-sentinel.jsonl").read_text(encoding="utf-8").splitlines() if _.strip()) if (run_dir / "passed-sentinel.jsonl").exists() else 0

    # Stage 3 — cross-check
    run_cross_check_batch(
        passed_sentinel_path=run_dir / "passed-sentinel.jsonl",
        rejected_path=rejected_path,
        verified_path=verified_path,
        vocabulary_path=_BUILD_TOOL_ASSETS / "vocabulary.json",
        llm_call=cross_check_llm,
    )
    n_verified = sum(1 for _ in verified_path.read_text(encoding="utf-8").splitlines() if _.strip()) if verified_path.exists() else 0
    n_rejected = sum(1 for _ in rejected_path.read_text(encoding="utf-8").splitlines() if _.strip()) if rejected_path.exists() else 0

    # Stage 4 — audit sample
    if n_verified == 0:
        return {
            "batch_id": batch_id, "n_candidates": n_candidates, "n_passed_sentinel": n_passed,
            "n_verified": 0, "n_rejected": n_rejected, "appended": False, "halt_reason": "no verified entries",
            "sample_accepted": [],
        }
    sampled = sample_audit(verified_path=verified_path, out_path=sample_path)

    # Operator gate
    decision = operator_decision_fn(sample_path, len(sampled), n_verified)
    if decision == "halt":
        return {
            "batch_id": batch_id, "n_candidates": n_candidates, "n_passed_sentinel": n_passed,
            "n_verified": n_verified, "n_rejected": n_rejected, "appended": False,
            "halt_reason": "operator halt", "sample_accepted": [],
        }
    audit_eval = evaluate_audit_decisions(decision, halt_threshold=0.10)
    if audit_eval.action == "halt":
        return {
            "batch_id": batch_id, "n_candidates": n_candidates, "n_passed_sentinel": n_passed,
            "n_verified": n_verified, "n_rejected": n_rejected, "appended": False,
            "halt_reason": f"audit reject rate {audit_eval.reject_rate:.2%} > 10%",
            "sample_accepted": [],
        }

    # Stage 5 — append (or stage)
    sample_ids = [s["candidate_id"] for s in sampled]
    if not promote:
        # Stage the accepted batch into the run dir; do NOT mutate the committed assets.
        # An explicit --promote run (or `append` CLI) performs the canonical append.
        staged_index = run_dir / "staged-index.json"
        staged_map = run_dir / "staged-corpus-map.md"
        append_verified_to_index(verified_path=verified_path, index_path=staged_index_seed(staged_index))
        regenerate_corpus_map(index_path=staged_index, out_path=staged_map)
        return {
            "batch_id": batch_id, "n_candidates": n_candidates, "n_passed_sentinel": n_passed,
            "n_verified": n_verified, "n_rejected": n_rejected, "appended": False, "staged": True,
            "halt_reason": None, "sample_accepted": sample_ids,
            "staged_index": str(staged_index), "staged_corpus_map": str(staged_map),
        }

    append_verified_to_index(verified_path=verified_path, index_path=_INDEX_PATH)
    regenerate_corpus_map(index_path=_INDEX_PATH, out_path=_CORPUS_MAP_PATH)
    return {
        "batch_id": batch_id, "n_candidates": n_candidates, "n_passed_sentinel": n_passed,
        "n_verified": n_verified, "n_rejected": n_rejected, "appended": True, "staged": False,
        "halt_reason": None, "sample_accepted": sample_ids,
    }


def staged_index_seed(staged_index: Path) -> Path:
    """Seed the staged index with a copy of the committed index so the staged append
    reflects what a promote would produce, without touching the live file."""
    if not staged_index.exists():
        staged_index.parent.mkdir(parents=True, exist_ok=True)
        staged_index.write_text(_INDEX_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    return staged_index
