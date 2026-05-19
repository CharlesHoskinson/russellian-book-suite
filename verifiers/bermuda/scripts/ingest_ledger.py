"""Bermuda-specific ledger ingester.

Reads examples/bermuda-manual/claims/ledger.jsonl, applies the predicate
map in rules/predicates.edn to fact-class claims, and emits typed atoms
to work/claims.edn. design_decision claims are emitted as :context atoms.

Generated initially by neurosym-forge --book-knowledge-bridge, then
specialized for the Bermuda predicate set.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterator

# scripts/__init__.py extends this package's __path__ to include forge's
# scripts/ dir, so the imports below resolve to neurosym-forge's modules.
from scripts._edn_reader import Keyword  # noqa: E402
from scripts._edn_streaming import (  # noqa: E402
    StreamingAtomWriter,
    check_no_orphan_partial,
)
from scripts._io import read_edn_file, write_edn_file  # noqa: E402, F401

_KW_VERSION = Keyword("version")
_KW_ATOMS = Keyword("atoms")
_KW_PREDICATES = Keyword("predicates")
_KW_PATTERNS = Keyword("patterns")
_KW_PREDICATE = Keyword("predicate")
_KW_SUBJECT = Keyword("subject")
_KW_VALUE_KIND = Keyword("value_kind")
_KW_VALUE_KIND_H = Keyword("value-kind")   # codegened hyphenated form
_KW_WORD_TO_INT = Keyword("word_to_int")
_KW_WORD_TO_INT_H = Keyword("word-to-int")  # codegened hyphenated form
_KW_VALUE = Keyword("value")

_KW_ID = Keyword("id")
_KW_DOC = Keyword("doc")
_KW_SOURCE_SPANS = Keyword("source_spans")
_KW_SUPPORTS_CHAPTERS = Keyword("supports_chapters")
_KW_CONFIDENCE = Keyword("confidence")
_KW_KIND = Keyword("kind")
_KW_SORT = Keyword("sort")
_KW_NAME = Keyword("name")
_KW_CONTEXT = Keyword("context")

# REQ-LLMLIFT-040, 044, 046: per-spec backend dispatch.
_KW_BACKEND = Keyword("backend")
_KW_BACKEND_REGEX = Keyword("regex")
_KW_BACKEND_LLM = Keyword("llm")
_KW_LIFT_ID = Keyword("lift-id")
_KW_LIFT_ID_U = Keyword("lift_id")
_KW_EMIT_TEMPLATE = Keyword("emit-template")
_KW_EMIT_TEMPLATE_U = Keyword("emit_template")

# REQ-LLMLIFT-043: defect-discriminator atoms surfaced when an LLM
# proposal fails schema validation. The Rust verifier ignores
# :kind :defect atoms at SMT time; verdict_to_qa surfaces them.
_KW_DEFECT = Keyword("defect")
_KW_REASON = Keyword("reason")
_KW_LLM_LIFT_REJECTED = Keyword("llm-lift-rejected")


def read_ledger(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def latest_per_id(rows: list[dict]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for r in rows:
        cid = r.get("claim_id") or r.get("id")
        if cid:
            out[cid] = r
    return out


def _is_verified(c: dict) -> bool:
    return c.get("status") == "verified" or c.get("tbf:status") == "verified"


def _get_spec(spec: dict, underscore_key: Keyword, hyphen_key: Keyword, default: Any = None) -> Any:
    """Dual-key lookup: try underscore form first (v0.2), then hyphenated (codegened)."""
    v = spec.get(underscore_key)
    if v is None:
        v = spec.get(hyphen_key)
    return v if v is not None else default


def _kind_str(v: Any) -> str:
    """Normalise value-kind: Keyword('int') → 'int', 'int' → 'int'."""
    if isinstance(v, Keyword):
        return v.name
    return str(v) if v is not None else ""


_JS_NAMED_GROUP = re.compile(r"\(\?<([A-Za-z_][A-Za-z0-9_]*)>")


class IngestRegexDialectError(ValueError):
    """REQ-INGEST-050, 051: a predicate pattern uses a regex dialect
    other than Python's `re` module.

    The most common case is JS-style `(?<name>...)` named groups
    (lifts.edn authored against the CLJS/JS regex engine). Python uses
    the Perl-style `(?P<name>...)` form. Earlier versions silently
    rewrote one to the other; we now reject the input so the author
    fixes the source rather than relying on a hidden translation layer.
    """


class IngestConfidenceError(ValueError):
    """REQ-CONFIDENCE-043: a claim's `:confidence` is non-numeric or out
    of the closed interval `[0, 1]`. Missing fields default to 1.0
    (backwards-compatible with pre-Tier-5 fixtures) and do *not* raise.
    """


def _validated_confidence(claim: dict) -> float:
    """REQ-CONFIDENCE-043: parse + validate a claim's `:confidence`.

    Missing field => 1.0 (backwards-compat). Non-numeric or out-of-range
    raises ``IngestConfidenceError`` naming the claim id and value.
    """
    cid = claim.get("claim_id") or claim.get("id") or "<unknown>"
    if "confidence" not in claim:
        return 1.0
    raw = claim["confidence"]
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise IngestConfidenceError(
            f"claim {cid!r} has non-numeric :confidence {raw!r} "
            f"(type {type(raw).__name__})"
        )
    val = float(raw)
    if not (0.0 <= val <= 1.0):
        raise IngestConfidenceError(
            f"claim {cid!r} :confidence {val} out of range [0, 1]"
        )
    return val


def _assert_python_regex_dialect(pat: str) -> None:
    """REQ-INGEST-050, 051: hard-fail on non-Python regex dialect.

    Catches JS-style `(?<name>...)` named groups. Re.compile errors
    surface as their native exceptions (re.error) when the search runs.
    """
    m = _JS_NAMED_GROUP.search(pat)
    if m is not None:
        raise IngestRegexDialectError(
            f"predicate pattern uses JS-style named group `(?<{m.group(1)}>...)`; "
            f"Python regex requires `(?P<{m.group(1)}>...)`. Offending pattern: {pat!r}"
        )


def _backend_of(spec: dict) -> Keyword:
    """REQ-LLMLIFT-040: return the lift's :backend (:regex by default)."""
    b = spec.get(_KW_BACKEND)
    if isinstance(b, Keyword):
        return b
    return _KW_BACKEND_REGEX


