"""Local PDF/text extraction for the offline corpus profile. No network."""
from __future__ import annotations

import re
from pathlib import Path

# Map common Windows-1252 / mojibake artifacts and smart punctuation to clean characters.
_MOJIBAKE = {
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "–": "-", "—": "-", "�": "'",
}


def normalize_text(text: str) -> str:
    for bad, good in _MOJIBAKE.items():
        text = text.replace(bad, good)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_pdf(path: Path) -> str:
    import pdfplumber  # deferred so unit tests not needing PDFs import cleanly
    chunks: list[str] = []
    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages:
            chunks.append(page.extract_text() or "")
    return normalize_text("\n".join(chunks))


def extract_any(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        return extract_pdf(path)
    return normalize_text(path.read_text(encoding="utf-8", errors="replace"))
