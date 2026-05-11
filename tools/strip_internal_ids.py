"""Strip 'Claim ledger: clm-...' and bare 'clm-XXXX-NNNNNN' references from
chapter drafts and the assembled manuscript.
"""
import re
from pathlib import Path

# Match clauses like:
#   " Claim ledger: clm-2026-000148 (status: verified); see also clm-2026-000143 on the Board's role."
# Strip from "Claim ledger:" to the end of that sentence (next period).
CLAIM_SENTENCE_RE = re.compile(
    r"\s*Claim ledger:[^.]*\.",
    re.IGNORECASE,
)
# Catch "see also clm-XXXX-NNNNNN ..." continuation sentences
SEE_ALSO_RE = re.compile(
    r"\s*see also clm-\d{4}-\d{6}[^.]*\.",
    re.IGNORECASE,
)
# Bare clm-XXXX-NNNNNN tokens with surrounding parenthetical / spaces
BARE_CLM_RE = re.compile(r"\s*\(?clm-\d{4}-\d{6}[^)]*\)?")

paths = [
    Path("C:/bermuda-manual/book/releases/3.0.0/manuscript.md"),
] + [
    Path(f"C:/bermuda-manual/chapters/drafts/ch-{n:02d}/draft.md")
    for n in range(1, 11)
]

for p in paths:
    text = p.read_text(encoding="utf-8")
    orig = text
    text = CLAIM_SENTENCE_RE.sub("", text)
    text = SEE_ALSO_RE.sub("", text)
    text = BARE_CLM_RE.sub("", text)
    # Clean doubled spaces / orphaned punctuation
    text = re.sub(r"  +", " ", text)
    text = re.sub(r" ([.,;:!?])", r"\1", text)
    if text != orig:
        p.write_text(text, encoding="utf-8")
        print(f"{p.name}: stripped")
    else:
        print(f"{p.name}: clean")
