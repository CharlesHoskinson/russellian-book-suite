# Book Knowledge — Added Requirements

## ADDED Requirements

### Requirement: PDF Ingest API
The book-knowledge skill SHALL expose
`ingest_pdf(source_path: Path, workspace_root: Path) -> IngestResult` where
`IngestResult` is a dataclass with fields: source_id, sha256,
claims_extracted, wiki_pages_touched, and status with values in
{ingested, already_present, failed}.

#### Scenario: Novel PDF is ingested and returns status ingested
- GIVEN a PDF file not previously seen by the workspace
- WHEN `ingest_pdf` is called
- THEN the returned IngestResult has status `ingested`, a non-empty sha256, and claims_extracted >= 0

#### Scenario: Duplicate PDF returns status already_present
- GIVEN a PDF whose sha256 matches an already-ingested source
- WHEN `ingest_pdf` is called
- THEN the returned IngestResult has status `already_present`

---

### Requirement: Claim Query API
The book-knowledge skill SHALL expose
`query_claims(filter_: ClaimFilter, workspace_root: Path) -> List[ClaimRecord]`
where `ClaimFilter` is a dataclass with optional fields: tags, topics,
source_ids, and state (a ClaimState enum value).

#### Scenario: Filter by tags returns matching claims
- GIVEN three claims tagged {finality} and two claims tagged {safety}
- WHEN `query_claims` is called with filter tags=["finality"]
- THEN exactly three ClaimRecord objects are returned

#### Scenario: Empty filter returns all claims
- GIVEN five claims in the workspace
- WHEN `query_claims` is called with an empty ClaimFilter
- THEN all five ClaimRecord objects are returned

---

### Requirement: Source Ingestion Check API
The book-knowledge skill SHALL expose
`is_source_ingested(sha256: str, workspace_root: Path) -> bool`.

#### Scenario: Returns true for known sha256
- GIVEN a sha256 corresponding to a previously ingested source
- WHEN `is_source_ingested` is called with that sha256
- THEN True is returned

#### Scenario: Returns false for unknown sha256
- GIVEN a sha256 not present in the ingested-source ledger
- WHEN `is_source_ingested` is called with that sha256
- THEN False is returned

---

### Requirement: Concept List API
The book-knowledge skill SHALL expose
`list_concepts(workspace_root: Path) -> List[ConceptRef]` where `ConceptRef`
is a dataclass with fields: slug, title, sources, and surface_forms.

#### Scenario: Concept list reflects workspace concept pages
- GIVEN a workspace containing three concept pages
- WHEN `list_concepts` is called
- THEN a list of three ConceptRef dataclasses is returned, each with a non-empty slug and title
