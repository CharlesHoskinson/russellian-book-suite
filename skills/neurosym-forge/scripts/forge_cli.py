"""Interactive author CLI for neurosym-forge (REQ-AUTHOR-040..046).

Subcommands:

``forge add-constraint``
    Append a defconstraint form to ``rules/booklogic/constraints.edn``
    (interactive prompts or fully-flagged non-interactive mode).  Runs
    ``make ci`` after the append and rolls back on non-zero exit.

``forge suggest-lifts``
    Call Phase P's LLM provider to propose ``deflift`` candidates.

``forge explain-defect``
    Print the defect's source span + unsat-core claim chain.

``forge similar``
    Print top-k semantically-similar claims.

``forge render``
    Shell out to Phase T's ``render_annotations.py``.

Phase P / Q / T modules are imported best-effort: if a prerequisite phase
has not landed in this checkout, the affected subcommand exits non-zero
with a hand-readable pointer to the missing phase.
"""
from __future__ import annotations

import json
import subprocess
import textwrap
from pathlib import Path
from typing import Any

import click


# ---------------------------------------------------------------------------
# Root group
# ---------------------------------------------------------------------------


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--debug",
    is_flag=True,
    default=False,
    help="Show full Python traceback on framework errors.",
)
@click.version_option(package_name="neurosym-forge", prog_name="forge")
@click.pass_context
def cli(ctx: click.Context, debug: bool) -> None:
    """forge — interactive author tooling for neurosym-forge verifiers."""
    ctx.ensure_object(dict)
    ctx.obj["debug"] = debug


# ---------------------------------------------------------------------------
# add-constraint (REQ-AUTHOR-041)
# ---------------------------------------------------------------------------


_VALID_BACKENDS = (":z3", ":cozo", ":egg")
_VALID_SCOPES = (":subject", ":corpus")
_VALID_SEVERITIES = (":critical", ":hard", ":advisory", ":info")


def _constraints_path(project_root: Path) -> Path:
    p = project_root / "rules" / "booklogic" / "constraints.edn"
    if not p.exists():
        raise FileNotFoundError(f"constraints.edn not found at {p}")
    return p


def _render_constraint(
    constraint_id: str,
    backend: str,
    scope: str,
    assert_form: str,
    tolerance: str | None,
    on_unsat_defect: str,
    on_unsat_severity: str,
    on_unsat_message: str | None,
) -> str:
    """Render a defconstraint form as EDN text for append."""
    body = textwrap.dedent(
        f"""
        (defconstraint {constraint_id}
          :backend {backend}
          :scope {scope}
          :assert {assert_form}"""
    ).strip("\n")
    if tolerance:
        body += f"\n  :tolerance {tolerance}"
    msg = on_unsat_message or f"{constraint_id} violated"
    body += (
        "\n  :on-unsat {{:defect {defect} :severity {sev} :message \"{msg}\"}})\n"
    ).format(defect=on_unsat_defect, sev=on_unsat_severity, msg=msg)
    return body


def _append_constraint(path: Path, rendered: str) -> str:
    """Append rendered form to constraints.edn; return the snapshot of the
    pre-append file so we can roll back on failure."""
    original = path.read_text(encoding="utf-8")
    sep = "" if original.endswith("\n\n") else ("\n" if original.endswith("\n") else "\n\n")
    path.write_text(original + sep + rendered, encoding="utf-8")
    return original


def _rollback_constraint(path: Path, original: str) -> None:
    path.write_text(original, encoding="utf-8")


def _run_make_ci(project_root: Path) -> subprocess.CompletedProcess[str]:
    """Run `make ci` in project_root and return the completed process."""
    return subprocess.run(
        ["make", "ci"],
        cwd=str(project_root),
        capture_output=True,
        text=True,
        check=False,
    )


