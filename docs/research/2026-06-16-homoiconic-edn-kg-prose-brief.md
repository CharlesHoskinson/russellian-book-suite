# Research brief â€” Homoiconic EDN Knowledge Graph that improves prose writing

**Captured:** 2026-06-17 (source PDF dated 2026-06-16, held outside the repo).
**Role:** informs `docs/specs/2026-06-17-kg-prose-enhancement-roadmap-design.md` (the v0.5 KG-for-prose roadmap).

> Text extracted verbatim from the source PDF via `pdftotext -layout`. Footnote superscripts and page-break artifacts are retained as-is.

---

Research Brief for a Homoiconic EDN Knowledge
Graph That Improves Prose Writing

Executive summary

The highest-leverage move is to make the writer claim-first and citation-first, not passage-first. In
practice, that means the prose pipeline should receive a chapter plan built from graph structure--
communities, thesis nodes, sub-arguments, contested claims, and source spans--then generate sentences
whose smallest support unit is a claim plus one or more source-span anchors. This transfers the
strongest parts of GraphRAG and attributed generation into your actual schema while avoiding one of
GraphRAG's weakest points: community summaries are useful for global coherence, but they are often hard
to trace cleanly back to exact source text unless attribution is designed in from the start. 1

The second move is to add a formal argumentation layer on top of your existing supports ,
 conflicts-with , counter-claim , load-bearing , and axiom relations. Your schema is already
close to an abstract or bipolar argumentation framework. The practical win is not "philosophical elegance";
it is a computable writer warning surface: this paragraph relies on a defeated claim, this attack is unanswered,
this sub-argument has no admissible defense, this load-bearing sentence is backed only by axioms. Grounded-
style acceptability is the best first target because it is explainable and computationally tractable; richer
preferred/stable semantics are useful later, but they usually want ASP or another non-monotonic solver
rather than plain embedded Datalog. 2

The third move is to introduce belief-erosion accounting. Your append-only ledger and p-prior / p-
posterior fields already create the right substrate. What is missing is a deterministic propagation rule
that updates a claim's effective support after source refresh, contradiction, supersession, or rebuttal. A full
probabilistic logic stack such as MLN or PSL is informative academically, but for this pipeline a bounded,
deterministic, provenance-aware propagation layer is a better engineering choice: faster, more debuggable,
and compatible with offline reproducibility. 3

The fourth move is to treat proof obligations as first-class KG entities. For mathematically or scientifically
delicate claims, the writer should never rely only on prose-level confidence. A proof-obligation entity
discharged by Z3, cvc5, Lean, a units checker, or a statistical-reporting checker should gate whether a claim
is available to the "math prose" and "halmos" passes. This is the cleanest way to turn existing external
verifiers into attributable, replayable evidence in the graph. Lean, mathlib, Z3, and cvc5 all support an
offline story; autoformalization is advancing quickly, but still needs tight scope and explicit uncertainty
labeling. 4

The fifth move is a deterministic contradiction workbench. Push exact symbolic checks into
EDNDatalog where possible: temporal overlap checks, normalized unit comparisons, quantity
mismatches, stale-source detection, supersession integrity, and explicit thesis-level incompatibilities.
Reserve NLI and external claim-verification models for the residue: paraphrastic contradiction, implicature,

                                                                           1
and scientific stance detection. That division matches the literature and preserves determinism where it
matters most. 5

The sixth move is to solve code  claim fusion in two stages: first with deterministic linking evidence from
filenames, symbol references, import/call graphs, and static-analysis facts; later with ranking models such
as embeddings or GNN link prediction. The literature on code-graph retrieval strongly suggests that
structural retrieval helps repository-scale reasoning and reduces project-specific hallucination, but high-
confidence automatic linking still benefits from explicit evidence capture and calibrated uncertainty. 6

The substrate verdict is conservative: keep Cozo now, but harden the seam and reduce dependency risk
immediately. The strongest evidence against an immediate switch is that no alternative simultaneously
matches your requirements for embedded execution, graph algorithms, Datalog-like querying, offline
operation, and Python-friendly integration. Cozo still offers exactly the graph primitives your design already
exploits, but its visible release cadence is slow, with the latest release I could verify being v0.7.6 from
December 11, 2023. DataScript is actively released and elegant for EDN/Datalog work, but it is in-memory,
browser-oriented, and not a drop-in durable backend. Asami's original repository explicitly says it is no
longer maintained. Soufflé and FlowLog are important reference engines, but they do not dominate Cozo
for this specific product shape. 7

Highest-leverage enhancements

Enhancement             Writing quality  Component touched          Evidence strength
                        improved

