# Vendored concreteness lexicon — provenance

`concreteness-brysbaert.csv` is a compact two-column projection (`word,conc`) of the
Brysbaert concreteness norms, used by the `concrete-anchor` and `analogy-mapping`
liveliness signals.

- **Source dataset:** Brysbaert, M., Warriner, A. B., & Kuperman, V. (2014).
  *Concreteness ratings for 40 thousand generally known English word lemmas.*
  Behavior Research Methods, 46, 904–911.
- **Fetched from:** the public mirror
  `https://raw.githubusercontent.com/ArtsEngine/concreteness/master/Concreteness_ratings_Brysbaert_et_al_BRM.txt`
  via the suite's sanctioned `scrapling-fetch` surface (one-time documented network step).
- **Projection:** the `Conc.M` (mean concreteness, 1–5 scale) column keyed by the
  lowercased `Word`; multi-word bigram entries dropped (single words only).
  37,058 rows.
- **Licence:** the norms are published as freely available research data.

Regenerating is a documented network step (scrapling-fetch); the loader and all
scorers that read this CSV are network-free.
