# Section Headers

The rules in this file apply to section and subsection titles in technical papers, specifications, design docs, and book chapters. They do not apply to running prose.

## Why headers matter

A paper's table of contents is the paper in miniature. A reader who is deciding whether to read the paper, or which section to skim, sees only the headers and the first sentence of each section. Headers that name a meta-category ("The Problem", "Discussion", "Methodology") tell that reader nothing about the argument. Headers that name what is actually inside ("Single-Vendor PoET Is Broken", "What the Network Layer Doesn't Promise", "Fifteen Attacks, Their Defences and Residuals") convey the argument before the reader has read a single sentence.

The cost of meta-category headers is paid by every future reader. The cost of writing content-naming headers is paid once, by the author. The trade is asymmetric, and it favours the content-naming choice in every paper that expects more than one reader.

## Four use categories

Headers that pass should fall into one of these four categories.

### 1. Claim headers

A declarative statement of what the section establishes. The header itself is the conclusion the section earns.

Examples:
- Lamport, "Time, Clocks, and the Ordering of Events in a Distributed System": **"Anomalous Behavior"** — names the phenomenon the section claims exists and characterises.
- Ouroboros Praos: **"The static stake setting"** — names what is being formalised in that section, not a generic "model" heading.
- EpochPoET §1.3: **"TEEs Are Defence-in-Depth, Not Root"** — declarative, states the position the section defends.

### 2. Named-thing headers

A proper noun, a protocol concept, a specific mechanism, a numbered result, or a sub-component name. The header denotes a specific object that the section describes.

Examples:
- Castro and Liskov, "Practical Byzantine Fault Tolerance": **"View Changes"** — names the sub-protocol.
- Lamport, Shostak, and Pease, "The Byzantine Generals Problem": **"A Solution with Signed Messages"** — names the specific construction.
- EpochPoET §5.3: **"Conjecture 1, Axis by Axis"** — names the conjecture and the structural treatment of it.

### 3. Question-of-fact headers

Phrased so that the section answers "what is X" rather than "what about X". The header sets up a definite question; the section gives the definite answer.

Examples:
- **"What the Constraint Checker Catches"** — the section enumerates exactly what the artefact verifies.
- **"What We Assume About the Adversary"** — the section lists the assumptions.
- **"What Cannot Be Proved Here"** — the section enumerates the gaps.

These headers are declarative noun phrases beginning with "what" — they are not interrogative sentences ending in a question mark. The difference matters: "Why does the protocol use VRFs?" invites speculation; "What VRF Sortition Provides" delivers a description.

### 4. Sub-protocol or mechanism names

A specific name for the protocol layer, algorithm, or component being described. Often a noun phrase containing a technical term whose definition the section assumes the reader knows or supplies.

Examples:
- Castro and Liskov, "Practical Byzantine Fault Tolerance": **"Normal-Case Operation"** — names the protocol mode being described.
- EpochPoET §4.1: **"Multi-Domain TEE Attestation Layer"** — names the layer.
- EpochPoET §4.3: **"τ=1 Private VRF Sortition with Slot-Granular Forward Security"** — names the construction.

These are the workhorse headers of a specification. They pass without controversy when the named thing is real and specific.

## Three ban categories

Headers that fall into these categories should be replaced.

### 1. Meta-category headers

"The Problem", "The Opportunity", "Our Position", "Our Approach", "Background", "Motivation", "Context", "Discussion", "Future Work", "Conclusion".

These headers could appear unchanged in 100 different papers in the same field. They name the structural role of the section in the paper template, not the content of the section. A reader who reads only the headers cannot tell what this paper, specifically, is about.

Replacement strategy: name the specific problem, opportunity, position, or future-work item.

- "The Problem" becomes **"Single-Vendor PoET Is Broken"**.
- "The Opportunity" becomes **"Praos, drand, and Casper Are Now Available"**.
- "Our Position" becomes **"TEEs Are Defence-in-Depth, Not Root"**.
- "Future Work" becomes **"Post-Quantum Migration Plan"** or **"What This Paper Does Not Do"**.

Exception: "Contributions" and "Related Work" are tolerated by convention. The reader knows what to expect, and replacing them creates more friction than it removes. "Conclusion" is also tolerated when the section actually concludes; replace it when the section is doing something else (a survey, a forward-look, a retraction).

### 2. Apologetic headers

"Threat model recap", "Conjectured safety argument", "Informal liveness argument", "Proof gaps", "Caveats and Open Problems", "Limitations of This Paper".

These read as apologies. They tell the reader what the section is not (not a proof, not a complete argument, not a full treatment) before telling them what it is. The reader who reads only headers comes away thinking the paper is a string of incomplete artefacts.

Replacement strategy: state what is there, not what is missing.

- "Threat model recap" becomes **"What We Assume About the Adversary"**.
- "Conjectured safety argument" becomes **"Why We Believe Safety Holds"**.
- "Informal liveness argument" becomes **"Why We Believe Liveness Holds"**.
- "Proof gaps" becomes **"What Cannot Be Proved Here"**.
- "Caveats and Open Problems" becomes **"What Could Still Go Wrong"**.
- "Limitations of This Paper" becomes **"What This Paper Does Not Do"**.

