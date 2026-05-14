# skills/book-knowledge/scripts/export_symbolic_trace.py
"""Export the workspace's ingestion history as a symbolic EDN event stream.

Reads:
- <workspace>/raw/manifests/*.json   -> (source/ingested ...) events
- <workspace>/claims/ledger.jsonl    -> (claim/proposed ...) events
- <workspace>/claims/events.jsonl    -> (claim/<status> ...) transition events (optional)

Writes:
- <workspace>/analysis/ingest-trace.edn

The output is regenerable: re-running with the same inputs produces a
byte-identical file (events are sorted by timestamp, then by stable
secondary keys).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

# scripts/__init__.py extends this package's __path__ to include forge's
# scripts/ dir, so the imports below resolve to neurosym-forge's modules.
from scripts._edn_reader import Keyword, Symbol  # noqa: E402
from scripts._edn_writer import write_edn  # noqa: E402


def _parse_instant(value: str) -> dt.datetime:
    """Parse an ISO-8601 instant tolerant of trailing 'Z'."""
    normalized = value.replace("Z", "+00:00") if value.endswith("Z") else value
    return dt.datetime.fromisoformat(normalized)


def _infer_kind(manifest: dict) -> Symbol:
    """Map a manifest hint to an :kind value."""
    path = manifest.get("path", "")
    if path.endswith(".pdf"):
        return Keyword("pdf")
    if path.endswith(".md"):
        return Keyword("markdown")
    if path.endswith(".yaml") or path.endswith(".yml"):
        return Keyword("yaml")
    if "thesis" in manifest.get("doc_id", "").lower():
        return Keyword("thesis")
    return Keyword("unknown")


def _manifest_to_event(manifest: dict) -> tuple[Symbol, dict]:
    """Translate a raw/manifests/*.json record to a source/ingested event."""
    payload: dict = {
        Keyword("doc/id"): manifest["doc_id"],
        Keyword("ingested-at"): _parse_instant(manifest["ingested_at"]),
        Keyword("kind"): _infer_kind(manifest),
    }
    if "path" in manifest:
        payload[Keyword("path")] = manifest["path"]
    if "title" in manifest:
        payload[Keyword("title")] = manifest["title"]
    if "sha256" in manifest:
        payload[Keyword("sha256")] = manifest["sha256"]
    return Symbol("ingested", namespace="source"), payload


def _claim_to_proposed_event(claim: dict) -> tuple[Symbol, dict]:
    """Translate a ledger row to a claim/proposed event."""
    payload: dict = {
        Keyword("claim/id"): claim["claim_id"],
    }
    if claim.get("canonical_text"):
        payload[Keyword("text")] = claim["canonical_text"]
    if claim.get("source_spans"):
        payload[Keyword("source/spans")] = [
            {Keyword("doc/id"): s["doc_id"], Keyword("locator-text"): s["locator_text"]}
            for s in claim["source_spans"]
        ]
    if "confidence" in claim:
        payload[Keyword("confidence")] = claim["confidence"]
    if claim.get("created_at"):
        payload[Keyword("proposed-at")] = _parse_instant(claim["created_at"])
    return Symbol("proposed", namespace="claim"), payload


def _event_to_status_event(event: dict) -> tuple[Symbol, dict]:
    """Translate a claims/events.jsonl row to a claim/<status> transition event."""
    head = Symbol(event["to"], namespace="claim")
    payload: dict = {
        Keyword("claim/id"): event["claim_id"],
        Keyword("from"): Keyword(event["from"]),
        Keyword("to"): Keyword(event["to"]),
        Keyword("transitioned-at"): _parse_instant(event["timestamp"]),
    }
    if event.get("cause_ticket_id"):
        payload[Keyword("cause-ticket-id")] = event["cause_ticket_id"]
    if event.get("cause_class"):
        payload[Keyword("cause-class")] = event["cause_class"]
    if event.get("operator"):
        payload[Keyword("operator")] = event["operator"]
    return head, payload


def _event_sort_key(event_tuple: tuple[Symbol, dict]) -> tuple:
    """Order events by their primary timestamp, then by stable secondary keys."""
    head, payload = event_tuple
    instant = (
        payload.get(Keyword("ingested-at"))
        or payload.get(Keyword("proposed-at"))
        or payload.get(Keyword("transitioned-at"))
    )
    if instant is None:
        # Fall back to MAX so missing timestamps sink to the end deterministically
        instant = dt.datetime.max.replace(tzinfo=dt.timezone.utc)
    # Tie-breaker: head string then claim/doc id
    secondary = str(head)
    tertiary = str(payload.get(Keyword("claim/id")) or payload.get(Keyword("doc/id")) or "")
    return (instant, secondary, tertiary)


def export_trace(workspace: Path, out_path: Path) -> int:
    """Generate the EDN ingestion trace. Returns the event count."""
    events: list[tuple[Symbol, dict]] = []

    manifests_dir = workspace / "raw" / "manifests"
    if manifests_dir.is_dir():
        for manifest_path in sorted(manifests_dir.glob("*.json")):
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            events.append(_manifest_to_event(manifest))

    ledger_path = workspace / "claims" / "ledger.jsonl"
    if ledger_path.exists():
        seen_claims: set[str] = set()
        for line in ledger_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            cid = row.get("claim_id")
            if cid and cid not in seen_claims:
                seen_claims.add(cid)
                events.append(_claim_to_proposed_event(row))

    events_path = workspace / "claims" / "events.jsonl"
    if events_path.exists():
        for line in events_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            events.append(_event_to_status_event(json.loads(line)))

    events.sort(key=_event_sort_key)

    payload = {
        Keyword("version"): 1,
        Keyword("book/id"): workspace.name,
        Keyword("events"): [[head, body] for head, body in events],
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        write_edn(payload, pretty=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return len(events)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--out", default=None,
                    help="defaults to <workspace>/analysis/ingest-trace.edn")
    args = ap.parse_args(argv)
    workspace = Path(args.workspace)
    out_path = Path(args.out) if args.out else workspace / "analysis" / "ingest-trace.edn"
    n = export_trace(workspace, out_path)
    print(f"exported {n} events -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
