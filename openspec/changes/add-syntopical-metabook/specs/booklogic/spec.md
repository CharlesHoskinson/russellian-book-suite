# Booklogic — Added Requirements

## ADDED Requirements

### Requirement: Single CLI Executable on PATH
The booklogic project SHALL ship a single CLI executable named `booklogic`
discoverable on the user's PATH after the project's documented install step.
The CLI SHALL be a ClojureScript application built with shadow-cljs target
`:node-script` and run on Node.

#### Scenario: booklogic is on PATH after install
- GIVEN the documented install step has been run
- WHEN `which booklogic` is executed
- THEN the path to the executable is returned and the command exits 0

---

### Requirement: Four Subcommands
The `booklogic` CLI SHALL expose exactly four subcommands:
`disputed-questions`, `reconcile-concepts`, `reachable-from-thesis`, and
`version`.

#### Scenario: All four subcommands are accessible
- GIVEN a working booklogic installation
- WHEN `booklogic --help` is run
- THEN the output lists disputed-questions, reconcile-concepts, reachable-from-thesis, and version

---

### Requirement: stdin/stdout Wire Format with EDN Canonical
Each non-`version` subcommand SHALL accept the global flag `--io {edn|json}`
(default `edn`), read input from stdin in the selected format, and write
output to stdout in the same format. EDN is the canonical form; JSON is the
deterministic projection defined in the JSON projection table below.
Booklogic SHALL use `cljs.tools.reader.edn` for EDN parsing and
`cljs.core/pr-str` for EDN printing.

#### Scenario: EDN input produces EDN output by default
- GIVEN an `:input/disputed-questions` atom serialized as EDN on stdin
- WHEN `booklogic disputed-questions` is invoked with no --io flag
- THEN the output on stdout is valid EDN

#### Scenario: JSON mode reads and writes JSON
- GIVEN an input atom serialized as JSON on stdin and `--io json` is passed
- WHEN `booklogic disputed-questions` is invoked
- THEN the output on stdout is valid JSON matching the projection table

---

### Requirement: Disputed Questions Detection
The booklogic CLI SHALL emit a list of zero or more `:disputed-question` atoms
when the `disputed-questions` subcommand receives an `:input/disputed-questions`
atom containing N verified claims, where each emitted atom corresponds to one
detected disputed question and carries at least two positions.

#### Scenario: Conflicting claims produce a disputed-question atom
- GIVEN two claims of conflicting form on topic `finality`
- WHEN `booklogic disputed-questions` is invoked
- THEN exactly one `:disputed-question` atom with two positions appears in the output

#### Scenario: Empty claims list produces empty output
- GIVEN an empty `:claims` list
- WHEN `booklogic disputed-questions` is invoked
- THEN the output is `[]` and exit code is 0

---

### Requirement: Concept Reconciliation Clustering
The booklogic CLI SHALL emit zero or more `:canonical-concept` atoms when the
`reconcile-concepts` subcommand receives an `:input/reconcile-concepts` atom
containing N concept atoms, one per detected cluster, each carrying exactly the
alternates that unify to the canonical slug under the active ruleset.

#### Scenario: Two unifying concepts produce one canonical-concept atom
- GIVEN two concept atoms whose surface forms unify under the active ruleset
- WHEN `booklogic reconcile-concepts` is invoked
- THEN one `:canonical-concept` atom with two alternates appears in the output

#### Scenario: Non-unifying concepts produce no canonical-concept atom
- GIVEN two concept atoms that do not unify under the active ruleset
- WHEN `booklogic reconcile-concepts` is invoked
- THEN no `:canonical-concept` atom is emitted (singletons are not emitted)

---

### Requirement: Thesis Reachability Verdict
The booklogic CLI SHALL emit exactly one `:verdict` atom whose `:candidate-id`
equals the input candidate ID when the `reachable-from-thesis` subcommand
receives an `:input/reachable-from-thesis` atom.

#### Scenario: Reachable candidate returns true verdict with rule-trace
- GIVEN a candidate whose extracted concepts rewrite to any thesis-node statement under the active ruleset
- WHEN `booklogic reachable-from-thesis` is invoked
- THEN `:reachable` is `true` and `:rule-trace` is non-empty

#### Scenario: Unreachable candidate returns false verdict with empty trace
- GIVEN a candidate with no rewrite path to any thesis node
- WHEN `booklogic reachable-from-thesis` is invoked
- THEN `:reachable` is `false`, `:rule-trace` is `[]`, and `:branch-witness` is `nil`

---

### Requirement: Provenance Keys on Every Output Atom
Every output atom from booklogic SHALL include the keys `:booklogic-version`,
`:ruleset-checksum`, and `:produced-at`. The checksum SHALL be the sha256 of
the concatenated `rules/*.edn` files in lexicographic filename order.

#### Scenario: Output atom carries all three provenance keys
- GIVEN a `disputed-questions` call that returns one result atom
- WHEN the atom is inspected
- THEN `:booklogic-version`, `:ruleset-checksum`, and `:produced-at` are all present and non-empty

---

### Requirement: Deterministic Output for Identical Inputs
The `booklogic` CLI SHALL produce byte-identical output EDN given identical
input EDN and identical `:ruleset-checksum`, achieved via ordered atomspace
traversal and canonical EDN printing.

