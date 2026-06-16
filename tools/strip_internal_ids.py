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
# Bare clm-XXXX-NNNNNN tokens, either parenthesised — "(clm-...; status ...)" —
# or standalone. The parenthesised arm consumes the inner suffix up to ")"; the
# bare arm must NOT (4.4): the old `[^)]*` ran to end-of-text on an unparenthesised
# id, deleting the rest of the sentence ("clm-... was verified" -> "").
BARE_CLM_RE = re.compile(
    r"\s*(?:\(clm-\d{4}-\d{6}[^)]*\)|clm-\d{4}-\d{6})"
)


def strip_ids(text: str) -> str:
    """Remove claim-ledger sentences and bare/parenthesised clm-ids from text."""
    text = CLAIM_SENTENCE_RE.sub("", text)
    text = SEE_ALSO_RE.sub("", text)
    text = BARE_CLM_RE.sub("", text)
    # Clean doubled spaces / orphaned punctuation
    text = re.sub(r"  +", " ", text)
    text = re.sub(r" ([.,;:!?])", r"\1", text)
    return text


def main() -> None:
    paths = [
        Path("C:/bermuda-manual/book/releases/3.0.0/manuscript.md"),
    ] + [
        Path(f"C:/bermuda-manual/chapters/drafts/ch-{n:02d}/draft.md")
        for n in range(1, 11)
    ]
    for p in paths:
        text = p.read_text(encoding="utf-8")
        stripped = strip_ids(text)
        if stripped != text:
            p.write_text(stripped, encoding="utf-8")
            print(f"{p.name}: stripped")
        else:
            print(f"{p.name}: clean")


if __name__ == "__main__":
    main()