Claim-first chapter     Well-reasoned,    chapter ,                 A -- hierarchical
planner with            fact-based        claim-chapter , thesis-   GraphRAG and local/
community-aware                          node , community , new     global retrieval are
retrieval bundles                        projector + writer prompt  established, but exact
                                         contract                   source traceability
Sentence-level          Fact-based,                                 needs explicit design.
citation contract with  attributable      claim , source-span ,
NLI-backed span                           source , new writer-         8
validation and revise                    assertion / citation-
loop                                     check entities, external   A -- ALCE, FActScore,
                                         checker seam               RARR, Self-RAG,
Grounded-               Well-reasoned                               LongCite, and CiteEval
acceptability                             supports , conflicts-     form a strong stack. 9
argumentation layer                      with , counter-claim ,
                                          load-bearing , new        B -- strong formal
                                         acceptability rules        foundations, but direct
                                                                    deployment studies in
                                                                    writing pipelines are
                                                                    thinner. 10

                                         2
Enhancement            Writing quality    Component touched             Evidence strength
                       improved
Deterministic belief-                     ledger projector, p-          B -- well grounded in
erosion propagation    Fact-based,        posterior , derived-          provenance and
with provenance-       scientifically     from , supports ,             probabilistic reasoning,
backed justifications  sound               conflicts-with , new         but exact propagation
                                           justification-set            policy must be product-
Contradiction          Fact-based,        relation                      tuned. 11
workbench with         scientifically
symbolic first pass    sound              new normalized temporal /     A for symbolic checks, B
and external residual                     quantity relations,           for NLI residue. 12
checker                Mathematical,      contradiction projector, NLI
                       scientific         seam
First-class proof
obligations for math/  Fact-based, well-  new proof-obligation ,        B -- strong tooling and
science gating         reasoned about      verification-artifact ,      rapidly improving
                       software            requires-proof relations;    research, but domain
Deterministic                                                           tuning matters. 13
codeclaim                                 Z3 / cvc5 / Lean seam
autolinking, with
model ranking only                         code-node , code-edge ,      B -- good adjacent
as second stage                            code-claim-link , new        evidence from code
                                           link-evidence relation       graphs and repository
                                                                        reasoning, but direct
                                          and linker projector          prose-writing evidence
                                                                        is still emerging. 14

In this brief, A means production-ready or already proven in closely adjacent settings, B means promising
and implementable with moderate uncertainty, and C means speculative or research-only. 15

State of the art survey

KG-grounded generation. The current best evidence says graph-grounding helps most when the task
needs global coherence, multi-hop reasoning, or hierarchical summarization, not as an automatic
replacement for every flat-RAG case. Microsoft GraphRAG's official design explicitly separates Global Search
for holistic questions from Local Search for entity-centered traversal and DRIFT Search for entity retrieval
plus community context. Dynamic community selection further shows that global retrieval should traverse
the hierarchy selectively rather than summarize every community at a fixed level. Newer evaluations are
more sober than the early hype: systematic comparisons and GraphRAG-Bench both report that GraphRAG
wins more clearly on complex reasoning and summarization than on straightforward fact retrieval, and may
underperform vanilla RAG when graph construction is incomplete or the task is not structurally demanding.
For your design, the transfer is direct: let communities and thesis structure plan chapters, but let claims
and source spans ground sentences. That gives global coherence without sacrificing source traceability.

  16

Attribution and factuality. The most robust stack today is not a single method but a layered one. ALCE
established reproducible automatic evaluation for answers-with-citations; FActScore showed that long-form

                                          3
factuality must be measured at the level of atomic facts; RARR demonstrated a practical retrieve-and-
revise loop for unsupported text; Self-RAG and CRAG showed the value of explicit retrieval gating and
retrieval-quality assessment; LongCite and "Attribute First, then Generate" pushed attribution toward
sentence-level or local spans instead of document-level footnotes; and CiteEval showed that plain NLI over
cited snippets is not enough for citation quality, because evaluation must consider the retrieval context,
user query, and the generated statement together. For your ledger, this transfers cleanly: each writer
sentence should decompose into atomic claims, attach to claim.id and source-span.id , then pass a
sentence-to-span support check and, if needed, a revise pass that either changes the sentence or
downgrades the claim's status. 17

Computational argumentation. Your current schema already contains the primitives needed for an
argumentation layer: support, conflict, rebuttal, load-bearing status, and axiomatic status. Dung's abstract
argumentation remains the simplest formal lens for attack/defense reasoning; ASPIC+ and ABA add
structured derivations that can better match thesis-node  sub-argument  claim ; quantitative
bipolar argumentation is especially relevant because your graph already has both support and conflict
edges plus confidence-like weights. The engineering lesson from the literature is that grounded or
complete semantics are the right first deployment target when you want deterministic, explainable
warnings; richer semantics such as preferred or stable are useful but computationally harder and more
naturally handled in ASP than in pure Datalog. That makes a two-tier design attractive: Datalog for
grounded admissibility and warning generation, optional ASP for deeper offline audits. 18

