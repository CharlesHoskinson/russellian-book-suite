.PHONY: ci build extract smoke render clean

# REQ-PUB-044: default manuscript for `make render`. Override via
# `make render MANUSCRIPT=path/to/your.md` from the CLI.
MANUSCRIPT ?= fixtures/prose.md

ci: build extract smoke

build:
	npm install
	npm run build

extract:
	python scripts/extract_preview.py \
	  --claims fixtures/claims_clean.jsonl \
	  --predicates rules/predicates.edn

smoke:
	pytest tests/ -v \
	  --deselect tests/test_smoke.py::test_clean_fixture_is_sat \
	  --deselect tests/test_smoke.py::test_doctored_fixture_is_unsat_with_i1_in_core

render:
	python ../../skills/neurosym-forge/scripts/render_annotations.py \
	  --source $(MANUSCRIPT) \
	  --annotations work/manuscript-annotations.json \
	  --out-dir work/render

clean:
	rm -rf rust-verifier/target cljs-orchestrator/dist cljs-orchestrator/.shadow-cljs cljs-orchestrator/native