def _apply_llm_lift(
    spec: dict,
    *,
    claim_id: str,
    canonical_text: str,
    schema_path: Path | None,
) -> tuple[str, Any] | None:
    """REQ-LLMLIFT-040, 042, 044, 046: dispatch a `:backend :llm` lift.

    Returns one of:
      ("match", (pred, value, subj))        — schema-valid proposal
      ("defect", (predicate-name, reason))  — schema-invalid proposal,
                                              surfaced as :llm-lift-rejected
      None                                  — provider returned no atom
    """
    from scripts._llm_lift import (  # type: ignore
        LLMLiftRejected,
        cached_extract,
        get_provider,
        validate_proposal,
    )

    provider = get_provider()
    emit_template = (
        _get_spec(spec, _KW_EMIT_TEMPLATE_U, _KW_EMIT_TEMPLATE, "") or ""
    )
    lift_id = _get_spec(spec, _KW_LIFT_ID_U, _KW_LIFT_ID, "") or ""
    if isinstance(lift_id, Keyword):
        lift_id = lift_id.name

    proposal = cached_extract(
        provider,
        claim_id=claim_id,
        canonical_text=canonical_text,
        emit_template=str(emit_template),
        lift_id=str(lift_id),
    )
    if proposal is None:
        return None

    pred_raw = proposal.get("predicate")
    if schema_path is not None and schema_path.exists():
        try:
            validate_proposal(schema_path, proposal)
        except LLMLiftRejected as e:
            # REQ-LLMLIFT-043: schema-invalid proposals surface as a
            # structured defect, not a silent OPAQUE.
            return ("defect", (str(pred_raw), str(e)))
    subj_raw = proposal.get("subject") or spec.get(_KW_SUBJECT)
    pred = (
        pred_raw if isinstance(pred_raw, Keyword)
        else Keyword(str(pred_raw).lstrip(":"))
    )
    subj = (
        subj_raw if isinstance(subj_raw, Keyword)
        else Keyword(str(subj_raw).lstrip(":"))
    )
    value = proposal.get("value")
    return ("match", (pred, value, subj))


