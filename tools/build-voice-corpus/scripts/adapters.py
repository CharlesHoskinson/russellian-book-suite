"""Real network/LLM boundaries for the voice-corpus pipeline (exercised live, not in tests).

scrapling-fetch is the suite's network boundary for discovery. It is invoked through its
OWN venv via subprocess, which (a) avoids colliding its `scripts` package with this tool's
`scripts` package, and (b) uses the venv where `scrapling[fetchers]` is installed.
yt-dlp is the one documented exception, scoped to caption retrieval, run from this tool's venv.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCRAPLING_FETCH = _REPO_ROOT / "skills" / "scrapling-fetch"


def _scrapling_python() -> Path:
    win = _SCRAPLING_FETCH / ".venv" / "Scripts" / "python.exe"
    posix = _SCRAPLING_FETCH / ".venv" / "bin" / "python"
    return win if win.exists() else posix


_FETCH_SNIPPET = (
    "import sys\n"
    "from skill_api import fetch\n"
    "page = fetch(sys.argv[1])\n"
    "sys.stdout.buffer.write(page.html.encode('utf-8'))\n"
)


def scrapling_fetch(url: str) -> str:
    """Fetch a URL's HTML via the scrapling-fetch skill's basic Fetcher, in its own venv."""
    proc = subprocess.run(
        [str(_scrapling_python()), "-c", _FETCH_SNIPPET, url],
        cwd=str(_SCRAPLING_FETCH),
        capture_output=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"scrapling-fetch failed for {url}: {proc.stderr.decode('utf-8', 'replace').strip()}"
        )
    return proc.stdout.decode("utf-8", "replace")


def ytdlp_runner(args: list[str]) -> subprocess.CompletedProcess:
    """Run yt-dlp from this tool's venv. Caption-only; never downloads media.

    `args[0]` is the literal "yt-dlp"; invoke the installed module via the current
    interpreter so the tool venv's yt-dlp is used regardless of PATH.
    """
    return subprocess.run(
        [sys.executable, "-m", "yt_dlp", *args[1:]],
        capture_output=True,
        text=True,
    )
