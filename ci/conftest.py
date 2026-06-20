"""Register the NFR-5 no-shadow-writes plugin for the ci/ test suite.

Without this, the autouse fixture in lint_no_shadow_writes.py is never collected
(the module is not a conftest and was not passed via -p), so the guard would be
dormant. Listing it in pytest_plugins makes the autouse fixture fire for every
test under ci/.
"""

pytest_plugins = ["ci.lint_no_shadow_writes"]
