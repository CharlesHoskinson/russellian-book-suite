# Skill ABI — Added Requirements

## ADDED Requirements

### Requirement: Public Surface Declaration in skill_api.py
Every russellian-book-suite skill callable from other skills SHALL expose its
public surface in `<skill-root>/skill_api.py` declaring `__all__: list[str]`
and `API_VERSION: tuple[int, int]`.

#### Scenario: skill_api.py present with required declarations
- GIVEN a russellian-book-suite skill that is callable from other skills
- WHEN `skill_api.py` is inspected
- THEN `__all__` and `API_VERSION` are defined at module level

---

### Requirement: Typed Signatures and Workspace-Root Argument
Every function in `skill_api.py` SHALL carry full type hints, SHALL accept
the workspace root as an explicit argument where state is required, and SHALL
return primitives, `pathlib.Path`, or `@dataclass`-decorated objects.
Untyped dicts as return types are prohibited.

#### Scenario: Untyped dict return type fails the static check
- GIVEN a `skill_api.py` function that declares `-> dict` as its return type
- WHEN the static type linter runs
- THEN the linter reports a violation

#### Scenario: Dataclass return type passes the static check
- GIVEN a `skill_api.py` function that returns a `@dataclass`-decorated object
- WHEN the static type linter runs
- THEN no violation is reported for the return type

---

### Requirement: Cross-Skill Calls via sibling_skills Loader
Cross-skill calls SHALL be routed through
`sibling_skills.load_skill_api(name: str) -> module`. Direct relative imports
across sibling skill roots are prohibited.

#### Scenario: Direct cross-skill import fails the import linter
- GIVEN a skill that uses a relative import path to reach a sibling skill's module
- WHEN the CI import linter runs
- THEN the linter reports a violation for the direct import

#### Scenario: sibling_skills loader succeeds for a valid skill name
- GIVEN a valid skill name registered in the suite
- WHEN `sibling_skills.load_skill_api(name)` is called
- THEN the module object for that skill's `skill_api.py` is returned

---

### Requirement: API Version Mismatch Raises Typed Error
`load_skill_api` SHALL raise `IncompatibleSkillApiVersion` carrying both
versions in the message when a caller's expected API_VERSION major value
differs from the callee's.

#### Scenario: Major version mismatch raises IncompatibleSkillApiVersion
- GIVEN a caller that expects major version 1 and a callee with major version 2
- WHEN `load_skill_api` is called
- THEN `IncompatibleSkillApiVersion` is raised and the message includes both version tuples

#### Scenario: Minor version difference does not raise
- GIVEN a caller that expects version (1, 0) and a callee at version (1, 3)
- WHEN `load_skill_api` is called
- THEN the module loads successfully without raising

---

### Requirement: sibling_skills as Shared Package
`sibling_skills` SHALL ship as a small shared package (not embedded in any
one skill) so that every consumer takes a stable dependency on the same
loader. Each suite skill SHALL declare it in its venv requirements.

#### Scenario: sibling_skills importable from every suite skill's venv
- GIVEN two separate suite skills installed in their own venvs
- WHEN `import sibling_skills` is executed in each venv
- THEN the import succeeds and the same package version is resolved in both