#### Scenario: Two identical invocations produce byte-identical output
- GIVEN the same input EDN and the same ruleset checksum
- WHEN `booklogic` is invoked twice
- THEN the stdout bytes of both runs are identical

---

### Requirement: Schema Violation Error on Bad Input
If the input EDN fails schema validation, the booklogic CLI SHALL emit an
`:error` atom with `:code :schema-violation` to stderr and exit with code 1.

#### Scenario: Missing required field triggers schema-violation
- GIVEN an input atom missing the required `:predicate` field
- WHEN `booklogic disputed-questions` is invoked
- THEN an `:error` atom with `:code :schema-violation` is written to stderr and the exit code is 1

---

### Requirement: Rule Evaluation Failure Error
The booklogic CLI SHALL emit an `:error` atom with `:code :rule-failure` to
stderr and exit with code 2 if rule evaluation fails (for example due to an
unbound free variable in a rewrite witness).

#### Scenario: Unbound variable causes rule-failure exit
- GIVEN a ruleset containing a rule with an unbound free variable
- WHEN `booklogic reconcile-concepts` processes a concept triggering that rule
- THEN an `:error` atom with `:code :rule-failure` is written to stderr and the exit code is 2

---

### Requirement: Timeout Termination
When invoked with `--timeout-s <N>`, the booklogic CLI SHALL terminate within
N seconds and, on timeout, SHALL emit `:code :timeout` to stderr with exit
code 4.

#### Scenario: Long-running call is terminated at timeout
- GIVEN `--timeout-s 1` is passed and the evaluation exceeds one second
- WHEN `booklogic reachable-from-thesis` is invoked
- THEN the process terminates within 1 second, emits `:code :timeout` to stderr, and exits with code 4

---

### Requirement: Zero Network Calls
The booklogic CLI SHALL make zero network calls. All evaluation is local
against `rules/*.edn` and `assets/` in the configured ruleset directory.

#### Scenario: booklogic runs without network access
- GIVEN network access is blocked at the OS level
- WHEN `booklogic disputed-questions` is invoked
- THEN it completes without error using only local ruleset files

---

### Requirement: Version Subcommand
The booklogic CLI SHALL emit a `:version` atom to stdout and exit 0 when
invoked with the `version` subcommand and no stdin.

#### Scenario: version subcommand returns a version atom
- GIVEN no stdin
- WHEN `booklogic version` is invoked
- THEN a `:version` atom is written to stdout and the exit code is 0

---

### Requirement: Ruleset Directory Override via Env Var
Where `BOOKLOGIC_RULESET_DIR=<path>` is set, the booklogic CLI SHALL load
`rules/*.edn` from `<path>` instead of the default `./rules/`.

#### Scenario: Custom ruleset directory is used when env var is set
- GIVEN `BOOKLOGIC_RULESET_DIR=/tmp/custom-rules` is set and valid EDN rules exist there
- WHEN `booklogic disputed-questions` is invoked
- THEN the rules loaded are those from `/tmp/custom-rules/rules/*.edn`

---

### Requirement: JSON Projection Bijectivity
The booklogic CLI SHALL preserve EDN-to-JSON projection bijectivity for all
atom shapes defined in the projection table: round-tripping any well-formed
input through `json->edn->json` and `edn->json->edn` SHALL be the identity
function.

The projection table defines the deterministic mapping between EDN forms and
their JSON wire representations:

| EDN form | JSON wire form | Notes |
|---|---|---|
| keyword `:finality` | string `":finality"` | leading colon preserved so the projection is unambiguous on the way back |
| symbol `foo` | string `"foo"` | bare strings without a leading colon are symbols |
| nil | `null` | direct |
| boolean | boolean | direct |
| integer / float | number | direct |
| string `"abc"` | string `"\"abc\""` | strings round-trip with their own quote layer to disambiguate from symbols/keywords; e.g. EDN string `"foo"` becomes JSON string value `"\"foo\""` |
| map `{:a 1 :b 2}` | object `{":a": 1, ":b": 2}` | keyword keys carry the colon prefix |
| vector `[1 2 3]` | array `[1, 2, 3]` | direct |
| list `(asserts X)` | object `{"$list": ["asserts", "X"]}` | distinguish from vector |
| set `#{a b}` | object `{"$set": ["a", "b"]}` | distinguish from vector; member order canonicalized lex |
| tagged literal `#inst "..."` | object `{"$tag": "inst", "$value": "..."}` | covers `#inst`, `#uuid`, and any custom tag |
| s-expression body (a list of atoms) | nested arrays of the above | e.g. `(:asserts X (:∀ x (P x)))` → `{"$list":[":asserts", "X", {"$list":[":∀", "x", {"$list":["P", "x"]}]}]}` |

#### Scenario: EDN round-trip through json->edn->json is identity
- GIVEN a `:disputed-question` atom emitted in JSON mode
- WHEN the JSON is projected back to EDN and then to JSON again
- THEN the resulting JSON bytes are identical to the original JSON output

#### Scenario: JSON round-trip through edn->json->edn is identity
- GIVEN a `:disputed-question` atom emitted in EDN mode
- WHEN the EDN is piped through `--io json` and then back through `--io edn`
- THEN the byte sequence is identical to the original EDN output
