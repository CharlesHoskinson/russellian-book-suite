# Book Thesis — Added Requirements

## ADDED Requirements

### Requirement: Thesis Tree Read API
The book-thesis skill SHALL expose
`read_thesis_tree(chapter_id: str, workspace_root: Path) -> ThesisTree`
with stable node IDs, and SHALL raise `ThesisNotDefined` for chapters with
no tree.

#### Scenario: Existing thesis tree is returned with stable node IDs
- GIVEN a chapter ID for which a thesis tree is defined in the workspace
- WHEN `read_thesis_tree` is called
- THEN a ThesisTree object is returned whose node IDs are identical across successive calls with the same inputs

#### Scenario: Missing thesis tree raises ThesisNotDefined
- GIVEN a chapter ID for which no thesis tree has been defined
- WHEN `read_thesis_tree` is called
- THEN `ThesisNotDefined` is raised
