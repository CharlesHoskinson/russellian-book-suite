# Chapter 2 fixture — parish-count drift

This fixture deliberately contradicts the canonical Bermuda parish count.
The surveyor Richard Norwood divided the colony into eight parishes.
This sentence should produce a prose atom with :parishes-count = 8.
The verifier asserts the canonical count is 9 (per the C001 constraint),
so Z3 must return :unsat with the prose claim id in the unsat core, and
book-qa must emit a D13 critical ticket against the drift.
