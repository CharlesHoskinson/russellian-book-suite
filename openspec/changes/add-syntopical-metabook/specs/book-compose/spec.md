# Book Compose — Added Requirements

## ADDED Requirements

### Requirement: Lens File Consumption Contract
The book-compose skill SHALL read lenses by exact path
`syntopical/lenses/<chapter_id>.md` and SHALL treat the YAML frontmatter and
the section ordering defined by the lens contract (`Topics`, `Disputed Questions`,
`Concept Reconciliation`, `Coverage`) as a stable interface.

#### Scenario: Lens is read from the canonical path
- GIVEN a lens file for chapter `ch-03` written by syntopical-metabook
- WHEN book-compose needs the lens for `ch-03`
- THEN it reads `syntopical/lenses/ch-03.md` and parses the YAML frontmatter

#### Scenario: Unexpected section order is treated as a contract violation
- GIVEN a lens file whose sections appear in an order other than Topics, Disputed Questions, Concept Reconciliation, Coverage
- WHEN book-compose attempts to parse the lens
- THEN a contract-violation error is raised indicating the unexpected section order