Belief revision and uncertainty. The classic TMS and AGM traditions are still conceptually valuable, but the
practical transfer to your pipeline is: track justification sets, preserve minimal-change updates, and
separate status lifecycle from numerical confidence propagation. Provenance semirings and recent
Datalog provenance work are especially relevant because they give a principled way to talk about why a
claim is believed, which supports matter, and which source refresh invalidated the derivation. Full probabilistic
logic systems such as MLN, PSL, and ProbLog remain useful references, but they are heavier than you need
if your main goal is to tell the writer that support eroded after a refresh. A bounded, deterministic
propagation policy plus explicit provenance is a better fit for a byte-deterministic offline build. 19

Contradiction and consistency. The literature now strongly differentiates between contradiction types.
Some are best handled symbolically: the same subject­predicate with incompatible objects, temporal
interval overlap, incompatible quantities after unit normalization, invalid supersession chains, or source
freshness problems. Others remain inherently fuzzy and benefit from NLI or domain claim-verification
models, especially in scientific text. Temporal claim verification has advanced enough to justify a dedicated
temporal normalization layer, and recent work on unit-aware verification shows that explicit unit handling is
not optional in scientific writing. Citation evaluation research also reinforces that support/contradiction
judgments are noisy if the checker sees only an isolated sentence pair rather than normalized context. 20

Mathematical and scientific rigor. Autoformalization and proof-assistant loops have improved rapidly,
with Lean-centered tooling and mathlib becoming the practical focal point. Lean's small kernel and mature
library ecosystem make it the best target for rigorous math claims that justify the overhead; Z3 and cvc5 are
better for bounded symbolic obligations, numeric constraints, and consistency checks. The frontier result is
that autoformalization quality is rising fast, including competition-level mathematics, but current systems
are still selective and error-prone enough that formalization should be framed as a proof obligation
workflow, not as a magical one-shot validator. On the scientific side, the more immediate wins are units

                                                                           4
checks, statistical-reporting checks, and explicit evidence-norm checks such as whether a claim reports
effect sizes, uncertainty, or evidence type appropriately. 21

Substrate and homoiconicity. The EDN-front design remains a strong architectural choice because it keeps
schema, constraints, and rules as data. Cozo is still attractive because it is embedded, transactional,
Datalog-oriented, time-travel capable, and already includes the graph algorithms your KG uses. But the
maintenance concern is real: the latest release I could verify is v0.7.6 from December 11, 2023.
DataScript is actively maintained and very congenial to EDN/Datalog, but it is explicitly an immutable, in-
memory, browser-oriented database, which makes it a poor direct replacement for your single durable
store. The original Asami repository states that it is no longer maintained, though it points to a fork for
ongoing development; the evidence I could verify still points to an in-memory Clojure/ClojureScript graph
store with the latest visible versioning around 2.2.4 . Soufflé is active and excellent for compiled Datalog,
and FlowLog/DBSP represent exciting incremental-Datalog directions, but none of them dominate Cozo
across embedded deployment, graph algorithms, Python seam simplicity, and swappability. 22

Cross-graph fusion. The strongest adjacent evidence comes from code indexing and repository-level code
reasoning rather than prose-writing studies per se. Glean, Joern/CPG, and CODEXGRAPH all demonstrate
that structural code graphs improve code navigation, repository reasoning, and documentation-related
tasks. De-Hallucinator shows a directly relevant pattern: project-specific grounding reduces invented APIs
and improves correctness. In graph learning, embeddings such as TransE and RotatE remain strong
baselines for missing-edge ranking, while current GNN link-prediction work increasingly emphasizes
uncertainty calibration. For your KG, the implication is pragmatic: use deterministic evidence first, then
make learned link prediction a candidate ranker, not an unreviewed fact ingester. 23

Concrete enhancement proposals

Community-to-chapter retrieval bundles target global coherence and reasoned organization. Add a
projector that materializes a chapter-retrieval-bundle relation from existing chapter , claim-
chapter , thesis-node , sub-argument , community , code-claim-link , and claim data. The
bundle should contain: the dominant communities for the chapter, the top load-bearing claims, unresolved
rebuttals, and the minimal set of source-span anchors for those claims. In EDN terms, this is a new
 defquery and projector, not a new engine. The writer should receive this structured bundle as EDN/JSON,
never a flat passage pile. Micro-example: a chapter on a software subsystem starts with two communities
linked to the same thesis; the bundle surfaces that the chapter's main thesis is supported by three verified
claims but attacked by one disputed counter-claim whose rebuttal window is still open. The writer then gets
a prompt scaffold like "state main thesis, present support claims in order, include caveat on disputed
counter-claim." Evidence strength is A; the most important citation is Microsoft's GraphRAG global/local
retrieval design. Feasibility is high because it reuses data you already compute and keeps determinism in
the projector. 24

