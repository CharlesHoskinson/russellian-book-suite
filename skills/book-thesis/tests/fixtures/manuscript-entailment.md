# Chapter 1: Entailment Fixture

::: paragraph supports="first-leg" evidence="clm-2026-000001"
The first paragraph uses a fenced-div carrier pointing at the first-leg
sub-argument. The entailment dispatcher should turn this into a payload.
:::

<!-- supports: second-leg; evidence: clm-2026-000002 -->
The second paragraph uses the HTML-comment carrier instead. It points at
the second-leg sub-argument, which also sits under :Thesis.

::: paragraph supports="first-leg"
A third paragraph reusing the first-leg node, this time without a cited
evidence claim. The payload should still build but with an empty
``cited_claim`` field.
:::
