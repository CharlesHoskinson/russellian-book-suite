"""Real network/LLM boundaries for the voice-corpus pipeline (exercised live, not in tests).

scrapling-fetch is the suite's network boundary for discovery. It is invoked through its
OWN venv via subprocess, which (a) avoids colliding its `scripts` package with this tool's
`scripts` package, and (b) uses the venv where `scrapling[fetchers]` is installed.
yt-dlp is the one documented exception, scoped to caption retrieval, run from this tool's venv.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCRAPLING_FETCH = _REPO_ROOT / "skills" / "scrapling-fetch"


class AdapterError(RuntimeError):
    """A live boundary (scrapling-fetch / yt-dlp / LLM) failed."""


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


def scrapling_fetch(url: str, *, timeout: float = 60.0) -> str:
    """Fetch a URL's HTML via the scrapling-fetch skill's basic Fetcher, in its own venv."""
    try:
        proc = subprocess.run(
            [str(_scrapling_python()), "-c", _FETCH_SNIPPET, url],
            cwd=str(_SCRAPLING_FETCH),
            capture_output=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as e:
        raise AdapterError(f"scrapling-fetch timed out after {timeout}s for {url}") from e
    if proc.returncode != 0:
        stderr = proc.stderr.decode("utf-8", "replace").strip()[:500]
        raise AdapterError(f"scrapling-fetch failed for {url}: {stderr}")
    return proc.stdout.decode("utf-8", "replace")


def ytdlp_runner(args: list[str], *, timeout: float = 600.0) -> subprocess.CompletedProcess:
    """Run yt-dlp from this tool's venv. Caption-only; never downloads media.

    `args[0]` is the literal "yt-dlp"; invoke the installed module via the current
    interpreter so the tool venv's yt-dlp is used regardless of PATH.
    """
    try:
        return subprocess.run(
            [sys.executable, "-m", "yt_dlp", *args[1:]],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as e:
        raise AdapterError(f"yt-dlp timed out after {timeout}s: {' '.join(args[1:])[:200]}") from e


def make_anthropic_llm_call(model: str | None = None, *, client: Any = None) -> Callable[[str], str]:
    """Build a real llm_call backed by the Anthropic SDK.

    Reads ANTHROPIC_API_KEY from the environment (SDK default). Model defaults to
    claude-opus-4-8, override via the VOICE_CORPUS_MODEL env var or the `model` arg.
    Pass `client` (a stub) in tests to avoid the network and the SDK import.
    """
    model_id = model or os.environ.get("VOICE_CORPUS_MODEL", "claude-opus-4-8")
    if client is None:
        import anthropic

        client = anthropic.Anthropic()

    def _call(prompt: str) -> str:
        resp = client.messages.create(
            model=model_id,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(getattr(b, "text", "") for b in resp.content if getattr(b, "type", "") == "text")

    return _call
