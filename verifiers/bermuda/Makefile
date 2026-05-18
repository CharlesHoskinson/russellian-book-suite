.PHONY: ci build smoke clean

ci: build smoke

build:
	npm install
	npm run build

smoke:
	pytest tests/ -v \
	  --deselect tests/test_axioms_lockstep.py::test_ci_yaml_has_bermuda_z3_jobs \
	  --deselect tests/test_axioms_lockstep.py::test_axioms_rs_committed_is_in_sync \
	  --deselect tests/test_d13_end_to_end.py::test_d13_fires_on_ch02_parish_count_drift

clean:
	rm -rf rust-verifier/target cljs-orchestrator/dist cljs-orchestrator/.shadow-cljs cljs-orchestrator/native