@cli.command("add-constraint")
@click.argument("project_root", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--id", "constraint_id", default=None, help="Constraint id (e.g. :C042-trial-n).")
@click.option("--backend", default=None, type=click.Choice(_VALID_BACKENDS),
              help="Solver backend.")
@click.option("--scope", default=None, type=click.Choice(_VALID_SCOPES), help="Constraint scope.")
@click.option("--assert", "assert_form", default=None,
              help="Assert sexp (e.g. \"(>= (:trial-n ?s) 10)\").")
@click.option("--tolerance", default=None, help="Optional approx= tolerance, e.g. 0.03.")
@click.option("--on-unsat-defect", default=None, help="Defect id for :on-unsat (e.g. :D42).")
@click.option("--on-unsat-severity", default=None, type=click.Choice(_VALID_SEVERITIES),
              help="Declared severity for :on-unsat.")
@click.option("--on-unsat-message", default=None, help="Human-readable defect message.")
@click.option("--non-interactive", is_flag=True, default=False,
              help="Fail fast on missing flags rather than prompting.")
@click.option("--skip-ci", is_flag=True, default=False, help="Skip the make-ci verification step.")
def add_constraint(
    project_root: Path,
    constraint_id: str | None,
    backend: str | None,
    scope: str | None,
    assert_form: str | None,
    tolerance: str | None,
    on_unsat_defect: str | None,
    on_unsat_severity: str | None,
    on_unsat_message: str | None,
    non_interactive: bool,
    skip_ci: bool,
) -> None:
    """Append a defconstraint to <project_root>/rules/booklogic/constraints.edn."""
    path = _constraints_path(project_root)

    def _need(name: str, value: str | None, default: str | None = None,
              choices: tuple[str, ...] | None = None) -> str:
        if value is not None:
            return value
        if non_interactive:
            raise click.UsageError(f"--non-interactive requires --{name.replace('_', '-')}")
        result = click.prompt(
            name.replace("_", " "),
            default=default,
            type=click.Choice(choices) if choices else None,
            show_default=default is not None,
        )
        return str(result)

    constraint_id = _need("id", constraint_id)
    backend = _need("backend", backend, default=":z3", choices=_VALID_BACKENDS)
    scope = _need("scope", scope, default=":subject", choices=_VALID_SCOPES)
    assert_form = _need("assert_form", assert_form)
    if tolerance is None and not non_interactive:
        prompt_val = click.prompt("tolerance (blank to skip)", default="", show_default=False)
        tolerance = prompt_val.strip() or None
    on_unsat_defect = _need("on_unsat_defect", on_unsat_defect)
    on_unsat_severity = _need(
        "on_unsat_severity", on_unsat_severity, default=":critical",
        choices=_VALID_SEVERITIES,
    )

    rendered = _render_constraint(
        constraint_id=constraint_id,
        backend=backend,
        scope=scope,
        assert_form=assert_form,
        tolerance=tolerance,
        on_unsat_defect=on_unsat_defect,
        on_unsat_severity=on_unsat_severity,
        on_unsat_message=on_unsat_message,
    )

    click.echo("Appending:")
    click.echo(rendered)
    snapshot = _append_constraint(path, rendered)

    if skip_ci:
        click.echo(f"Wrote {path} (skipped make ci by --skip-ci).")
        return

    proc = _run_make_ci(project_root)
    if proc.returncode != 0:
        _rollback_constraint(path, snapshot)
        log_slice = (proc.stderr or proc.stdout or "").strip()
        if len(log_slice) > 2000:
            log_slice = log_slice[-2000:]
        click.echo("make ci FAILED — rolled back the appended constraint.", err=True)
        click.echo("---- build log (tail) ----", err=True)
        click.echo(log_slice, err=True)
        raise subprocess.CalledProcessError(proc.returncode, ["make", "ci"], proc.stdout, proc.stderr)

    click.echo(f"Wrote {path}; make ci PASSED.")


# ---------------------------------------------------------------------------
# Remaining subcommand stubs (wired in subsequent commits).
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# suggest-lifts (REQ-AUTHOR-042) — Phase P optional integration
# ---------------------------------------------------------------------------


_PHASE_P_MSG = (
    "suggest-lifts requires Phase P (tier5-llm-extractors) merged first.\n"
    "Until then, the scripts._llm_lift module is unavailable in this "
    "checkout."
)


def _load_claim(project_root: Path, claim_id: str) -> dict[str, Any]:
    claims_path = project_root / "work" / "claims.jsonl"
    if not claims_path.exists():
        raise FileNotFoundError(f"claims.jsonl not found at {claims_path}")
    with claims_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            if record.get("claim_id") == claim_id or record.get("id") == claim_id:
                return record
    raise LookupError(f"claim {claim_id} not found in {claims_path}")


@cli.command("suggest-lifts")
@click.argument("claim_id")
@click.option("--project-root", "project_root", default=".", type=click.Path(path_type=Path),
              help="Project root (defaults to cwd).")
@click.option("--k", type=int, default=3, help="Number of candidate lifts to request.")
def suggest_lifts(claim_id: str, project_root: Path, k: int) -> None:
    """Propose deflift candidates for an unmatched claim via Phase P's LLM provider."""
    try:
        from scripts import _llm_lift  # type: ignore[import-not-found]
    except ImportError:
        click.echo(_PHASE_P_MSG, err=True)
        raise click.exceptions.Exit(2)

    project_root = Path(project_root).resolve()
    record = _load_claim(project_root, claim_id)
    canonical_text = record.get("canonical_text") or record.get("text") or ""
    if not canonical_text:
        raise ValueError(f"claim {claim_id} has no canonical_text")

    provider = _llm_lift.get_provider()
    candidates = provider.suggest_lifts(canonical_text, k=k)
    click.echo(f"Candidate deflift forms for {claim_id} ({len(candidates)} suggestions):")
    click.echo("=" * 72)
    for idx, cand in enumerate(candidates, 1):
        click.echo(f";; candidate {idx} — review before merging")
        click.echo(cand if isinstance(cand, str) else json.dumps(cand, indent=2))
        click.echo()
    click.echo("(Not auto-merged; copy a candidate into rules/booklogic/lifts.edn.)")


# ---------------------------------------------------------------------------
# explain-defect (REQ-AUTHOR-043)
# ---------------------------------------------------------------------------


def _load_verdict(project_root: Path) -> dict[str, Any]:
    """Load work/verdict.edn or work/verdict.json (whichever exists).

    The JSON sibling is accepted for fixture friendliness; production
    verdicts are EDN but the schema is structurally identical.
    """
    work = project_root / "work"
    json_path = work / "verdict.json"
    edn_path = work / "verdict.edn"
    if json_path.exists():
        return json.loads(json_path.read_text(encoding="utf-8"))
    if edn_path.exists():
        from scripts._edn_reader import read_edn  # type: ignore[attr-defined]

        return _coerce_edn(read_edn(edn_path.read_text(encoding="utf-8")))
    raise FileNotFoundError(f"verdict.edn not found at {edn_path}")


def _coerce_edn(value: Any) -> Any:
    """Best-effort EDN→python coercion for verdict pretty-printing."""
    try:
        from scripts._edn_reader import Keyword  # type: ignore[attr-defined]
    except ImportError:
        return value
    if isinstance(value, Keyword):
        return f":{value.name}"
    if isinstance(value, dict):
        return {(_coerce_edn(k) if not isinstance(k, str) else k): _coerce_edn(v)
                for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_coerce_edn(v) for v in value]
    return value


def _find_defect(verdict: dict[str, Any], defect_id: str) -> dict[str, Any]:
    defects = verdict.get("defects") or verdict.get(":defects") or []
    for defect in defects:
        if defect.get("id") == defect_id or defect.get(":id") == defect_id:
            return defect
    raise LookupError(f"defect {defect_id} not in verdict")


def _load_claims_index(project_root: Path) -> dict[str, dict[str, Any]]:
    path = project_root / "work" / "claims.jsonl"
    if not path.exists():
        return {}
    index: dict[str, dict[str, Any]] = {}
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            cid = record.get("claim_id") or record.get("id")
            if cid:
                index[cid] = record
    return index


def _render_context(text: str, line: int, before: int = 3, after: int = 3) -> str:
    if not text:
        return "(no source context available)"
    lines = text.splitlines()
    start = max(0, line - 1 - before)
    end = min(len(lines), line + after)
    width = len(str(end))
    out = []
    for i in range(start, end):
        marker = ">>" if (i + 1) == line else "  "
        out.append(f"{marker} {str(i + 1).rjust(width)}: {lines[i]}")
    return "\n".join(out)


@cli.command("explain-defect")
@click.argument("defect_id")
@click.option("--project-root", "project_root", default=".", type=click.Path(path_type=Path),
              help="Project root (defaults to cwd).")
def explain_defect(defect_id: str, project_root: Path) -> None:
    """Render an unsat-core walkthrough for a defect."""
    project_root = Path(project_root).resolve()
    verdict = _load_verdict(project_root)
    defect = _find_defect(verdict, defect_id)
    claims = _load_claims_index(project_root)

    constraint_id = defect.get("constraint") or defect.get(":constraint") or "(unknown)"
    severity = defect.get("severity") or defect.get(":severity") or "(unknown)"
    declared = defect.get("declared_severity") or defect.get(":declared-severity") or severity
    conf = defect.get("defect_confidence") or defect.get(":defect-confidence") or "(unknown)"
    message = defect.get("message") or defect.get(":message") or ""
    core_ids = defect.get("unsat_core") or defect.get(":unsat-core") or []

    click.echo(f"Defect: {defect_id} (constraint {constraint_id})")
    click.echo(f"Severity: {declared} (declared) / {severity} (rendered)")
    click.echo(f"Defect confidence: {conf}")
    click.echo("")
    click.echo("Source span:")
    span = defect.get("span") or defect.get(":span") or {}
    src_path = span.get("path") or span.get(":path")
    src_line = span.get("line") or span.get(":line") or 0
    if src_path:
        full = project_root / src_path if not Path(src_path).is_absolute() else Path(src_path)
        if full.exists():
            click.echo(_render_context(full.read_text(encoding="utf-8"), int(src_line)))
        else:
            click.echo(f"  {src_path}:{src_line} (file missing on disk)")
    else:
        click.echo("  (no source span recorded)")

    click.echo("")
    click.echo("Unsat core (newest claim first):")
    for cid in core_ids:
        rec = claims.get(cid, {})
        cconf = rec.get("confidence", "(unknown)")
        snippet = (rec.get("canonical_text") or "").strip().replace("\n", " ")
        if len(snippet) > 110:
            snippet = snippet[:107] + "..."
        click.echo(f"  {cid}  conf {cconf}")
        if snippet:
            click.echo(f"    \"{snippet}\"")

    click.echo("")
    click.echo("Interpretation:")
    interpretation = (
        f"Constraint {constraint_id} requires {message or 'a condition that does not hold'}. "
        f"The unsat core lists {len(core_ids)} claim(s) whose values disagree under the "
        "constraint; resolve by editing the conflicting source spans, downgrading the "
        "defect's severity, or relaxing the constraint."
    )
    click.echo(textwrap.fill(interpretation, width=78))


@cli.command("similar")
def similar() -> None:
    """Print the top-k semantically-similar claims to <claim_id>."""
    click.echo("similar not yet wired")


@cli.command("render")
def render() -> None:
    """Shell out to Phase T's render_annotations.py."""
    click.echo("render not yet wired")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main() -> None:
    cli(prog_name="forge")


if __name__ == "__main__":
    main()