def _apply_predicates(
    text: str,
    predicates: dict,
    *,
    claim_id: str = "",
    schema_path: Path | None = None,
) -> tuple[str, Any] | None:
    """Match text against the predicate map.

    Returns:
      ("match", (pred, value, subj))      — successful extraction
      ("defect", (pred-name, reason))     — :backend :llm proposal failed
                                            schema validation (REQ-LLMLIFT-043)
      None                                — no lift matched
    """
    for _name, spec in predicates.items():
        backend = _backend_of(spec)
        if backend == _KW_BACKEND_LLM:
            # REQ-LLMLIFT-040: route through the LLM provider.
            result = _apply_llm_lift(
                spec,
                claim_id=claim_id,
                canonical_text=text,
                schema_path=schema_path,
            )
            if result is None:
                continue
            return result
        # Default: regex backend (current behaviour).
        for pat in spec.get(_KW_PATTERNS, []):
            _assert_python_regex_dialect(pat)
            m = re.search(pat, text, flags=re.IGNORECASE | re.DOTALL)
            if not m:
                continue
            value_kind = _kind_str(_get_spec(spec, _KW_VALUE_KIND, _KW_VALUE_KIND_H))
            if value_kind == "bool":
                value = spec.get(_KW_VALUE, True)
            elif value_kind == "int":
                raw = m.group("n") if "n" in m.groupdict() else m.group(1)
                raw = raw.replace(",", "").strip()
                word_to_int = _get_spec(spec, _KW_WORD_TO_INT, _KW_WORD_TO_INT_H, {})
                value = word_to_int.get(raw.lower(), None)
                if value is None:
                    try:
                        value = int(raw)
                    except ValueError:
                        continue
            elif value_kind == "real":
                raw = m.group("n") if "n" in m.groupdict() else m.group(1)
                raw = raw.replace(",", "").strip()
                try:
                    value = float(raw)
                except ValueError:
                    continue
            elif value_kind == "string":
                value = m.group("binomial").strip()
            elif value_kind == "entity":
                value = m.group("island").replace(".", "").replace(" ", "_")
            else:
                continue
            pred_raw = spec.get(_KW_PREDICATE)
            subj_raw = spec.get(_KW_SUBJECT)
            # REQ-EDN-049: emit Keyword objects, not string-with-colon-prefix.
            pred = pred_raw if isinstance(pred_raw, Keyword) else Keyword(str(pred_raw).lstrip(":"))
            subj = subj_raw if isinstance(subj_raw, Keyword) else Keyword(str(subj_raw).lstrip(":"))
            return ("match", (pred, value, subj))
    return None


def _claim_to_atom(
    claim: dict, predicates: dict, schema_path: Path | None = None,
) -> dict:
    text = claim.get("canonical_text", "")
    claim_id = claim.get("claim_id", "?")
    # REQ-CONFIDENCE-043: validate :confidence at the boundary; missing
    # field defaults to 1.0 (backwards-compat with pre-Tier-5 fixtures).
    confidence = _validated_confidence(claim)
    base: dict = {
        _KW_ID: claim_id,
        _KW_DOC: text[:200],
        _KW_SOURCE_SPANS: claim.get("source_spans", []),
        _KW_SUPPORTS_CHAPTERS: claim.get("supports_chapters", []),
        _KW_CONFIDENCE: confidence,
    }
    if claim.get("claim_type") == "design_decision":
        base.update({
            _KW_KIND: Keyword("symbol"),
            _KW_SORT: Keyword("formula"),
            _KW_NAME: Keyword("CONTEXT"),
            _KW_CONTEXT: True,
        })
        return base
    result = _apply_predicates(
        text, predicates, claim_id=claim_id, schema_path=schema_path,
    )
    if result is None:
        base.update({
            _KW_KIND: Keyword("symbol"),
            _KW_SORT: Keyword("formula"),
            _KW_NAME: Keyword("OPAQUE"),
        })
        return base
    tag, payload = result
    if tag == "defect":
        # REQ-LLMLIFT-043: emit :kind :defect atom with a structured
        # :llm-lift-rejected reason. The Rust verifier ignores
        # :kind :defect atoms at SMT time; verdict_to_qa surfaces them.
        pred_name, reason = payload
        base.update({
            _KW_KIND: _KW_DEFECT,
            _KW_SORT: Keyword("formula"),
            _KW_REASON: _KW_LLM_LIFT_REJECTED,
            _KW_PREDICATE: pred_name,
            _KW_DOC: reason[:500],
        })
        return base
    # tag == "match"
    predicate, value, subject = payload
    base.update({
        _KW_KIND: Keyword("expression"),
        _KW_SORT: Keyword("formula"),
        _KW_PREDICATE: predicate,
        _KW_SUBJECT: subject,
        _KW_VALUE: value,
        _KW_CONTEXT: False,
    })
    return base