The replacements are still honest about what the section is; they just lead with content rather than disclaimer. The disclaimer belongs in the first sentence, not the title.

### 3. Generic structure headers

"Methodology", "Analysis", "Experimental Setup", "Results", "Approach", "Design".

These name the structural element in a paper template. They do not name the specific method, analysis, setup, or result being described.

Replacement strategy: name the specific thing.

- "Methodology" becomes **"VRF Sortition Draws One Leader per Slot"** or **"Single-Threaded Lean Mechanisation"**.
- "Analysis" becomes **"Per-Epoch Tail Bound"** or **"Fifteen Attacks, Their Defences and Residuals"**.
- "Experimental Setup" becomes **"Six-Node Testbed on AWS Nitro"**.

## Decision rules

1. If your header could appear unchanged in 100 different papers in your field, it is a meta-category. Replace it.
2. If your header reads as an apology for what is missing, replace it with a statement of what is there.
3. If your header is a noun phrase that names a specific cryptographic primitive, protocol layer, theorem, result, or mechanism, it passes.
4. If your header is a declarative sentence (not a question), it usually passes. Sentences are stronger than noun phrases when the section establishes a claim; noun phrases are stronger when the section describes a named object.
5. If your header begins with "what" or "why" followed by a noun phrase (not a question mark), it passes. These are content-naming question-of-fact headers, not interrogatives.
6. "Contributions", "Related Work", and "Conclusion" are tolerated by convention when the section content matches the conventional expectation.

## The practical test

Print the table of contents. Read only the headers, in sequence, without reading any section body. Do they convey the argument?

If the answer is yes — if a reader who reads only the headers can reconstruct the paper's spine — the headers are doing real work. If the answer is no — if the reader needs to open each section to find out what is actually in it — the headers are decoration and should be rewritten.

The test is sharper than the per-header rules. A paper can pass every per-header rule and still fail the practical test if the headers, in sequence, do not tell a story. A paper can fail one or two per-header rules and still pass the practical test if the overall sequence is content-bearing.

Run the practical test after every substantive revision. The cost is a five-minute read; the return is a TOC that does the paper's preview work.

## EpochPoET v0.4 case study

The following replacements were applied to the EpochPoET paper in May 2026. The full design is in `paper/docs/superpowers/specs/2026-05-20-section-headers-rewrite.md`.

| Before | After | Why |
|---|---|---|
| §1.1 "The Problem" | "Single-Vendor PoET Is Broken" | Names the specific problem. |
| §1.2 "The Opportunity" | "Praos, drand, and Casper Are Now Available" | Names the specific primitives. |
| §1.3 "Our Position" | "TEEs Are Defence-in-Depth, Not Root" | States the position as a claim. |
| §1.5 "Paper Structure" | "Map" | One-word named-thing; shorter than the meta-category. |
| §4.5 "Network-Layer Threat Scoping" | "What the Network Layer Doesn't Promise" | Question-of-fact; names what the section enumerates. |
| §5.1 "Threat model recap" | "What We Assume About the Adversary" | Question-of-fact; drops the "recap" apology. |
| §5.2 "Adversary class declaration (F-73)" | "Classical, Q1, and Q2" | Named-things; names the three classes. |
| §5.3 "Conjecture 1: derivation sketch and proof obligations" | "Conjecture 1, Axis by Axis" | Named-thing plus structural hint; drops the apology. |
| §5.4 "Attack table" | "Fifteen Attacks, Their Defences and Residuals" | Names the contents and the count. |
| §5.5 "Conjectured safety argument" | "Why We Believe Safety Holds" | Question-of-fact; drops "conjectured". |
| §5.6 "Informal liveness argument" | "Why We Believe Liveness Holds" | Question-of-fact; drops "informal". |
| §5.7 "Proof gaps" | "What Cannot Be Proved Here" | Question-of-fact; states what is there. |
| §5.8 "Residual attacks under Mode A" | "Mode A's Forgery Window" | Named-thing; names the specific residual. |
| §5.9 "Economic-layer proof gap (R4 retraction)" | "The Economic Layer Is Not a Theorem" | Declarative claim; states the position. |
| §5.10 "Claim-ledger sanity checks" | "What the Constraint Checker Catches" | Question-of-fact; names what the artefact verifies. |
| §7.1 "Caveats and Open Problems" | "What Could Still Go Wrong" | Question-of-fact; drops the apology. |
| §7.4 "Limitations of This Paper" | "What This Paper Does Not Do" | Question-of-fact; drops "limitations". |

Headers not changed: §1.4 "Contributions" (conventional, tolerated); §4.1 "Multi-Domain TEE Attestation Layer", §4.2 "σ_BLS Randomness Beacon", §4.3 "τ=1 Private VRF Sortition", §4.4 "Block Production, Fork Choice, and Accountable Finality", §4.7 "Economic Layer Parameters", §7.2 "Post-Quantum Migration Plan", §7.3 "Governance and Decentralisation Trade-offs" — all already named-things; all appendix subsections already named-things.

The before/after table is the empirical record of the rule in use. Read it once before drafting a new section, and once again before the final pass.
