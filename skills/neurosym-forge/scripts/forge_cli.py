"""Interactive author CLI for neurosym-forge (REQ-AUTHOR-040..046).

Subcommands:

``forge add-constraint``
    Append a defconstraint form to ``rules/booklogic/constraints.edn``.

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

import click


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


@cli.command("add-constraint")
def add_constraint() -> None:
    """Append a defconstraint to <project_root>/rules/booklogic/constraints.edn."""
    click.echo("add-constraint not yet wired")


@cli.command("suggest-lifts")
def suggest_lifts() -> None:
    """Propose deflift candidates for an unmatched claim via Phase P's LLM provider."""
    click.echo("suggest-lifts not yet wired")


@cli.command("explain-defect")
def explain_defect() -> None:
    """Render an unsat-core walkthrough for a defect."""
    click.echo("explain-defect not yet wired")


@cli.command("similar")
def similar() -> None:
    """Print the top-k semantically-similar claims to <claim_id>."""
    click.echo("similar not yet wired")


@cli.command("render")
def render() -> None:
    """Shell out to Phase T's render_annotations.py."""
    click.echo("render not yet wired")


def main() -> None:
    cli(prog_name="forge")


if __name__ == "__main__":
    main()
