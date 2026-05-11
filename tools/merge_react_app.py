"""Merge v3.0.0 data payload + manuscript into v1.0.0's React-bundled HTML."""
import re
from pathlib import Path

V1 = Path("C:/bermuda-manual/book/releases/1.0.0/manuscript.html")
V3 = Path("C:/bermuda-manual/book/releases/3.0.0/manuscript.html")

v1_text = V1.read_text(encoding="utf-8")
v3_text = V3.read_text(encoding="utf-8")

PAYLOAD_RE = re.compile(
    r'(<script id="book-payload" type="application/json">)(.*?)(</script>)',
    re.DOTALL,
)
MANUSCRIPT_RE = re.compile(
    r'(<script id="book-manuscript" type="text/markdown">)(.*?)(</script>)',
    re.DOTALL,
)

m_payload_v3 = PAYLOAD_RE.search(v3_text)
m_manuscript_v3 = MANUSCRIPT_RE.search(v3_text)
assert m_payload_v3, "v3 missing book-payload"
assert m_manuscript_v3, "v3 missing book-manuscript"

new_payload_body = m_payload_v3.group(2)
new_manuscript_body = m_manuscript_v3.group(2)

merged = PAYLOAD_RE.sub(
    lambda m: m.group(1) + new_payload_body + m.group(3), v1_text, count=1
)
merged = MANUSCRIPT_RE.sub(
    lambda m: m.group(1) + new_manuscript_body + m.group(3), merged, count=1
)

V3.write_text(merged, encoding="utf-8")
print(f"merged {V3}")
print(f"v1 size:     {len(v1_text):>9}")
print(f"v3 in:       {len(v3_text):>9}")
print(f"v3 merged:   {len(merged):>9}")