Writer-assertion contract with local attributions targets fact-based and attributable writing.
Introduce a first-class writer-assertion entity with fields such as sentence-text , asserts-
claim , cites-span , citation-check-status , and revision-origin . Every generated sentence
must bind to one or more existing claim.id values and one or more source-span.id values. A post-
generation checker seam runs sentence-to-span support scoring, preferably with a small NLI or citation-
faithfulness model, and a deterministic policy: if support fails, either revise the sentence from the cited

                                                                           5
spans or downgrade it to a hedged form and mark it non-canonical. Micro-example: the sentence "Module
X guarantees lock-free writes" binds to claim/C17 and source-span/S301 ; the checker finds only
partial support, so the revise step rewrites it to "Module X aims to reduce write contention" and links it to
the same source span with a partial-support flag. Evidence strength is A; the key citation is "Attribute
First, then Generate." Feasibility is high: it needs one new external-checker seam and a small schema
extension, but it fits your ledger and provenance model naturally. 25

Atomic-fact decomposition and research-and-revise targets factual precision in long-form prose. Add a
 draft-atomic-fact relation produced by a deterministic decomposer or tightly scoped LLM prompt run
over draft prose. Each atomic fact is then mapped to an existing claim or flagged as novel-draft-
claim . Facts without adequate support trigger a RARR-style revise loop against the KG, not the open web.
Micro-example: a paragraph contains four atomic facts; three map to verified claims with spans, one maps
to nothing and becomes novel-draft-claim/N1 . The system refuses to publish the paragraph until
 N1 is either ingested into the ledger with evidence or removed. Evidence strength is A; the key citation is
FActScore. Feasibility is medium-high because the decomposition step is not perfect, but the pipeline
remains offline and deterministic if you freeze the model and prompt. 26

Grounded acceptability warnings target well-reasoned argumentation. Implement Datalog rules that
derive attacked , defended , undefeated-attacker , grounded-accepted , and grounded-
rejected over supports , conflicts-with , counter-claim , sub-argument , and load-
bearing . Keep the semantics modest at first: grounded-style acceptability, plus explicit warnings for load-
bearing claims that are unsupported or attacked by undefeated arguments. Micro-example: thesis T1
relies on claim C9 , marked load-bearing ; C9 is attacked by CC2 , and the only rebuttal to CC2 is
itself supported by a disputed source. The query marks C9 as "contested-load-bearing-with-undefended-
attack," and the writer gets a warning to either defend it explicitly or downgrade the paragraph. Evidence
strength is B; the key citation is Dung's acceptability framework, backed by later ASPIC+ and ASP results.
Feasibility is high as a rule layer; you do not need a new store, only new derived relations. 27

Bipolar confidence propagation with belief erosion targets fact-based and scientifically cautious
writing. Materialize a new effective-confidence relation derived from p-prior , p-posterior ,
 supports , derived-from , conflicts-with , source.trust-score , and source freshness. The
propagation policy should be deterministic and explicit: for instance, bounded support aggregation for
convergent support, attenuation for long derivation chains, and subtractive or adversarial penalties for
conflicts from trusted or fresher sources. Also materialize support-erosion-reason using minimal
justification sets. Micro-example: claim C42 originally had p-posterior = 0.82 , supported by two
source spans; one source is refreshed and now contradicts the old text, dropping
 effective-confidence to 0.54 , with
 support-erosion-reason = refreshed-source+trusted-conflict . The writer then sees "avoid
assertive phrasing; cite the dispute." Evidence strength is B; the key citation is provenance semirings for
Datalog. Feasibility is good because you can avoid a full probabilistic engine and still get a usable, auditable
signal. 28

Provenance-on-demand for load-bearing claims targets debuggability and attributable reasoning. Full
why-provenance for recursive Datalog can be intractable, so do not make it the default for every query.
Instead, add an optional why-support seam that computes minimal-depth or bounded-cardinality
provenance only for load-bearing claims flagged by the writer or checker. Use a SAT-backed helper if

                                                                           6
needed, and cache the result in the ledger as justification-set . Micro-example: a key chapter
sentence rests on C87 ; the writer requests explanation. The system returns the three smallest witness sets
of source-backed claims that derive C87 , which can then be rendered as a provenance note or used to
inspect fragility. Evidence strength is B; the key citation is the 2024 SAT-based why-provenance work and the
2024 complexity result that warns against universal deployment. Feasibility is medium: it is justified only for
a narrow slice of claims, which is exactly where your load-bearing flag helps. 29

