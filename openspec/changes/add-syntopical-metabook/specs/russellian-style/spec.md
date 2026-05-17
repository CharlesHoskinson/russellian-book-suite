# Russellian Style — Added Requirements

## ADDED Requirements

### Requirement: Fragment Lint API
The russellian-style skill SHALL expose
`lint_fragment(text: str, linters: Optional[List[str]] = None) -> List[LintIssue]`
returning issues with line and column coordinates relative to the input.

#### Scenario: Lint issues include line and column
- GIVEN a text fragment containing a style violation
- WHEN `lint_fragment` is called
- THEN a LintIssue with non-null line and column coordinates is returned for the violation

#### Scenario: Clean fragment returns empty issue list
- GIVEN a text fragment with no style violations
- WHEN `lint_fragment` is called
- THEN an empty list is returned

#### Scenario: Specific linters subset limits checks
- GIVEN a text fragment and a `linters` argument naming one specific linter
- WHEN `lint_fragment` is called
- THEN only issues from the named linter are returned
