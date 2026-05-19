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

import functools
import json
import os
import subprocess
import sys
import textwrap
import traceback
from pathlib import Path
from typing import Any, Callable

import click

from scripts._cli_errors import interpret


# ---------------------------------------------------------------------------
# Error decorator (REQ-AUTHOR-045)
# ---------------------------------------------------------------------------


_DEBUG_ENV = "FORGE_DEBUG"


def _debug_enabled(ctx: click.Context | None) -> bool:
    if ctx is not None:
        root = ctx.find_root()
        if root.params.get("debug"):
            return True
    return os.environ.get(_DEBUG_ENV) == "1"


def _handle(func: Callable[..., Any]) -> Callable[..., Any]:
    """Wrap a click command body to translate framework errors.

    Click's own usage / exit signals are re-raised so click handles them
    itself; everything else is rendered via the ``_cli_errors`` table.
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        ctx = click.get_current_context(silent=True)
        try:
            return func(*args, **kwargs)
        except click.ClickException:
            raise
        except click.exceptions.Exit:
            raise
        except SystemExit:
            raise
        except BaseException as exc:  # noqa: BLE001 — last-resort surface
            if _debug_enabled(ctx):
                traceback.print_exc()
                raise click.exceptions.Exit(1) from exc
            entry = interpret(exc)
            click.echo(entry.render(), err=True)
            raise click.exceptions.Exit(1) from exc

    return wrapper


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
    if debug:
        os.environ[_DEBUG_ENV] = "1"


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
@_handle
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
@_handle
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
    """Best-effort EDN→python coercion for verdict / sidecar pretty-printing.

    Keywords carry their namespace (``:induced/foo`` survives the round-trip);
    legacy callers passing already-stringified keys are left untouched.
    """
    try:
        from scripts._edn_reader import Keyword  # type: ignore[attr-defined]
    except ImportError:
        return value
    if isinstance(value, Keyword):
        return str(value)
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
@_handle
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


# ---------------------------------------------------------------------------
# similar (REQ-AUTHOR-044) — Phase Q optional integration
# ---------------------------------------------------------------------------


_PHASE_Q_MSG = (
    "similar requires Phase Q (tier5-semantic-retrieval) merged first.\n"
    "Until then, the scripts._semantic_index module is unavailable in this "
    "checkout."
)


@cli.command("similar")
@click.argument("claim_id")
@click.option("--k", type=int, default=5, help="Number of neighbours to return.")
@click.option("--project-root", "project_root", default=".", type=click.Path(path_type=Path),
              help="Project root (defaults to cwd).")
@_handle
def similar(claim_id: str, k: int, project_root: Path) -> None:
    """Print the top-k semantically-similar claims to <claim_id>."""
    try:
        from scripts import _semantic_index  # type: ignore[import-not-found]
    except ImportError:
        click.echo(_PHASE_Q_MSG, err=True)
        raise click.exceptions.Exit(2)

    project_root = Path(project_root).resolve()
    index = _semantic_index.SemanticIndex.load(project_root)
    hits = index.similar_claims(claim_id, k=k)

    click.echo(f"Top {len(hits)} similar claims to {claim_id}:")
    click.echo(f"{'claim_id':<22}  {'score':>6}  {'subject':<18}  snippet")
    click.echo("-" * 78)
    for hit in hits:
        cid = hit.get("claim_id", "")
        score = hit.get("score", 0.0)
        subject = (hit.get("subject") or "")[:18]
        snippet = (hit.get("snippet") or "").replace("\n", " ")[:32]
        click.echo(f"{cid:<22}  {score:>6.3f}  {subject:<18}  {snippet}")


# ---------------------------------------------------------------------------
# render (Phase T integration)
# ---------------------------------------------------------------------------


_PHASE_T_MSG = (
    "render requires Phase T (tier5-publication-bridge) merged first.\n"
    "Until then, scripts/render_annotations.py is unavailable in this "
    "checkout."
)


@cli.command("render")
@click.option("--project-root", "project_root", default=".", type=click.Path(path_type=Path),
              help="Project root (defaults to cwd).")
@click.option("--manuscript", "manuscript", default=None, type=click.Path(path_type=Path),
              help="Optional path to the manuscript .md file.")
@_handle
def render(project_root: Path, manuscript: Path | None) -> None:
    """Shell out to Phase T's render_annotations.py."""
    project_root = Path(project_root).resolve()
    script = Path(__file__).resolve().parent / "render_annotations.py"
    if not script.exists():
        click.echo(_PHASE_T_MSG, err=True)
        raise click.exceptions.Exit(2)
    cmd = [sys.executable, str(script), "--project-root", str(project_root)]
    if manuscript is not None:
        cmd += ["--manuscript", str(manuscript)]
    proc = subprocess.run(cmd, check=False)
    if proc.returncode != 0:
        raise click.exceptions.Exit(proc.returncode)