Normalized contradiction workbench targets factual, scientific, and temporally consistent writing.
Extend the schema with normalized helper entities or projector outputs such as claim-quantity ,
 claim-unit , claim-time-interval , and claim-normal-form . Add Datalog rules for exact
contradictions, interval inconsistencies, quantity clashes after unit conversion, and stale supersession
chains. Send only unresolved paraphrastic cases to an external NLI or domain verifier. Micro-example: one
claim says "latency is 5 ms," another says "latency is 0.02 s" for the same benchmark/context. The symbolic
checker converts and marks a hard contradiction. Another pair differs only by wording around "substantially
faster"; that pair goes to the residual NLI checker. Evidence strength is A/B split as above; the key citation is
the temporal claim-verification literature plus unit-aware verification. Feasibility is high because normalized
symbolic checks are deterministic and cheap. 30

Proof obligations as KG entities target mathematical rigor and scientific rigor. Add proof-
obligation with fields like id , statement , linked-claim , checker-kind , status ,
 assumptions , artifact-path , countermodel-path , checked-at , and normal-form . Checker
kinds should include at least z3 , cvc5 , lean , units , and stats-report . The writer's math/science
passes must consume only claims whose linked proof obligations are discharged or explicitly waived.
Micro-example: claim C105 states a monotonicity property; proof-obligation/PO7 formalizes it for
Z3 and returns unsat for the negation, so the writer may state it as verified. Another claim about
asymptotic equivalence fails discharge, so the writer must mark it conjectural or omit it. Evidence strength
is B; the key citation is Lean's kernel-based verification plus Z3 proof objects. Feasibility is medium-high
because you already have Z3 in the suite, and the seam stays offline and replayable. 31

Scientific-claim compliance checks target scientific soundness. Add a scientific-claim-check
seam that verifies units, presence of uncertainty qualifiers, evidence type, and statistical-reporting norms.
For domains that use reporting guidelines, store guideline-specific checks as machine-readable obligations
rather than free-form prose instructions. Micro-example: a sentence claims "treatment improved outcomes
significantly" without effect size, interval, or evidence type. The checker flags "statistical-claim-
underreported," and the writer is required to add either the quantitative evidence or a weaker wording.
Evidence strength is B; the key citation is recent guidance on statistical reporting and the EQUATOR /
PRISMA ecosystem. Feasibility is good because many checks are schema-driven and deterministic. 32

Deterministic codeclaim autolinking targets fact-based writing about software systems. Replace
today's wholly explicit code-claim-link with a derived relation whose evidence is stored. The first stage
should use deterministic signals only: a claim's source.file matches a module path, a mention resolves
to a symbol present in code-node , or a cited symbol has a call/import/reference edge to the relevant
community. Store the evidence in a link-evidence relation with fields like kind , score , witness ,
and provenance . A second-stage model may rank ambiguous candidates, but only deterministic or
thresholded reviewed links should become canonical. Micro-example: a claim extracted from src/cache/
policy.py mentions Evictor.rebalance ; the linker finds the symbol in code-node , confirms a

                                                                           7
 CONTAINS and USES trail in the code graph, and materializes code-claim-link with
 kind = exact-symbol . Evidence strength is B; the key citation is CODEXGRAPH. Feasibility is high for
stage one and moderate for stage two. 33

Substrate verdict

The decisive recommendation is: keep Cozo as the production backend for now, do not move the
primary store to Asami or DataScript, and spend the migration budget on seam-hardening plus a
reference evaluator instead of a full switch. Cozo still matches your actual workload unusually well:
embedded execution, Datalog queries, graph algorithms in-engine, time-travel support, and a Python-
friendly access path. Those are not generic database features; they are exactly the features your design is
already exploiting. 34

The counterweight is maintenance risk. The latest release I could verify is v0.7.6 , dated December 11,
2023. That does not mean Cozo is unusable, but it does mean migration risk is real enough to justify active
mitigation rather than "wait and hope." The right mitigation is not an immediate database rewrite. It is a
conformance harness behind cozo_store : frozen EDN query fixtures, dual-run result equality tests,
canonical ordering checks, and a small reference backend for rule semantics. That makes a future switch
cheap enough to contemplate without paying for it now. 35

A move to DataScript is attractive only for a narrow role: a pure-EDN reference evaluator or authoring-
time test backend. Its README is explicit that it is an immutable, in-memory database intended to run
inside the browser, and that it is ephemeral. That is excellent for determinism and developer ergonomics,
but not for your single durable production store. The fact that DataScript is still actively released is a plus,
just not enough to overturn the durability and Python-primary constraints. 36

