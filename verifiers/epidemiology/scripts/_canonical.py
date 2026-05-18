"""Canonical Z3-variable-name algorithm.

The Z3 variable name for a predicate-subject pair is the framework's
single most load-bearing string. Three languages — CLJS, Python, Rust —
must agree byte-for-byte on its construction. This module is the Python
source of truth; the CLJS and Rust implementations carry the same
algorithm and the same golden test vectors at
`skills/neurosym-forge/tests/golden/canonical_var_name.edn`.

REQ-EDN-042 (Python implementation).
"""
from __future__ import annotations


def canonical_var_name(predicate: str, subject: str) -> str:
    """Return the canonical Z3 variable name for a (predicate, subject) pair.

    Algorithm:
      pred = predicate.lstrip(':?')
      subj = subject.lstrip(':?')
      return f"{pred}_{subj}"

    Accepts predicate / subject in any of three EDN surface forms:
      :foo   (keyword written as a Python str ":foo")
      ?foo   (logic-var symbol)
      foo    (bare identifier)
    """
    pred = predicate.lstrip(":?")
    subj = subject.lstrip(":?")
    return f"{pred}_{subj}"
