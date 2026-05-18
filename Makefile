# Top-level Makefile. The CI workflow and `make preflight` execute the same
# step list. Every shell line is the unit of comparison against
# scripts/ci-steps.txt — keep them aligned (the flake-drift check enforces).

.PHONY: preflight lint scaffold-bake regression nextest smoke-bermuda smoke-osmotic clean

preflight: lint scaffold-bake regression nextest smoke-bermuda smoke-osmotic

lint:
	clj-kondo --lint $$(git ls-files '*.clj' '*.cljs' '*.cljc' '*.edn') --fail-level error
	cargo fmt --check --manifest-path verifiers/bermuda/rust-verifier/Cargo.toml
	cargo fmt --check --manifest-path verifiers/osmotic_pressure/rust-verifier/Cargo.toml
	nixpkgs-fmt --check $$(git ls-files '*.nix')
# Python lint deliberately omitted from `make lint`. The repo has ~210 pre-
# existing ruff violations across legacy code; bringing them clean is a
# multi-PR effort tracked separately. Per-skill tests still enforce ruff
# where each skill's pyproject.toml declares it as a [dev]/[ci] dependency.

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
