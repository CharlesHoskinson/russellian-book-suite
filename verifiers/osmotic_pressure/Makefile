.PHONY: ci build extract index-semantic smoke clean

ci: build extract smoke

build:
	npm install
	npm run build

extract:
	python scripts/extract_preview.py \
	  --claims fixtures/claims_clean.jsonl \
	  --predicates rules/predicates.edn

index-semantic:
	@if [ -f work/claims.edn ]; then \
	  python scripts/build_semantic_index.py; \
	else \
	  echo "[index-semantic] no work/claims.edn; run make extract first"; \
	fi

smoke:
	pytest tests/ -v \
	  --deselect tests/test_smoke.py::test_clean_fixture_is_sat \
	  --deselect tests/test_smoke.py::test_doctored_fixture_is_unsat_with_i1_in_core

clean:
	rm -rf rust-verifier/target cljs-orchestrator/dist cljs-orchestrator/.shadow-cljs cljs-orchestrator/native
