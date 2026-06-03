"""forge meta subcommand group routing."""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FORGE = ROOT / "neurosym-forge" / "scripts" / "forge_cli.py"


def _run(args):
    return subprocess.run([sys.executable, str(FORGE)] + args,
                          capture_output=True, text=True, check=False)


def test_meta_help_lists_subcommands():
    out = _run(["meta", "--help"])
    assert out.returncode == 0
    for sub in ("acquire", "synthesize", "lens", "gap"):
        assert sub in out.stdout


def test_meta_lens_requires_workspace():
    out = _run(["meta", "lens"])
    assert out.returncode != 0
