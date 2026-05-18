.PHONY: ci build extract smoke clean

ci: build extract smoke

build:
	npm install
	npm run build

extract:
	@if [ -f fixtures/claims_clean.jsonl ] && [ -f rules/predicates.edn ]; then \
	  python scripts/extract_preview.py \
	    --claims fixtures/claims_clean.jsonl \
	    --predicates rules/predicates.edn; \
	else \
	  echo "[extract] missing fixtures/claims_clean.jsonl or rules/predicates.edn; skipping"; \
	fi

smoke:
	@if [ -d tests ]; then pytest tests/ -v; else echo "[smoke] no tests/ directory; skipping"; fi

clean:
	rm -rf rust-verifier/target cljs-orchestrator/dist cljs-orchestrator/.shadow-cljs cljs-orchestrator/native