# ---------------------------------------------------------------------------
# Tier 6 — induce / revise / theory (REQ-AUTHOR-050..056)
# ---------------------------------------------------------------------------
#
# Each subcommand depends on phases V/W/X/Y/Z that may not be merged on this
# checkout. Per the Phase U pattern, conditional imports degrade gracefully:
# the subcommand surfaces a hand-readable pointer to the missing phase rather
# than a Python ImportError stack trace.


class InductionPipelineError(RuntimeError):
    """Raised when the nbb induction orchestrator exits non-zero.

    Surfaced via ``_cli_errors.interpret`` so the user sees a four-line
    interpretive message rather than the raw subprocess return code.
    """


class RevisionInputError(click.UsageError):
    """Raised when ``forge revise`` is invoked with no inputs.

    Inherits ``click.UsageError`` so click's own help-formatter kicks in
    naturally; the interpret-table entry matches on the class name and adds
    the four-line ERROR block on top.
    """


class ProvenanceSidecarError(RuntimeError):
    """Raised when the PROV-O sidecar is missing or malformed."""


_PHASE_AA_INDUCE_MSG = (
    "forge induce requires the nbb orchestrator at "
    "scripts/induce_theory.cljs (Phase W) to be present, and Phase V/X/Y "
    "modules merged first.\n"
    "Run with --debug for the underlying error."
)

_PHASE_AA_REVISE_MSG = (
    "forge revise requires Phase Z (tier6-agm-revision) merged first.\n"
    "Until then, the scripts._agm_revision module is unavailable in this "
    "checkout."
)

_PHASE_AA_THEORY_MSG = (
    "forge theory requires Phase Y (tier6-provenance-sidecar) merged "
    "first.\n"
    "Until then, the scripts._provenance module is unavailable in this "
    "checkout."
)


# Filenames the three subcommands operate on. Centralised so tests and the
# implementation agree on the layout.
_INDUCED_THEORY_FILE = "induced-theory.edn"
_INDUCED_PROV_FILE = "induced-theory.prov.edn"
_SEMANTIC_INDEX_FILE = "_semantic_index.bin"


def _booklogic_dir(project_root: Path) -> Path:
    return project_root / "rules" / "booklogic"


def _induced_paths(project_root: Path) -> tuple[Path, Path]:
    booklogic = _booklogic_dir(project_root)
    return booklogic / _INDUCED_THEORY_FILE, booklogic / _INDUCED_PROV_FILE


def _semantic_index_path(project_root: Path) -> Path:
    return project_root / "work" / _SEMANTIC_INDEX_FILE


def _check_semantic_index(project_root: Path) -> None:
    """Warn (don't fail) when Phase Q's semantic index is absent.

    REQ-AUTHOR-054: emits the prescribed warning string and proceeds.
    """
    idx = _semantic_index_path(project_root)
    if not idx.exists():
        click.echo(
            f"warning: semantic index not found at {idx}; running pure-"
            "symbolic induction (no atom clustering, no semantic neighbours).",
            err=True,
        )


def _load_sidecar(prov_path: Path) -> dict[str, Any]:
    """Best-effort load of induced-theory.prov.edn.

    REQ-AUTHOR-053: when the sidecar is missing or malformed, we surface the
    structured error and return an empty provenance dict so the rule list
    still renders.
    """
    if not prov_path.exists():
        raise ProvenanceSidecarError(
            f"sidecar missing at {prov_path}"
        )
    try:
        from scripts._edn_reader import read_edn  # type: ignore[attr-defined]
    except ImportError:  # pragma: no cover — EDN reader is in-tree
        raise ProvenanceSidecarError("EDN reader unavailable")
    try:
        return _coerce_edn(read_edn(prov_path.read_text(encoding="utf-8")))
    except Exception as exc:  # noqa: BLE001 — wrap all parse errors uniformly
        raise ProvenanceSidecarError(
            f"sidecar at {prov_path} is malformed: {exc}"
        ) from exc


