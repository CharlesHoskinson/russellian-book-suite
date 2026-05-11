# Ontology philosophy

The schema in `assets/shapes.ttl` and `assets/graph-context.jsonld` is small on purpose. This page explains the reasoning so future extensions stay coherent.

## BFO upper-category split

Basic Formal Ontology distinguishes **continuants** from **occurrents**:

- **Continuants** persist through time and have all their parts at every moment they exist. Documents, claims, source spans, wiki pages, entities, and chapters are continuants. They have identity over time even as their attributes change.
- **Occurrents** unfold over time. They have temporal parts. Ingest events, validation runs, releases, and verification activities are occurrents. They happen and are over.

Mapping in this skill:

- `tbf:Document`, `tbf:Claim`, `tbf:SourceSpan`, `tbf:WikiPage`, `tbf:ChapterSection` are continuants.
- `tbf:IngestActivity`, `tbf:ValidationRun`, `tbf:ReleaseGateRun` are occurrents (and `prov:Activity` instances).

The split matters because continuants and occurrents take different relations. A claim has a `dcterms:created` (continuant property), but a validation run has a `prov:startedAtTime` and `prov:endedAtTime` (occurrent property). Mixing the two produces incoherent graphs.

## SKOS for editorial taxonomies

Editorial categories — `domain`, `audience`, `evidence-type`, `maturity-level`, `topic-tag` — are SKOS concept schemes, not OWL classes. Use `skos:broader`, `skos:narrower`, and `skos:related`. Do NOT use `rdfs:subClassOf`.

The reason is category-theoretic. OWL subclass implies that every instance of the subclass IS-A instance of the superclass in a strict ontological sense, with all the inheritance and inference baggage that follows. A book labeled `audience: practitioner` is not a kind of book; it is a book to which an editorial category has been attached. Forcing the relation into `rdfs:subClassOf` introduces brittleness:

- Inferred classification grows the ABox unboundedly.
- The hierarchy has to be re-justified every time the editorial team changes its mind.
- Borderline cases (a book that is for both practitioners and researchers) require multiple inheritance, which OWL handles awkwardly.

SKOS handles all of this gracefully. Concepts can have multiple broaders, the hierarchy is editable without breaking inference, and the system treats categories as concepts (where they belong) rather than as types.

## OWL RL, not OWL DL

OWL 2 RL is the rule-based profile. It supports forward-chaining over a small set of inference rules and runs in polynomial time. The skill uses OWL RL for two things:

- Propagating `prov:wasDerivedFrom` transitively when a claim is derived from a derived claim.
- Inferring class membership for entities that are subclasses of `prov:Entity`.

Do not reach for OWL DL. The full description-logic profile pulls in tableau reasoning, undecidability for some constructs, and tooling that does not match the skill's local-only constraint. The graph is a small dataset; OWL RL forward chaining over it terminates fast and produces stable results.

## OntoClean review

When extending the schema, run an OntoClean-style review on every new class. Three properties to check:

### Rigidity

A property is **rigid** if it travels with an entity through every change. `tbf:Claim` is rigid: once a record is a claim, it is always a claim. `tbf:Editor` is **anti-rigid**: a person who edits a chapter is an Editor only while the role holds. Anti-rigid concepts model roles, not identity, and should not be classes that own identity criteria. Model them as concept-scheme tags or as relational properties (`tbf:editedBy`).

### Identity

A class **carries an identity criterion** if you can answer "what makes two instances the same?" `tbf:Document` carries identity via sha256. `tbf:Claim` carries identity via claim_id. `tbf:Editor` carries no identity of its own — it inherits identity from `tbf:Person`. Classes that fail the identity test are not sortals and should not be at the root of a subclass hierarchy.

### Unity

A class has a **unity criterion** if you can say what holds an instance together as a single thing. A document is unified by its file. A chapter is unified by its contract. A "list of all citations in the project" is not a single thing; it is a query result, not a class.

These three diagnostics catch most schema drift before it lands. Use them as a checklist, not as theology.

## When to extend the schema

Default to SKOS first. If a new distinction can be expressed as a concept-scheme tag with `skos:broader`, that is the right answer. Reserve OWL extensions for cases where:

- The new entity carries its own identity criterion (passes the OntoClean identity test).
- The new entity is rigid.
- Existing concept-scheme tags genuinely cannot represent the relation.

If you have to extend, add the new term to `assets/graph-context.jsonld` and corresponding shape rules to `assets/shapes.ttl`. Document the addition in `wiki/log.md` with the OntoClean justification.

## `audit_taxonomy.py` — what it catches

The audit script implements one heuristic: it reports any `rdfs:subClassOf` edge whose superclass carries an identity criterion and whose subclass carries no separate identity criterion (i.e., looks role-shaped). Concrete trigger:

```turtle
tbf:Editor rdfs:subClassOf tbf:Person .   # role under identity-bearing class
```

Editors are roles played by Persons. They should be modeled either as a SKOS concept-scheme tag (`tbf:editorRole`) or as a relation (`tbf:editedBy`). The audit flags the bad subclass; remediation is to re-model.

The heuristic is intentionally narrow. It will miss subtler errors (anti-rigid types one level below the root, identity-criterion conflicts) but it catches the most common drift, which is "everything is a class because RDF makes it cheap." When the audit returns clean and your graph still feels wrong, run a manual OntoClean pass.

## Anti-patterns

- **Modeling roles as subclasses.** Roles are anti-rigid. Use SKOS or relations.
- **Reaching for OWL DL.** Stay in RL. If you need DL reasoning, reconsider whether the question really requires it.
- **Subclassing under SKOS concepts.** SKOS concepts and OWL classes are different beasts. Mixing produces incoherent typing.
- **Inventing top-level classes for every new tag.** Tags are concepts. Use `skos:Concept` and a concept scheme; do not crowd the class hierarchy.
