# Logical Atomism for Technical Writers

Russell's logical atomism holds that the world consists of simple, independent facts that combine into complex propositions. Applied to writing, this means: every complex technical statement must decouple into atomic propositions before being layered into a model.

## The IF / AND IF / THEN refactor pattern

When a sentence contains nested conditionals, refactor it into a stacked decision structure.

### Before

> If the user authentication token is successfully validated by the primary security server, and provided that the rate-limiting threshold has not been exceeded in the last minute, the system will execute the query and return the JSON payload, unless the database is locked.

### After

```
1. IF: The primary security server validates the user authentication token.
2. AND IF: The user has not exceeded the rate-limiting threshold within the preceding 60 seconds.
3. AND IF: The target database is currently unlocked.
4. THEN: The system executes the requested query and returns the JSON payload.
```

The reader is no longer forced to hold three variables in working memory while parsing the conclusion.

## When to atomize

Atomize a sentence when any of the following holds:

- Word count exceeds 30.
- The sentence contains more than one conditional ("if," "when," "unless," "provided that").
- A modifier separates a subject from its verb by more than five words.
- The sentence depends on the reader holding a variable in memory while a second clause unfolds.

## When not to atomize

Do not atomize when the propositions are genuinely a single movement and forced separation introduces awkward repetition. The test: can each fragment stand alone as a true statement? If a fragment is meaningless without the next, it is not atomic.

## Decoupling a complex architecture

Complex software architectures are explained by atomizing components, not by describing them holistically.

### Before

> Our microservices platform implements a sophisticated event-driven architecture where the orchestration layer coordinates between the message bus and the persistence tier while maintaining strict consistency guarantees through distributed transactions.

### After

```
1. The platform consists of three layers: an orchestrator, a message bus, and a persistence tier.
2. The orchestrator routes events between the bus and the tier.
3. The persistence tier participates in distributed transactions.
4. Distributed transactions enforce strict consistency.
```

Each line is independently verifiable. The reader builds the model one fact at a time.
