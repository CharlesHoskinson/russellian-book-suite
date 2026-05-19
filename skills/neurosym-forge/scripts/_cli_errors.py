"""Hand-readable error messages for the forge CLI (REQ-AUTHOR-045).

The CLI catches framework exceptions and renders them as four-line
interpretive messages: summary, what likely happened, likely fix, and a
reference into ``docs/booklogic-dsl-reference.md``.  The mapping lives in
this module so the user-surface error library is reviewable in one place.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class CliError:
    """One hand-written interpretation of a framework error."""

    summary: str
    what_likely_happened: str
    likely_fix: str
    reference: str

    def render(self) -> str:
        return (
            f"ERROR: {self.summary}\n"
            f"What likely happened: {self.what_likely_happened}\n"
            f"Likely fix: {self.likely_fix}\n"
            f"Reference: {self.reference}\n"
            "Run with --debug for full traceback."
        )


# Match against substrings of the exception class name + message.  The first
# entry whose ``match_any`` produces a hit wins.  Order matters: put more
# specific matches first.
ERROR_TABLE: tuple[tuple[Iterable[str], CliError], ...] = (
    (
        ("FileNotFoundError", "constraints.edn"),
        CliError(
            summary="constraints.edn missing under <project>/rules/booklogic/",
            what_likely_happened=(
                "forge add-constraint expects a scaffolded project tree; the "
                "rules/booklogic/constraints.edn file was not found."
            ),
            likely_fix=(
                "Run scaffold_project to bootstrap the tree, or cd into an "
                "existing verifier directory before invoking forge."
            ),
            reference="docs/booklogic-dsl-reference.md §1 (Project layout)",
        ),
    ),
    (
        ("FileNotFoundError", "claims.jsonl"),
        CliError(
            summary="claims.jsonl missing under <project>/work/",
            what_likely_happened=(
                "forge suggest-lifts and forge similar read the ingested claim "
                "ledger; it has not been produced for this project yet."
            ),
            likely_fix="Run `make ingest` (or its scaffolded equivalent) to "
            "produce work/claims.jsonl before invoking this subcommand.",
            reference="docs/booklogic-dsl-reference.md §2 (Ingest pipeline)",
        ),
    ),
    (
        ("FileNotFoundError", "verdict.edn"),
        CliError(
            summary="verdict.edn missing under <project>/work/",
            what_likely_happened=(
                "forge explain-defect reads the most recent solver verdict; "
                "it has not been produced for this project yet."
            ),
            likely_fix="Run `make ci` (or `make verify`) to produce "
            "work/verdict.edn before invoking explain-defect.",
            reference="docs/booklogic-dsl-reference.md §4 (Verification)",
        ),
    ),
    (
        ("CalledProcessError",),
        CliError(
            summary="`make ci` failed for the appended constraint",
            what_likely_happened=(
                "the new constraint compiled to a form the verifier or solver "
                "rejected (unknown predicate, malformed assert form, bad "
                ":on-unsat block, etc.)."
            ),
            likely_fix=(
                "Inspect the build-log slice above; fix the constraint or roll "
                "back the append.  The CLI rolls back automatically on `make "
                "ci` non-zero exit."
            ),
            reference="docs/booklogic-dsl-reference.md §3 (Constraints)",
        ),
    ),
    (
        ("ValueError", "predicate"),
        CliError(
            summary="predicate name failed schema type-check",
            what_likely_happened=(
                "a regex group resolves to a Python type that does not match "
                "the predicate's declared sort (e.g. parse-float on an :int "
                "predicate)."
            ),
            likely_fix=(
                "Either change the predicate's :return sort in "
                "predicates.edn, or change the lift's :emit coercion to match."
            ),
            reference="docs/booklogic-dsl-reference.md §5 (Lifts)",
        ),
    ),
)


_GENERIC = CliError(
    summary="forge subcommand failed",
    what_likely_happened="an unhandled framework error reached the CLI.",
    likely_fix=(
        "Re-run with --debug to see the full Python traceback, then file a "
        "bug if the cause is not clear from the trace."
    ),
    reference="docs/booklogic-dsl-reference.md (Troubleshooting)",
)


def interpret(exc: BaseException) -> CliError:
    """Return the best ``CliError`` for ``exc``.

    The lookup keys on the exception class name and string representation; if
    no entry matches, a generic interpretation is returned.
    """
    haystack = f"{type(exc).__name__} {exc}"
    for needles, entry in ERROR_TABLE:
        if all(needle in haystack for needle in needles):
            return entry
    return _GENERIC


__all__ = ["CliError", "ERROR_TABLE", "interpret"]
