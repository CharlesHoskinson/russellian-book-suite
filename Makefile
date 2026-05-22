# Top-level Makefile. The CI workflow and `make preflight` execute the same
# step list. Every shell line is the unit of comparison against
# scripts/ci-steps.txt — keep them aligned (the flake-drift check enforces).

.PHONY: preflight lint scaffold-bake regression nextest smoke-bermuda smoke-osmotic clean install-hooks readme-lint

preflight: lint scaffold-bake regression smoke-bermuda smoke-osmotic

# `nextest` is not part of preflight because there is no top-level cargo
# workspace; per-verifier cargo nextest can be added when a verifier ships
# Rust unit tests worth running outside its smoke chain.

lint:
	clj-kondo --lint $$(git ls-files '*.clj' '*.cljs' '*.cljc' '*.edn') --fail-level error
	ruff check .
	cargo fmt --check --manifest-path verifiers/bermuda/rust-verifier/Cargo.toml
	cargo fmt --check --manifest-path verifiers/osmotic_pressure/rust-verifier/Cargo.toml
	nixpkgs-fmt --check $$(git ls-files '*.nix')
	pytest skills/neurosym-forge/tests/test_support_matrix.py -q
	pytest skills/neurosym-forge/tests/test_induction_grammar_drift.py -q

scaffold-bake:
	pytest skills/neurosym-forge/tests/test_scaffold_bake.py -x

regression:
	pytest skills/neurosym-forge/tests/regression/ -x

nextest:
	cargo nextest run --workspace --no-fail-fast

smoke-bermuda:
	make -C verifiers/bermuda ci

smoke-osmotic:
	make -C verifiers/osmotic_pressure ci

clean:
	cargo clean
	rm -rf verifiers/*/rust-verifier/target
	rm -rf verifiers/*/cljs-orchestrator/dist
	rm -rf verifiers/*/cljs-orchestrator/.shadow-cljs
	rm -rf verifiers/*/cljs-orchestrator/native

install-hooks:
	@command -v lefthook >/dev/null 2>&1 || { \
		echo "ERROR: lefthook not found. Install it first:"; \
		echo "  nix develop  # (recommended — lefthook is in flake.nix)"; \
		echo "  OR: go install github.com/evilmartians/lefthook@latest"; \
		exit 1; \
	}
	lefthook install
	@echo "Pre-commit hooks installed. They will run on every git commit."

readme-lint:
	nix develop -c bash -c 'cd tools/readme-lint && .venv/bin/python -m scripts.lint_readme'
