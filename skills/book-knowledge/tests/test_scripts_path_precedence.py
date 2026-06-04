"""book-knowledge's own scripts/ dir must take precedence over forge's on the
package search path, so a future module-name collision resolves to the local
module rather than being shadowed by neurosym-forge's copy."""
from __future__ import annotations

from pathlib import Path

import scripts


def test_book_knowledge_scripts_dir_precedes_forge():
    own = Path(scripts.__file__).resolve().parent
    path_entries = [Path(p).resolve() for p in scripts.__path__]
    assert own in path_entries
    forge = (own.parents[1] / "neurosym-forge" / "scripts").resolve()
    # forge is still reachable (the EDN reader/writer live there) ...
    assert forge in path_entries
    # ... but only as a fallback: book-knowledge's own dir is searched first.
    assert path_entries.index(own) < path_entries.index(forge)
