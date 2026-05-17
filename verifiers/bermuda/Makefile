.PHONY: ci build smoke clean

ci: build smoke

build:
	npm install
	npm run build

smoke:
	pytest tests/ -v

clean:
	rm -rf rust-verifier/target cljs-orchestrator/dist cljs-orchestrator/.shadow-cljs cljs-orchestrator/native