A move to Asami is weaker still for production. The original repository explicitly states that it is no longer
being maintained and points users to another repository for ongoing development. The verifiable materials
I found still describe it as a Clojure/ClojureScript graph store, with an in-memory orientation and visible
changelog entries around 2022. That makes it interesting as a conceptual north star for homoiconicity, but
not the backend I would choose for this pipeline today. 37

No newer engine I could verify dominates Cozo under your constraints. Soufflé is active and strong for
Datalog compilation, but it is a program-analysis engine more than a transactional embedded graph store.
FlowLog and DBSP are exciting for incremental Datalog, but remain closer to research or specialist systems
than to a drop-in embedded Python backend with graph algorithms and offline swappability. Glean and
jQAssistant are instructive for code-graph modeling, but they require different language/runtime
commitments and do not solve your whole-KG problem. 38

The trigger to switch should therefore be explicit, not emotional: switch only if one of the following
becomes true: Python compatibility or platform support breaks materially; an unpatchable correctness or
security issue appears; the seam-hardening effort shows that a reference backend can reproduce your rule
surface with acceptable performance; or you decide to relax the "embedded, Python-primary, offline"
constraints enough to admit a JVM/server class of store. Until then, keep Cozo and buy optionality. 39

                                                                           8
Evaluation plan

The evaluation philosophy should match the repository discipline you already described: characterization
first, goldens second, and exact result-set equality wherever determinism allows. For retrieval and
generation, add a frozen benchmark set of chapter-writing tasks whose inputs are ledger snapshots and
whose outputs are not only text but also graph-structured side products: selected claims, cited spans,
contradiction alerts, and proof-obligation traces. This lets you measure improvements without relying only
on subjective prose judgments. 40

For attribution, measure sentence-level citation precision and recall against human-verified source spans,
plus partial-support rates. ALCE and CiteEval make good design references for evaluation dimensions, but
your internal gold standard should be stricter because your KG already stores exact spans. Also measure
unsupported-assertion rate after atomic decomposition, which is closer to FActScore than to document-level
citation coverage. 41

For factuality, decompose output chapters into atomic facts and compute: percentage backed by verified
claims; percentage backed by disputed claims; percentage with no claim binding; and percentage whose
cited spans pass the support checker. That yields an internal version of FActScore that is better aligned with
your ledger than generic wiki-backed factuality. Track both micro-average by sentence and macro-average
by chapter. 42

For reasoning quality, evaluate argument-acceptability coverage. Concretely: the precision and recall of
warnings like undefended-attack , unsupported-load-bearing , and axiom-only-support
against human judgments from a small annotated set. Also measure chapter-level "argument closure": the
percentage of thesis-support chains where every load-bearing claim is either grounded-accepted or
explicitly caveated in the prose. 27

For contradiction handling, maintain a curated fixture bank of logical, temporal, and numeric
inconsistencies. Measure exact contradiction-catch rate for symbolic rules, recall on paraphrastic
contradictions for the residual checker, and false-positive rate separately. This is important because NLI-
style contradiction detectors can be brittle out of context. 43

For mathematical and scientific rigor, measure proof-obligation discharge rate, failed-obligation
detection rate, and "gated sentence escape" rate: how often the final prose still contains a sentence that
should have been blocked by an open or failed proof obligation. For scientific claims, track unit-check pass
rate and statistical-claim completeness rate. 44

For cross-graph fusion, evaluate codeclaim linking in two passes: deterministic linker precision/recall
against a hand-labeled sample, then downstream writing outcomes such as lower invented-API rate and
fewer architecture mismatches in software descriptions. The right negative control is a writer that sees the
same natural-language sources but no code-graph links. 45

Prioritized roadmap

The first tranche should be quick wins with strong evidence. Build the writer-assertion contract,
sentence-to-span citation checks, and the chapter-retrieval bundle. These are mostly projector and prompt-

                                                                           9
interface changes, not substrate changes. They are the smallest path to measurable gains in attribution,
factuality, and global chapter coherence. Size: S/M. Evidence: A. Dependencies: none beyond the current
 claim / source-span model. 46

Next, implement symbolic contradiction normalization and grounded-acceptability warnings. These
are mostly EDNDatalog rule additions and will immediately improve the writer's warning surface. Add
temporal and quantity normalization before adding any heavier verifier. Size: M. Evidence: A/B.
Dependencies: writer-assertion contract, because contradiction warnings are most useful when attached to
explicit assertions. 47

Then implement belief erosion propagation and load-bearing provenance-on-demand. This is where the
ledger becomes genuinely useful to the prose pipeline instead of merely archival. Start with deterministic
propagation and bounded justification extraction only for flagged claims. Size: M/L. Evidence: B.
Dependencies: contradiction normalization and argument warnings. 48

In parallel, begin deterministic codeclaim autolinking. Restrict the first release to file-path and exact-
symbol evidence. Do not start with embeddings or GNNs. The goal is to get high precision and an auditable
 link-evidence trail. Size: M. Evidence: B. Dependencies: none beyond current code graph ingestion. 49

