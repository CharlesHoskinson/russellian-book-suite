"""CLI entry that chains the four stages: extract → sentinel → cross-check → append.

Each subcommand is independently invocable so the operator can stop after sentinel and
audit the pipeline, or re-run cross-check after the operator has tuned the vocabulary.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Callable


def cmd_derive_vocabulary(args: argparse.Namespace) -> None:
    from scripts.derive_vocabulary import derive_controlled_vocabulary
    derive_controlled_vocabulary(index_path=args.index, out_path=args.out)


def cmd_extract(args: argparse.Namespace, llm_call: Callable[[str], str] | None = None) -> None:
    from scripts.extract_candidates import extract_candidates
    if llm_call is None:
        from scripts.live_llm import extract_llm
        llm_call = extract_llm
    extract_candidates(
        source_path=args.source,
        source_id=args.source_id,
        source_url=args.source_url,
        vocabulary_path=args.vocabulary,
        prompt_path=args.prompt,
        out_path=args.out,
        n=args.n,
        llm_call=llm_call,
    )


def cmd_sentinel(args: argparse.Namespace) -> None:
    from scripts.sentinel import run_sentinel_batch
    run_sentinel_batch(
        candidates_path=args.candidates,
        source_cache_dir=args.source_cache,
        allow_list_path=args.allow_list,
        vocabulary_path=args.vocabulary,
        generic_phrases_path=args.generic_phrases,
        existing_index_path=args.index,
        run_dir=args.run_dir,
    )


def cmd_cross_check(args: argparse.Namespace, llm_call: Callable[[str], str] | None = None) -> None:
    from scripts.cross_check import run_cross_check_batch
    if llm_call is None:
        from scripts.live_llm import cross_check_llm
        llm_call = cross_check_llm
    run_cross_check_batch(
        passed_sentinel_path=args.passed_sentinel,
        rejected_path=args.rejected,
        verified_path=args.verified,
        vocabulary_path=args.vocabulary,
        llm_call=llm_call,
    )


def cmd_audit(args: argparse.Namespace) -> None:
    from scripts.audit_sample import sample_audit
    sample_audit(verified_path=args.verified, out_path=args.out, sample_rate=args.rate, seed=args.seed)


def cmd_append(args: argparse.Namespace) -> None:
    from scripts.append_to_index import append_verified_to_index, regenerate_corpus_map
    append_verified_to_index(verified_path=args.verified, index_path=args.index)
    regenerate_corpus_map(index_path=args.index, out_path=args.corpus_map)


def main() -> None:
    parser = argparse.ArgumentParser(prog="build-russell-corpus")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("derive-vocabulary")
    p.add_argument("--index", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.set_defaults(func=cmd_derive_vocabulary)

    p = sub.add_parser("extract")
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--source-id", type=str, required=True)
    p.add_argument("--source-url", type=str, required=True)
    p.add_argument("--vocabulary", type=Path, required=True)
    p.add_argument("--prompt", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--n", type=int, default=100)
    p.set_defaults(func=cmd_extract)

    p = sub.add_parser("sentinel")
    p.add_argument("--candidates", type=Path, required=True)
    p.add_argument("--source-cache", type=Path, required=True)
    p.add_argument("--allow-list", type=Path, required=True)
    p.add_argument("--vocabulary", type=Path, required=True)
    p.add_argument("--generic-phrases", type=Path, required=True)
    p.add_argument("--index", type=Path, required=True)
    p.add_argument("--run-dir", type=Path, required=True)
    p.set_defaults(func=cmd_sentinel)

    p = sub.add_parser("cross-check")
    p.add_argument("--passed-sentinel", type=Path, required=True)
    p.add_argument("--rejected", type=Path, required=True)
    p.add_argument("--verified", type=Path, required=True)
    p.add_argument("--vocabulary", type=Path, required=True)
    p.set_defaults(func=cmd_cross_check)

    p = sub.add_parser("audit")
    p.add_argument("--verified", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--rate", type=float, default=0.05)
    p.add_argument("--seed", type=int, default=None)
    p.set_defaults(func=cmd_audit)

    p = sub.add_parser("append")
    p.add_argument("--verified", type=Path, required=True)
    p.add_argument("--index", type=Path, required=True)
    p.add_argument("--corpus-map", type=Path, required=True)
    p.set_defaults(func=cmd_append)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
