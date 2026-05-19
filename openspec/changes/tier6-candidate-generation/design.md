# Design: tier6-candidate-generation

## Three candidate sources, one interface

A uniform protocol in `induce_theory.cljs`:

```clojure
(defprotocol CandidateSource
  (source-name   [_])                          ;; :horn-body / :popper / :llm
  (generate      [_ atoms schema cluster opts])
  ;; returns: (sequence-of {:edn ... :cited-atoms [...] :origin <kw>})
  )
```

Each source emits a uniform candidate map; the orchestrator
does not branch on source identity downstream of generation.

### Source 1 — Horn-body mining (AMIE / AnyBURL-style)

A Cozo Datalog query enumerates frequent predicate-pair
co-occurrences over the atomspace:

```datalog
?[p1, p2, count(*)] :=
  *atom{predicate: p1, document: d, ...},
  *atom{predicate: p2, document: d, ...},
  p1 != p2
:order -count(*)
:limit N
```

Each surviving pair is wrapped in a `defconstraint`
candidate template `(implies (p1 ?d) (p2 ?d))`. The Cozo
support count becomes the candidate's `:support` metadata.

### Source 2 — Popper-style typed search

Bounded enumeration over the schema's predicate signatures,
≤4 literals per rule (the Popper sweet spot). Mode
declarations are derived mechanically from
`booklogic-schema.edn`'s `:args` and `:return` sorts.

```
For each predicate P returning :real:
  For each predicate Q returning :real with matching binding sort:
    emit (approx= (P ?d) (Q ?d) :tolerance ε)
```

The ε placeholder is filled by Phase X (SMT numeric
fitting); the typed search emits the structural form.

### Source 3 — LLM proposer (Phase V)

The Phase V proposer is called once per atom cluster from
`SemanticIndex`. The cluster's atoms form the user-prompt
section; the schema + BNF form the system prompt. Output is
a single EDN form per call; the grammar enforcer rejects
non-conforming output before it enters the queue.

## Deduplication via canonical form

Two candidates are alpha-equivalent if they share canonical
S-expression form after var-name canonicalisation. The
existing `_canonical.py` already canonicalises variable
names; this change extends it with
`canonical_constraint_form(edn) -> str` and the orchestrator
de-dupes by that string key BEFORE validation. Origin
metadata is preserved: if two sources produce the same
canonical form, the candidate carries `:origin [:horn-body
:llm]`.

## Semantic-coherence ranking

When Phase Q's `SemanticIndex` is available:

```python
def coherence(candidate, sem_index):
    atoms = candidate["cited_atoms"]
    if len(atoms) < 2:
        return 1.0
    pairs = itertools.combinations(atoms, 2)
    sims = [sem_index.cosine(a, b) for a, b in pairs]
    return mean(sims)
```

Candidates with mean cosine > 0.5 are ranked at the top of
the queue; the orchestrator validates higher-ranked
candidates first, so the budget hits the most likely
winners earliest.

## Persisted candidate queue

`work/induction/candidates.edn` carries the full queue
including rejected candidates:

```edn
{:version 1
 :generated-at "2026-05-19T18:00:00Z"
 :corpus-size 47
 :candidates
 [{:id "c-001"
   :canonical-form "(defconstraint ...)"
   :origin [:horn-body :llm]
   :cited-atoms ["adsc-001-A12" "adsc-014-B03"]
   :coherence 0.72
   :status :pending
   :rejection-reason nil}
  {:id "c-002"
   :canonical-form "(defconstraint ...)"
   :origin [:popper]
   :cited-atoms ["adsc-099-X07"]
   :coherence 0.34
   :status :rejected
   :rejection-reason :grammar-fail/illegal-op}]}
```

The queue is the debugging surface for post-mortem analysis:
inspecting why a candidate was dropped, which source
produced which winner, what coherence cut survived.

## Budget tracking

`NEUROSYM_INDUCTION_BUDGET_USD` is read at orchestrator
startup. Each LLM call consults the Phase P SQLite cache
for the cost-per-call delta; the orchestrator increments
the run's spend counter on each non-cached call. When spend
exceeds the budget, the LLM source returns `[]` from
`generate`; Horn-body and Popper sources are unaffected.

The cost field is `:prov/cost-usd` on the candidate; the
total spend at termination is logged to
`work/induction/budget.json`.

## Edge case — small corpora

A corpus under 10 atoms makes Horn-body's frequent-pair
statistics meaningless. The Horn-body source emits a
structured warning `{:warning :corpus-too-small :n <int>
:threshold 10}` and returns `[]`. Popper and LLM still run;
Popper's typed search and the LLM's per-cluster proposal
work on any non-zero atomspace.

## Why three sources, not two?

A single deep-research report could have argued for just
LLM + Horn-body, treating Popper as redundant. Both reports
explicitly recommended all three:

- AMIE / Horn-body catches frequent co-occurrence shapes
- Popper catches typed combinations the LLM under-samples
- LLM catches relational shapes Popper's bounded search
  cannot enumerate at the depth the schema implies

Dropping any one source narrows the candidate distribution.
The triple is defensive in depth; deduplication keeps the
queue tractable.

## Why not bundle into Phase V (grammar)?

Phase V is the SHAPE gate; this change is the GENERATION
stage. The grammar enforcer runs on every candidate
regardless of source; the source enumeration is the layer
above. Bundling the two would couple "what can be a
constraint" with "where constraints come from" — two
concerns that should evolve independently.