After that, add proof obligations for narrow but high-value claim classes: algebraic identities, numeric
bounds, unit-sensitive transformations, and mechanically checkable scientific statements. Keep Lean for the
small subset of claims that truly benefit from theorem proving; use Z3/cvc5 for the broader set of bounded
obligations. Size: L. Evidence: B. Dependencies: normalized contradiction workbench and claim typing. 50

Finally, do the seam-hardening and fallback-substrate program: dual-backend conformance tests, a
DataScript reference evaluator for selected rule subsets, and frozen semantic fixtures. This is foundational
but should follow the earlier product-facing wins, because it reduces infrastructure risk without directly
improving prose quality. Size: M/L. Evidence: B. Dependencies: stable fixtures from the earlier work. 51

The speculative tranche is small: learned codeclaim ranking, richer ASPIC+/preferred semantics in a
separate solver, and autoformalization loops for complex mathematical prose. These are worth exploring,
but only after the earlier deterministic layers are in place. Size: L. Evidence: C/B, depending on the item. 52

Open questions and risks

The main unsettled research question is how much graph structure itself, rather than simply better
retrieval and prompting, improves long-form writing quality in your setting. The broader GraphRAG
literature is no longer uniformly optimistic; recent evaluations show meaningful gains on some classes of
reasoning tasks and weaker results elsewhere. The right experiment is therefore not "GraphRAG vs RAG" in
the abstract, but claim-first graph bundles vs flat passage bundles on your own chapter-writing tasks.

  53

A second open question is how reliable sentence-to-span entailment is when the writer paraphrases
aggressively. Citation evaluation work shows that NLI-only judging is incomplete and that partial-support
judgments remain difficult. That pushes the design toward narrower, more local citation contracts and
explicit "partial support" states instead of binary passes. 54

                                                                           10
A third risk is provenance cost explosion. Recent work confirms that why-provenance for recursive Datalog
can be intractable in general, so the temptation to compute full explanation graphs for every claim should
be resisted. Your load-bearing flag gives you a natural throttle: explain the small set of claims that
matter most. 55

A fourth risk is over-investing in the wrong backend switch. Cozo has maintenance risk, but the visible
alternatives each violate at least one of your constraints: durability, Python primacy, embedded execution,
graph algorithms, or active maintenance. The best small experiment here is a semantic shadow backend
for a limited rule subset, not a production migration. 39

A fifth risk is premature autoformalization. The field has improved quickly, but even the strongest results
do not justify treating natural-language mathematical claims as formally checked unless a real formal
artifact exists and has passed the checker. The safe experiment is to start with bounded SMT obligations
and a small hand-curated Lean subset, then measure discharge rates and author value. 56

Annotated bibliography

GraphRAG and graph-grounded generation. Microsoft GraphRAG documentation and blog posts matter
here because they define the practical local/global/dynamic-search pattern your KG can reuse without
adopting Microsoft's entire stack. HiRAG matters because it shows that hierarchical retrieval can empirically
outperform flatter baselines for structure-sensitive tasks. The 2025­2026 evaluation papers matter because
they temper the hype and show where graph methods actually help. 57

Attributed generation and factuality. ALCE is the reproducible baseline for answers-with-citations;
FActScore is the right mental model for long-form atomic factuality; RARR is the clearest retrieve-and-revise
design; Self-RAG and CRAG provide retrieval control patterns; "Attribute First, then Generate," LongCite, and
CiteEval push the field toward local, sentence-level attribution and better citation quality judgments. 17

Formal argumentation. Dung remains the foundational abstraction for attack/defense acceptability.
ASPIC+ and ABA matter because your schema already has structured support chains and rebuttals that go
beyond plain abstract attacks. Quantitative bipolar argumentation is relevant because your KG has both
supporting and conflicting weighted signals. ASP encodings matter because they indicate which semantics
are feasible in plain Datalog and which want a stronger non-monotonic solver. 58

Belief revision, provenance, and uncertainty. Provenance semirings remain the most directly transferable
theory for your claim ledger. Recent Datalog provenance work matters because it explains both what is
possible and where complexity bites. ProbLog, PSL, and MLN matter as reference points for uncertainty, but
mostly as cautionary comparisons rather than as immediate deployment recommendations. 59

Contradiction and claim verification. Temporal claim-verification work matters because stale or time-
sensitive claims are a central KG risk. Unit-aware verification matters because scientific prose often fails
numerically rather than rhetorically. Recent citation-faithfulness work matters because support judgments
degrade when evaluation ignores broader context. 20

Mathematical and scientific verification. Lean and mathlib matter because they offer an offline,
auditable path for rigorous formal checking. Z3 and cvc5 matter because they are easier to integrate for

                                                                           11