def _sidecar_rules(prov: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return the :rules dict from a loaded sidecar, normalised to plain dict."""
    rules = prov.get("rules") or prov.get(":rules") or {}
    if not isinstance(rules, dict):
        return {}
    return {str(k): v for k, v in rules.items() if isinstance(v, dict)}


def _prov_field(rule_prov: dict[str, Any], *names: str) -> Any:
    """Look up the first matching key from rule_prov.

    Accepts both ``:prov/foo`` and ``prov/foo`` and bare ``foo`` because the
    EDN coercion may flatten keywords to either form.
    """
    for name in names:
        for candidate in (name, f":{name}", f":prov/{name}", f"prov/{name}"):
            if candidate in rule_prov:
                return rule_prov[candidate]
    return None


# ---------------------------------------------------------------------------
# forge induce — REQ-AUTHOR-050, 051, 054
# ---------------------------------------------------------------------------


def _run_nbb_induce(
    project_root: Path,
    folds: int,
    budget_usd: float | None,
) -> subprocess.CompletedProcess[str]:
    """Shell out to the nbb orchestrator.

    Separated so tests can monkeypatch the subprocess call without faking
    a real nbb runtime.
    """
    script = Path(__file__).resolve().parent / "induce_theory.cljs"
    cmd = [
        "nbb",
        "-m", "induce-theory",
        str(project_root),
        "--folds", str(folds),
    ]
    if budget_usd is not None:
        cmd += ["--budget-usd", str(budget_usd)]
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
        cwd=str(script.parent),
    )


def _format_induce_summary(prov: dict[str, Any]) -> str:
    """Render the one-screen summary printed after a successful induce run."""
    rules = _sidecar_rules(prov)
    total = len(rules)

    total_cost = 0.0
    ranked: list[tuple[str, float, int]] = []
    for rid, rprov in rules.items():
        cost = _prov_field(rprov, "cost-usd") or 0.0
        if isinstance(cost, (int, float)):
            total_cost += float(cost)
        entrench = _prov_field(rprov, "entrenchment") or 0.0
        docs = _prov_field(rprov, "source-documents") or []
        doc_count = len(docs) if isinstance(docs, (list, tuple)) else 0
        try:
            entrench_f = float(entrench)
        except (TypeError, ValueError):
            entrench_f = 0.0
        ranked.append((rid, entrench_f, doc_count))

    ranked.sort(key=lambda row: row[1], reverse=True)
    top3 = ranked[:3]

    lines = [
        f"Induction complete: {total} rule(s) induced.",
        f"Total cost: ${total_cost:.4f}",
        "",
        "Top-3 highest-entrenchment rules:",
    ]
    if not top3:
        lines.append("  (none)")
    else:
        for rid, entrench, doc_count in top3:
            lines.append(
                f"  {rid:<48}  entrench={entrench:.3f}  docs={doc_count}"
            )
    return "\n".join(lines)


@cli.command("induce")
@click.argument("project_root", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--folds", type=int, default=5,
              help="Document-held-out validation folds (default 5).")
@click.option("--budget-usd", "budget_usd", type=float, default=None,
              help="Opt-in dollar ceiling across the induction run.")
@_handle
def induce(
    project_root: Path,
    folds: int,
    budget_usd: float | None,
) -> None:
    """Induce a BookLogic theory from <project_root>'s atomspace.

    Shells out to the nbb orchestrator at scripts/induce_theory.cljs.  On
    success, emits rules/booklogic/induced-theory.edn and the PROV-O sidecar,
    then prints a one-screen summary.
    """
    project_root = Path(project_root).resolve()
    booklogic = _booklogic_dir(project_root)
    if not booklogic.exists():
        raise FileNotFoundError(
            f"rules/booklogic/ not found under {project_root}"
        )

    # REQ-AUTHOR-054: warn when Phase Q's semantic index is absent.
    _check_semantic_index(project_root)

    click.echo(
        f"forge induce: project={project_root} folds={folds} "
        f"budget={'unset' if budget_usd is None else f'${budget_usd:.2f}'}"
    )

    proc = _run_nbb_induce(project_root, folds, budget_usd)
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "").strip()
        if len(tail) > 2000:
            tail = tail[-2000:]
        click.echo("---- nbb orchestrator stderr (tail) ----", err=True)
        click.echo(tail, err=True)
        raise InductionPipelineError(
            f"nbb induce-theory exited {proc.returncode}"
        )

    if proc.stdout:
        click.echo(proc.stdout, nl=False)

    theory_path, prov_path = _induced_paths(project_root)
    if not prov_path.exists():
        raise ProvenanceSidecarError(
            f"orchestrator exited 0 but sidecar missing at {prov_path}"
        )

    prov = _load_sidecar(prov_path)
    click.echo("")
    click.echo(_format_induce_summary(prov))
    click.echo("")
    click.echo(f"Wrote: {theory_path}")
    click.echo(f"Wrote: {prov_path}")


# ---------------------------------------------------------------------------
# forge revise — REQ-AUTHOR-050, 052
# ---------------------------------------------------------------------------


def _format_revision_report(report: Any) -> str:
    """Render a RevisionReport (from Phase Z) in human form.

    The shape we expect (per design.md):

        report.rules_affected: int
        report.status_counts: {":active": int, ":tentative": int, ":quarantined": int}
        report.transitions: [(rule_id, from_status, to_status), ...]
        report.full_quarantine_warning: bool
    """
    out: list[str] = []
    if getattr(report, "full_quarantine_warning", False):
        out.append("=" * 72)
        out.append("WARNING: full quarantine triggered — every rule in the "
                   "induced theory is now :quarantined.")
        out.append("=" * 72)
        out.append("")

    counts = getattr(report, "status_counts", None) or {}
    affected = getattr(report, "rules_affected", 0)

    def _count(*keys: str) -> int:
        for k in keys:
            if k in counts:
                return int(counts[k])
        return 0

    out.append("Revision summary:")
    out.append(f"  Rules affected:    {affected:>4}")
    out.append(f"  Rules active:      {_count(':active', 'active'):>4}")
    out.append(f"  Rules tentative:   {_count(':tentative', 'tentative'):>4}")
    out.append(f"  Rules quarantined: {_count(':quarantined', 'quarantined'):>4}")
    out.append("")

    transitions = getattr(report, "transitions", None) or []
    if transitions:
        out.append("Status transitions:")
        rows = list(transitions)
        for row in rows[:3]:
            if isinstance(row, dict):
                rid = row.get("rule_id") or row.get(":rule-id")
                frm = row.get("from") or row.get(":from")
                to = row.get("to") or row.get(":to")
            else:
                rid, frm, to = row
            out.append(f"  {rid}  {frm} -> {to}")
        if len(rows) > 3:
            out.append(f"  ... and {len(rows) - 3} more (see sidecar)")
    else:
        out.append("Status transitions: (none)")

    return "\n".join(out)


@cli.command("revise")
@click.argument("project_root", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--retracted-paper", "retracted_papers", multiple=True,
              help="Document id retracted from the corpus (repeatable).")
@click.option("--contradicting-atom", "contradicting_atoms", multiple=True,
              help="Atom id that contradicts an existing rule (repeatable).")
@_handle
def revise(
    project_root: Path,
    retracted_papers: tuple[str, ...],
    contradicting_atoms: tuple[str, ...],
) -> None:
    """Re-rank entrenchment and contract/quarantine rules on new evidence."""
    project_root = Path(project_root).resolve()

    if not retracted_papers and not contradicting_atoms:
        raise RevisionInputError(
            "forge revise requires at least one --retracted-paper or "
            "--contradicting-atom"
        )

    try:
        from scripts import _agm_revision  # type: ignore[import-not-found]
    except ImportError:
        click.echo(_PHASE_AA_REVISE_MSG, err=True)
        raise click.exceptions.Exit(2)

    theory_path, prov_path = _induced_paths(project_root)
    if not prov_path.exists():
        raise ProvenanceSidecarError(
            f"sidecar missing at {prov_path}"
        )

    click.echo(
        f"forge revise: project={project_root} "
        f"retracted={len(retracted_papers)} "
        f"contradicting={len(contradicting_atoms)}"
    )

    report = _agm_revision.revise_theory(
        induced_path=theory_path,
        prov_path=prov_path,
        retracted_docs=list(retracted_papers),
        contradicting_atoms=list(contradicting_atoms),
    )

    click.echo("")
    click.echo(_format_revision_report(report))


# ---------------------------------------------------------------------------
# forge theory — REQ-AUTHOR-050, 053
# ---------------------------------------------------------------------------


def _load_induced_theory(theory_path: Path) -> dict[str, Any]:
    """Load induced-theory.edn (rule forms only; raises on absent file)."""
    if not theory_path.exists():
        raise FileNotFoundError(
            f"induced-theory.edn not found at {theory_path}"
        )
    try:
        from scripts._edn_reader import read_edn  # type: ignore[attr-defined]
    except ImportError:  # pragma: no cover
        return {}
    return _coerce_edn(read_edn(theory_path.read_text(encoding="utf-8")))


def _rule_ids_from_theory(theory: dict[str, Any]) -> list[str]:
    """Walk the :forms vector and pull each defconstraint's id.

    The schema (per design doc) is::

        {:version 1 :forms [(defconstraint :induced/foo ...) ...]}

    We tolerate the rule-id appearing either as the second element of a
    sexp-shaped form or as an explicit ``:id`` key on a map-shaped form.
    """
    forms = theory.get("forms") or theory.get(":forms") or []
    out: list[str] = []
    for form in forms:
        if isinstance(form, (list, tuple)) and len(form) >= 2:
            head = form[0]
            head_name = getattr(head, "name", None) or str(head)
            if head_name in ("defconstraint", "defrule") and isinstance(form[1], str):
                out.append(form[1])
            elif head_name in ("defconstraint", "defrule"):
                rid = str(form[1])
                if rid.startswith(":"):
                    out.append(rid)
                else:
                    out.append(f":{rid}")
        elif isinstance(form, dict):
            rid = form.get(":id") or form.get("id")
            if rid:
                out.append(str(rid))
    return out


def _aggregate_theory_summary(
    theory: dict[str, Any], prov: dict[str, Any]
) -> str:
    rules_in_theory = _rule_ids_from_theory(theory)
    rules_prov = _sidecar_rules(prov)

    total_rules = len(rules_in_theory) if rules_in_theory else len(rules_prov)

    status_counts = {":active": 0, ":tentative": 0, ":quarantined": 0}
    entrenchments: list[float] = []
    total_cost = 0.0
    doc_counter: dict[str, int] = {}

    for rprov in rules_prov.values():
        status = _prov_field(rprov, "status")
        status_key = str(status) if status else None
        if status_key in status_counts:
            status_counts[status_key] += 1
        elif status_key and status_key.lstrip(":") in (
            "active", "tentative", "quarantined"
        ):
            status_counts[f":{status_key.lstrip(':')}"] += 1

        e = _prov_field(rprov, "entrenchment")
        if isinstance(e, (int, float)):
            entrenchments.append(float(e))

        cost = _prov_field(rprov, "cost-usd")
        if isinstance(cost, (int, float)):
            total_cost += float(cost)

        docs = _prov_field(rprov, "source-documents") or []
        if isinstance(docs, (list, tuple)):
            for d in docs:
                doc_counter[str(d)] = doc_counter.get(str(d), 0) + 1

    avg_e = sum(entrenchments) / len(entrenchments) if entrenchments else 0.0

    out = [
        f"Theory summary:",
        f"  Rules:                {total_rules}",
        (
            f"  Status:               :active {status_counts[':active']}  "
            f":tentative {status_counts[':tentative']}  "
            f":quarantined {status_counts[':quarantined']}"
        ),
        f"  Average entrenchment: {avg_e:.3f}",
        f"  Total induction cost: ${total_cost:.4f}",
        "",
        "Top-5 most-cited source documents:",
    ]
    top_docs = sorted(doc_counter.items(), key=lambda kv: kv[1], reverse=True)[:5]
    if not top_docs:
        out.append("  (no provenance source documents recorded)")
    else:
        for doc_id, n in top_docs:
            label = "rule" if n == 1 else "rules"
            out.append(f"  {doc_id:<32}  {n} {label}")
    return "\n".join(out)


def _deep_dive_rule(rule_id: str, prov: dict[str, Any]) -> str:
    rules = _sidecar_rules(prov)
    rprov = rules.get(rule_id) or rules.get(f":{rule_id.lstrip(':')}")
    if rprov is None:
        return f"Rule {rule_id} not found in sidecar."

    out = [f"Rule {rule_id}"]

    def _row(label: str, value: Any) -> None:
        if value is None:
            return
        out.append(f"  {label:<14} {value}")

    _row("Status:", _prov_field(rprov, "status"))
    e = _prov_field(rprov, "entrenchment")
    if isinstance(e, (int, float)):
        _row("Entrenchment:", f"{float(e):.3f}")

    atoms = _prov_field(rprov, "derived-from-atoms") or []
    docs = _prov_field(rprov, "source-documents") or []
    contras = _prov_field(rprov, "contradiction-atoms") or []
    if atoms or docs:
        atom_n = len(atoms) if isinstance(atoms, (list, tuple)) else 0
        doc_n = len(docs) if isinstance(docs, (list, tuple)) else 0
        _row("Support:", f"{atom_n} atoms across {doc_n} documents")
    if contras:
        contra_n = len(contras) if isinstance(contras, (list, tuple)) else 0
        _row("Contradicts:", f"{contra_n} atoms (advisory)")

    proposer = _prov_field(rprov, "proposed-by")
    if isinstance(proposer, dict):
        lineage = proposer.get(":lineage") or proposer.get("lineage")
        model = proposer.get(":model") or proposer.get("model")
        provider = proposer.get(":provider") or proposer.get("provider")
        _row("Proposed by:", f"{lineage}  model={model}  provider={provider}")
    elif proposer is not None:
        _row("Proposed by:", proposer)

    validators = _prov_field(rprov, "validated-by") or []
    if isinstance(validators, (list, tuple)) and validators:
        first = True
        for v in validators:
            if not isinstance(v, dict):
                continue
            backend = v.get(":backend") or v.get("backend") or "?"
            parts = []
            if ":held-out-folds" in v or "held-out-folds" in v:
                k = v.get(":held-out-folds") or v.get("held-out-folds")
                parts.append(f"{k}-fold")
            for key in (":sat-rate", "sat-rate"):
                if key in v:
                    parts.append(f"sat-rate {v[key]}")
                    break
            for key in (":tolerance-fit", "tolerance-fit"):
                if key in v:
                    parts.append(f"tolerance {v[key]}")
                    break
            for key in (":support-rate", "support-rate"):
                if key in v:
                    parts.append(f"support-rate {v[key]}")
                    break
            line = f"{backend} (" + ", ".join(parts) + ")" if parts else str(backend)
            _row("Validated by:" if first else "             ", line)
            first = False

    repair = _prov_field(rprov, "llm-repair-calls")
    if repair is not None:
        _row("Repair calls:", repair)

    cost = _prov_field(rprov, "cost-usd")
    if isinstance(cost, (int, float)):
        _row("Cost:", f"${float(cost):.4f}")

    neighbours = _prov_field(rprov, "semantic-neighbours")
    if isinstance(neighbours, (list, tuple)) and neighbours:
        _row("See also:", ", ".join(str(n) for n in neighbours))

    return "\n".join(out)


@cli.command("theory")
@click.argument("project_root", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--rule", "rule_id", default=None,
              help="Deep-dive into one rule's provenance.")
@_handle
def theory(project_root: Path, rule_id: str | None) -> None:
    """Inspect induced-theory.edn + the PROV-O sidecar."""
    project_root = Path(project_root).resolve()
    theory_path, prov_path = _induced_paths(project_root)

    if not theory_path.exists():
        raise FileNotFoundError(
            f"induced-theory.edn not found at {theory_path}"
        )

    theory_data = _load_induced_theory(theory_path)

    # REQ-AUTHOR-053 graceful-degrade: if the sidecar is missing or malformed
    # we still render the rule list from induced-theory.edn with empty
    # provenance.  The structured error is printed to stderr.
    prov_data: dict[str, Any] = {}
    sidecar_error: ProvenanceSidecarError | None = None
    try:
        prov_data = _load_sidecar(prov_path)
    except ProvenanceSidecarError as exc:
        sidecar_error = exc

    if sidecar_error is not None:
        from scripts._cli_errors import interpret
        click.echo(interpret(sidecar_error).render(), err=True)
        click.echo("", err=True)
        click.echo("Continuing with empty provenance — rule list only.", err=True)
        click.echo("")

    if rule_id is not None:
        click.echo(_deep_dive_rule(rule_id, prov_data))
        return

    click.echo(_aggregate_theory_summary(theory_data, prov_data))

    if sidecar_error is not None:
        rule_ids = _rule_ids_from_theory(theory_data)
        if rule_ids:
            click.echo("")
            click.echo("Rules (from induced-theory.edn; sidecar unavailable):")
            for rid in rule_ids:
                click.echo(f"  {rid}")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main() -> None:
    cli(prog_name="forge")


if __name__ == "__main__":
    main()
