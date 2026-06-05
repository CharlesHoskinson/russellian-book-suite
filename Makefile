# Top-level Makefile. Pure gates live in flake checks (`make lint` is an
# alias for the same `nix flake check` CI runs). preflight chains the
# sandbox-unsafe suites: cargo builds and npm ci cannot run inside the
# nix sandbox, so they stay Make verbs under `nix develop`.

.PHONY: preflight lint scaffold-bake regression nextest smoke-bermuda smoke-osmotic clean install-hooks readme-lint

preflight: scaffold-bake regression smoke-bermuda smoke-osmotic

# `nextest` is not part of preflight because there is no top-level cargo
# workspace; per-verifier cargo nextest can be added when a verifier ships
# Rust unit tests worth running outside its smoke chain.

lint:
	nix flake check -L

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
	@echo "Hooks are installed by the dev shell (nix develop)."
	@echo "lefthook.yml is generated from nix/hooks.nix — do not hand-edit."
	nix develop -c true

readme-lint:
	nix develop -c bash -c 'cd tools/readme-lint && .venv/bin/python -m scripts.lint_readme'
