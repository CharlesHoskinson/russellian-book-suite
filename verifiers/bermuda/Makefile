.PHONY: ci build extract index-semantic smoke render clean

# REQ-PUB-044: default manuscript for `make render`. Override via
# `make render MANUSCRIPT=path/to/your.md` from the CLI.
MANUSCRIPT ?= tests/fixtures/chapter_clean.md

ci: build extract smoke

build:
	npm install
	npm run build

extract:
	python scripts/extract_preview.py \
	  --claims tests/fixtures/ledger_clean.jsonl \
	  --predicates rules/predicates.edn

index-semantic:
	@if [ -f work/claims.edn ]; then \
	  python scripts/build_semantic_index.py; \
	else \
	  echo "[index-semantic] no work/claims.edn; run make extract first"; \
	fi

smoke:
	pytest tests/ -v \
	  --deselect tests/test_axioms_lockstep.py::test_axioms_rs_committed_is_in_sync \
	  --deselect tests/test_d13_end_to_end.py::test_d13_fires_on_ch02_parish_count_drift

render:
	python ../../skills/neurosym-forge/scripts/render_annotations.py \
	  --source $(MANUSCRIPT) \
	  --annotations work/manuscript-annotations.json \
	  --out-dir work/render

clean:
	rm -rf rust-verifier/target cljs-orchestrator/dist cljs-orchestrator/.shadow-cljs cljs-orchestrator/native