def _validate_against_schema(predicates_path: Path, predicates: dict) -> None:
    """REQ-EDN-053: validate predicate names against booklogic-schema.edn.

    The schema is emitted by `nbb -m booklogic` next to predicates.edn. If
    present, every key in `predicates` must match a key in the schema's
    :predicates map. Missing schema -> warning only (older projects).
    """
    schema_path = predicates_path.parent / "booklogic-schema.edn"
    if not schema_path.exists():
        return
    schema = read_edn_file(schema_path)
    known = set(schema.get(Keyword("predicates"), {}).keys())
    unknown = [str(p) for p in predicates if p not in known]
    if unknown:
        import sys
        print(
            f"ingest_ledger: unknown predicate(s) {unknown!r}; not in "
            f"booklogic-schema.edn (expected one of {sorted(map(str, known))!r})",
            file=sys.stderr,
        )
        sys.exit(1)


def compute_atoms_iter(
    ledger_path: Path, predicates_path: Path,
) -> Iterator[dict]:
    """REQ-PERF-050: yield atoms one at a time instead of materialising
    the full list. The intermediate `latest` dedup map still has to be
    built (a later JSONL row may supersede an earlier `claim_id`), but
    the post-`_claim_to_atom` enrichment — the part that dominates
    peak RSS at book-knowledge scale — is now lazy.
    """
    predicates_data = read_edn_file(predicates_path)
    predicates = predicates_data.get(_KW_PREDICATES, {})
    _validate_against_schema(predicates_path, predicates)
    # REQ-LLMLIFT-042: hand the schema path to `_claim_to_atom` so any
    # `:backend :llm` lift can schema-check its LLM proposals before
    # admitting them to the atomspace.
    schema_path = predicates_path.parent / "booklogic-schema.edn"

    rows = read_ledger(ledger_path)
    latest = latest_per_id(rows)
    del rows
    for claim in latest.values():
        if not _is_verified(claim):
            continue
        yield _claim_to_atom(claim, predicates, schema_path=schema_path)


def compute_atoms(ledger_path: Path, predicates_path: Path) -> list[dict]:
    """Backwards-compat wrapper around `compute_atoms_iter`."""
    return list(compute_atoms_iter(ledger_path, predicates_path))


def ingest(ledger_path: Path,
           predicates_path: Path,
           out_path: Path,
           return_atoms: bool = False) -> list[dict] | int:
    """REQ-PERF-050..053: stream atoms to `out_path` via `StreamingAtomWriter`.

    `return_atoms=True` preserves the legacy materialise-and-return
    contract (the bermuda smoke harness still uses it). The default
    streaming path never holds more than one atom in flight on the
    writer side.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # REQ-PERF-053: refuse to proceed if a stale `.partial` sibling
    # marker says the previous run was killed mid-write. The operator
    # must clear the marker (and any truncated output) to acknowledge
    # the crash; we won't silently overwrite or append to a corrupt
    # document.
    check_no_orphan_partial(out_path)

    if return_atoms:
        atoms = list(compute_atoms_iter(ledger_path, predicates_path))
        with StreamingAtomWriter(out_path, version=1) as w:
            for a in atoms:
                w.write(a)
        return atoms

    n = 0
    with StreamingAtomWriter(out_path, version=1) as w:
        for a in compute_atoms_iter(ledger_path, predicates_path):
            w.write(a)
            n += 1
            if n % 1000 == 0:
                # REQ-PERF-052: progress every 1000 atoms so operators
                # know the process is alive on book-knowledge corpora.
                print(f"ingest: {n} atoms processed", file=sys.stderr)
    return n


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--predicates", required=True)
    ap.add_argument("--out", default="work/claims.edn")
    args = ap.parse_args(argv)
    n = ingest(Path(args.ledger), Path(args.predicates), Path(args.out))
    print(f"ingested {n} verified atoms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