bounded obligations and proof objects. Autoformalization surveys and competition-level results matter
because they show the research pace, but also imply that proof obligations should be tracked explicitly, not
assumed. Reporting-guideline resources matter for scientific-claim norms. 60

Substrate and Datalog systems. Cozo's documentation matters because it confirms the core fit:
embedded Datalog, graph algorithms, and time travel. DataScript matters as an EDN/Datalog reference
backend, not a durable primary store. Asami matters mostly as a warning that the conceptual north star is
not the same thing as an operationally verified production backend. Soufflé, DBSP, and FlowLog matter as
forward-looking references for compiled and incremental Datalog. 61

Code graphs, code indexing, and cross-graph fusion. Glean and Joern matter because they show how
code structure can be turned into queryable facts at scale. CODEXGRAPH matters because it directly
demonstrates repository-level gains from graph-based code retrieval. De-Hallucinator matters because it
provides concrete evidence that project-specific grounding reduces invented APIs. Embedding and GNN
link-prediction papers matter because they are the right second-stage ranking tools once deterministic
evidence has been exhausted. 23

 1 8 16 24 57 Welcome - GraphRAG

https://microsoft.github.io/graphrag/

 2 10 18 27 58 Artificial Intelligence

https://cse-robotics.engr.tamu.edu/dshell/cs631/papers/dung95acceptability.pdf?utm_source=chatgpt.com

 3 11 19 28 48 59 Provenance Semirings

https://web.cs.ucdavis.edu/~green/papers/pods07.pdf?utm_source=chatgpt.com

 4 13 21 31 60 The Lean Language Reference

https://lean-lang.org/doc/reference/latest/?utm_source=chatgpt.com

 5 12 20 30 43 47 An End-to-End Solution for Temporal Claim Verification

https://aclanthology.org/2024.emnlp-industry.48.pdf?utm_source=chatgpt.com

 6 14 23 GitHub - facebookincubator/Glean: System for collecting, deriving and working with facts about
source code. · GitHub

https://github.com/facebookincubator/Glean

 7 22 35 39 Releases · cozodb/cozo

https://github.com/cozodb/cozo/releases?utm_source=chatgpt.com

 9 15 17 40 41 aclanthology.org

https://aclanthology.org/2023.emnlp-main.398.pdf

25 46 Attribute First, then Generate: Locally-attributable Grounded Text Generation - ACL Anthology

https://aclanthology.org/2024.acl-long.182/

26 42 FActScore: Fine-grained Atomic Evaluation of Factual Precision in Long Form Text Generation - ACL
Anthology

https://aclanthology.org/2023.emnlp-main.741/

29 Computing the Why-Provenance for Datalog Queries via ...

https://ojs.aaai.org/index.php/AAAI/article/view/28914/29739?utm_source=chatgpt.com

                                                                           12
32 Improving statistical reporting in psychology

https://www.nature.com/articles/s44271-025-00356-w?utm_source=chatgpt.com

33 49 aclanthology.org

https://aclanthology.org/2025.naacl-long.7.pdf

34 61 The Cozo Database Manual 0.4

https://docs.cozodb.org/_/downloads/en/v0.4.0/pdf/

36 51 GitHub - tonsky/datascript: Immutable database and Datalog query engine for Clojure, ClojureScript
and JS · GitHub

https://github.com/tonsky/datascript

37 threatgrid/asami: A graph store for Clojure and ClojureScript

https://github.com/threatgrid/asami?utm_source=chatgpt.com

38 souffle-lang/souffle: Soufflé is a variant of Datalog for tool ...

https://github.com/souffle-lang/souffle?utm_source=chatgpt.com

44 50 Programming Z3

https://theory.stanford.edu/~nikolaj/programmingz3.html?utm_source=chatgpt.com

45 De-Hallucinator: Mitigating LLM Hallucinations in Code Generation Tasks via Iterative Grounding

https://arxiv.org/html/2401.01701v3

52 An Answer Set Programming Approach to Argumentative ...

https://proceedings.kr.org/2020/63/?utm_source=chatgpt.com

53 RAG vs. GraphRAG: A Systematic Evaluation and Key Insights

https://arxiv.org/pdf/2502.11371

54 Towards Fine-Grained Citation Evaluation in Generated Text: A Comparative Analysis of Faithfulness
Metrics

https://aclanthology.org/2024.inlg-main.35.pdf

55 The Complexity of Why-Provenance for Datalog Queries

https://dl.acm.org/doi/10.1145/3651146?utm_source=chatgpt.com

56 Autoformalization in the Era of Large Language Models

https://arxiv.org/html/2505.23486v1?utm_source=chatgpt.com

                                                                           13
