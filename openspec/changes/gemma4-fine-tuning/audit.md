# Gemma 4 Fine-Tuning Plan Audit - 2026-05-24

Review target: `review_context.md`
Related files checked: `proposal.md`, `design.md`, `tasks.md`, `llm-infra/src/llm_infra/adapter.py`, `llm-infra/src/llm_infra/persona_dispatch.py`, `llm-infra/src/llm_infra/cache.py`, `llm-infra/src/llm_infra/health.py`, `skills/russellian-style/skill_api.py`.
Panel: Deep Learning & Fine-Tuning Engineer, Style Alignment & Tone Expert, Systems & MLOps Architect, QA & Compliance Gatekeeper.

## Approval Status

**Reject.**

The proposal has several high-risk design errors that should be corrected before implementation begins. The two hard blockers are the adapter/base mismatch (`google/gemma-2-27b-it` fine-tune deployed over `gemma4:31b`) and the training/evaluation plan's reliance on exposed synthetic `<think>` traces. The plan also under-specifies 32GB VRAM fit, DPO construction, source provenance, and compliance gates.

## Critical Findings

### 1. Adapter/base mismatch makes the Ollama deployment invalid

**Severity:** critical  
**Raised by:** Agent 1, Agent 3  
**Evidence:** `review_context.md:45`, `review_context.md:49`, `review_context.md:68`, `review_context.md:81`; `design.md:21`, `design.md:27`, `design.md:49`, `design.md:62`

The plan fine-tunes `google/gemma-2-27b-it` but loads the resulting adapter over `gemma4:31b` in the Ollama Modelfile. A LoRA adapter must match the base model architecture, layer names, tokenizer assumptions, and tensor dimensions used during training. Deploying a Gemma 2 27B adapter over a Gemma 4 31B base is not a safe compatibility shortcut; it is expected to fail or behave unpredictably.

**Required correction:** Choose one base and keep it identical through train, adapter export, Modelfile `FROM`, cache keys, and verification. Either train on the exact base represented by the local Ollama model and pin it by digest, or import/deploy the exact Gemma 2 27B base used for training and create the Ollama model from that base.

### 2. The named model and adapter path are inconsistent

**Severity:** critical  
**Raised by:** Coordinator synthesis, Agent 3  
**Evidence:** `review_context.md:10`, `review_context.md:18`, `review_context.md:78`, `review_context.md:82`, `review_context.md:115`; `design.md:59`, `design.md:63`

The plan now names the target model `russellgpt`, but the Modelfile still points at `./models/gemma4-book-adapter`. This creates a deployment ambiguity: training output, Modelfile path, model tag, docs, and `adapter.py` routing may refer to different artifacts.

**Required correction:** Standardize on one model name and one artifact directory. For example: `models/russellgpt-adapter/`, `ollama create russellgpt -f Modelfile`, and `DEFAULT_MODEL = "russellgpt"`. Add a smoke test that verifies the created model tag reports the expected adapter SHA and base digest.

### 3. The 32GB VRAM fit is asserted, not engineered

**Severity:** critical  
**Raised by:** Agent 1, Agent 3  
**Evidence:** `review_context.md:45`, `review_context.md:69-75`, `review_context.md:103-109`; `design.md:21`, `design.md:50-56`

A 27B QLoRA SFT plus DPO plan with rank 64 LoRA across attention and MLP projections, 4096-token examples, DPO/reference-model computation, gradient checkpointing, optimizer state, and Windows overhead is likely to OOM or become unstable on a 32GB RTX 5090 unless the memory budget is explicitly controlled. The plan does not specify per-device batch size, gradient accumulation, optimizer, activation strategy, reference-model handling, or fallback ranks.

**Required correction:** Make memory configuration explicit before implementation:

- `per_device_train_batch_size=1`
- explicit `gradient_accumulation_steps` and target effective batch size
- NF4 4-bit quantization with double quantization
- bf16 compute if supported by the pinned stack
- paged AdamW 8-bit or equivalent memory-aware optimizer
- gradient checkpointing with `use_cache=False`
- DPO reference handling via PEFT adapter-disable/reference sharing or precomputed reference logprobs
- fallback matrix for `r=16`, `r=32`, reduced target modules, and shorter DPO sequences
- a first task that runs a 100-step memory profile and fails on CPU fallback or OOM

### 4. Gutenberg source IDs include wrong books

**Severity:** critical  
**Raised by:** Agent 2  
**Evidence:** `review_context.md:59`, `review_context.md:62`; `design.md:40`, `design.md:43`

The proposal lists Project Gutenberg IDs that do not correspond to the named Russell works. Agent 2 found that `17020` is not *Mysticism and Logic and Other Essays*, and `37060` is not *Introduction to Mathematical Philosophy*; the latter should be checked against PG `41654`. Training on the wrong public-domain corpus would silently poison the style warmup.

**Required correction:** Replace the free-form source list with a checked allow-list containing title, author, eBook number, source URL, retrieved date, public-domain evidence, stripped-byte hash, and cleaned-text hash. The curation script must fail if the downloaded title/author/eBook metadata does not match the allow-list.

### 5. Synthetic `<think>` traces should not be training targets

**Severity:** critical  
**Raised by:** Agent 2, Agent 4  
**Evidence:** `review_context.md:15`, `review_context.md:38`, `review_context.md:51`, `review_context.md:96`; `design.md:10`, `design.md:30`

The plan proposes generating gold-standard `<think>...</think>` traces for historical outputs and then verifying that model output starts with `<think>`. These are post-hoc rationales, not observed reasoning. Training on them rewards plausible hidden-process narration, increases leakage risk, and conflicts with the existing artifact contract that expects YAML frontmatter at the start of review reports.

**Required correction:** Do not include exposed `<think>` blocks in final training targets. Use final answers plus short auditable rationale summaries, rubric labels, or verifier-visible metadata. If an internal reasoning block remains necessary, define a strict grammar and strip it before artifact validation and persistence.

### 6. Verification gates do not cover promised compliance surfaces

**Severity:** critical  
**Raised by:** Agent 4  
**Evidence:** `review_context.md:10`, `review_context.md:19`, `review_context.md:51`, `review_context.md:118-120`; `proposal.md:4`, `proposal.md:13`; `tasks.md:28-30`

The proposal promises YAML frontmatter and JSON-LD ledger compliance, but verification only names a mock chapter review, think parsing, YAML, and latency. It omits strict JSON-LD/JSONL ledger validation, malformed-output negative fixtures, train/eval leakage checks, split manifests, and parser compatibility with existing book-review/report tooling.

**Required correction:** Expand `verify_finetune.py` into a real compliance gate with failing fixtures:

- malformed, missing, duplicate, nested, and misplaced `<think>` blocks
- valid YAML frontmatter at the position expected by existing parsers, or an explicit pre-strip step before validation
- review report schema validation
- JSONL parsing for ledger rows with no skipped malformed lines
- JSON-LD context/schema checks for ledger outputs
- train/validation/test/acceptance split manifest validation
- exact and near-duplicate leakage checks across prompts, outputs, rationale summaries, and fixtures
- cache disabled or keyed by adapter SHA during verification

## Important Findings

### 7. LoRA target-module patterns are probably wrong

**Severity:** important  
**Raised by:** Agent 1  
**Evidence:** `review_context.md:73-75`; `design.md:54-55`

The target module list uses glob-like strings such as `*.language_model.*.q_proj`. PEFT target matching is typically based on actual module names or suffixes, and Gemma 2 causal LM layers are not expected to live under `language_model` in that form. This can produce zero trainable parameters or miss intended modules.

**Correction:** Use suffix targets such as `q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj`, or `target_modules="all-linear"` with explicit exclusions. Add an assertion that trainable parameter count is nonzero and within the expected percentage before training starts.

### 8. Context length is inconsistent between training and deployment

**Severity:** important  
**Raised by:** Agent 1  
**Evidence:** `review_context.md:64`, `review_context.md:75`, `review_context.md:83`; `design.md:46`, `design.md:56`, `design.md:64`

Training is capped at 4096 tokens while the Modelfile deploys `num_ctx 8192`. The adapter is therefore not trained or validated for the 4k-8k operating range that deployment exposes.

**Correction:** Either train and evaluate representative 8192-token examples, or deploy with `num_ctx 4096` and treat 8192 as a later, separately validated expansion.

### 9. DPO ranking is driven by style score instead of correctness-first gates

**Severity:** important  
**Raised by:** Agent 2  
**Evidence:** `review_context.md:40-43`, `review_context.md:65`, `review_context.md:97-99`; `design.md:13-17`, `design.md:46`

The proposed DPO construction chooses highest and lowest `S_style` candidates. That can mark stylish but invalid YAML/JSON-LD as `chosen`, or reject a correct but plainer answer. Style is important, but it should not outrank schema validity, task completion, factuality, or leakage safety.

**Correction:** Make ranking lexicographic: hard schema validity, task completeness, factual/provenance checks, no leakage, then style. Use format-invalid outputs as explicit rejection/repair examples, not as style-only preference pairs.

### 10. `S_style` is under-specified and does not match the current linter API

**Severity:** important  
**Raised by:** Agent 2  
**Evidence:** `review_context.md:40-41`, `review_context.md:97`; `skills/russellian-style/skill_api.py`

The proposal says "12 programmatic style linters," but the local `russellian-style` API exposes a registry with more rule names and a default subset. The scalar formula lacks normalized units, fixed weights, failure policy, rule versioning, and separation between style and length.

**Correction:** Add a versioned scoring module that records raw counts, normalized per-token/per-sentence rates, rule weights, linter versions, and score components. Treat linter import/runtime failures as scoring failures. Keep length as a hard eligibility/range gate or separate term, not an unbounded scalar boost.

### 11. Candidate generation and triplets are not reproducible

**Severity:** important  
**Raised by:** Agent 2, Agent 4  
**Evidence:** `review_context.md:65`, `review_context.md:98-99`; `design.md:46`

The design only says candidates are generated at `T=0.7`. It does not specify candidate count, generator model/version, seeds, deduplication, score-margin thresholds, source split timing, or prompt-level holdout. That makes the DPO dataset hard to reproduce or audit.

**Correction:** Define `k` candidates per prompt, generator model tag/digest, seeds, temperature set, dedup hashes, minimum chosen/rejected margin, split-before-generation discipline, and a manifest for every triplet.

### 12. Native Windows RTX 5090 dependency gates are missing

**Severity:** important  
**Raised by:** Agent 3  
**Evidence:** `review_context.md:16`, `review_context.md:27`, `review_context.md:103-109`; `proposal.md:10`, `proposal.md:21`

The plan relies on native Windows PyTorch, bitsandbytes, and an RTX 5090. That stack needs explicit driver/CUDA/PyTorch/bitsandbytes compatibility checks, especially for Blackwell architecture. Without gates, training can fail, segfault, or silently fall back.

**Correction:** Add a preflight that asserts CUDA availability, driver version, PyTorch CUDA build, `torch.cuda.get_device_capability()`, compiled architecture support, bf16 support, bitsandbytes 4-bit load, and a one-batch backward pass before running the full job.

### 13. Ollama `ADAPTER` is a model creation step, not dynamic per-request loading

**Severity:** important  
**Raised by:** Agent 3  
**Evidence:** `review_context.md:17`, `review_context.md:23`, `review_context.md:49`, `review_context.md:111-115`; `proposal.md:11`, `proposal.md:17`, `proposal.md:23`

The text frames the adapter as dynamically loaded in Ollama, but `ADAPTER` belongs in a Modelfile used to create a model tag. `adapter.py` should route to the created model tag; it should not be expected to attach arbitrary adapters per request.

**Correction:** Add an explicit deployment step: `ollama create russellgpt -f Modelfile`, record base digest and adapter hash, then route `make_ollama_call(model="russellgpt")` to that model.

### 14. Routing changes are incomplete

**Severity:** important  
**Raised by:** Agent 3  
**Evidence:** `review_context.md:18`, `review_context.md:115`; `llm-infra/src/llm_infra/adapter.py:16`; `llm-infra/src/llm_infra/persona_dispatch.py:105`; skill `production_llm.py` wrappers

Task 3.4 only mentions `adapter.py`, but model defaults also live in persona dispatch and skill wrappers. Updating one file will leave some Ollama paths on `gemma4:31b`.

**Correction:** Add a central config/env override for default Ollama model selection, or update all model defaults and CLI `--model` defaults. Add a matrix test that proves every Ollama path resolves to `russellgpt` unless explicitly overridden.

### 15. Cache keys can hide adapter regressions

**Severity:** important  
**Raised by:** Agent 3  
**Evidence:** `llm-infra/src/llm_infra/cache.py:3`; `llm-infra/src/llm_infra/adapter.py`

The cache keys include model name, prompt, temperature, `num_predict`, and `num_ctx`, but not adapter SHA, Modelfile hash, base digest, or `think`. Recreating `russellgpt` under the same tag can return stale cached outputs during verification.

**Correction:** Disable cache during fine-tune verification. For production, include model digest, adapter SHA256, Modelfile hash, and `think` in cache keys.

### 16. CPU/GPU regression checks are too weak

**Severity:** important  
**Raised by:** Agent 3  
**Evidence:** `review_context.md:120`; `llm-infra/src/llm_infra/health.py:18`

The task asks for zero CPU regression, but current health logic is latency-based and can miss partial offload. A warm 10-token latency check is not sufficient for a 31B model with adapters and 8192 context.

**Correction:** Verify `ollama ps` reports full or expected GPU residency, expected context length, and VRAM size. Measure warm tokens/sec excluding load duration and fail if CPU offload or material throughput regression is detected.

### 17. Ollama unload hook is underspecified

**Severity:** important  
**Raised by:** Agent 3  
**Evidence:** `review_context.md:109`; `llm-infra/src/llm_infra/persona_dispatch.py:107`

The task says to unload active Ollama inference instances, but existing persona dispatch can keep models alive for 3600 seconds. The plan does not say how to force eviction or verify free VRAM before training.

**Correction:** Before training, send an Ollama request with `keep_alive: 0` or run `ollama stop <model>`, poll `/api/ps` until the model is absent, then assert free VRAM with `nvidia-smi`.

## Recommended Corrections

1. **Rewrite the model identity and deployment section.** Pick one base model. Pin it by digest. Rename all artifacts consistently to `russellgpt` or another single name. Make the Ollama creation step explicit.
2. **Add a memory-profiled training configuration.** Specify batch size, accumulation, NF4/double quant, bf16, optimizer, DPO reference strategy, fallback LoRA rank, max sequence length, warmup, scheduler, eval cadence, and stop criteria.
3. **Fix PEFT target modules.** Replace glob-like `language_model` patterns with actual module suffixes and assert nonzero trainable params.
4. **Remove exposed synthetic `<think>` targets.** Train on final outputs plus short rationale summaries or labels. If think blocks remain internal, define a parser and strip them before artifact validation.
5. **Replace the Gutenberg list with a verified allow-list.** Include title/author/eBook URL/public-domain evidence/hash metadata and fail on mismatches.
6. **Make DPO correctness-first.** Gate candidates by schema, task completion, provenance/factuality, leakage, and then style. Use style only after hard validity gates pass.
7. **Version `S_style`.** Define rule set, weights, normalization, failure policy, and score manifest. Align it with the current `russellian-style` API.
8. **Add split and leakage discipline.** Create deterministic train/validation/test/acceptance partitions before candidate generation. Check exact and near-duplicate leakage across prompts, outputs, rationales, and ledgers.
9. **Expand verification.** Include YAML parser compatibility, JSON-LD/JSONL ledger validation, malformed-output negative tests, cache-disabled runs, GPU residency checks, and throughput regression checks.
10. **Centralize model routing.** Use a single default model config/env var and test all Ollama paths, not only `adapter.py`.
11. **Make cache adapter-aware.** Include base digest, adapter SHA, Modelfile hash, and `think` in keys, or bypass cache for all acceptance verification.
12. **Pin Windows GPU dependencies.** Gate on driver, CUDA, PyTorch build, bitsandbytes 4-bit support, bf16 support, and a one-batch train smoke test.

## Minimal Revised Acceptance Gate

A revised plan should not be approved until it demonstrates all of the following:

- `train_adapter.py --dry-run-memory-profile` completes on RTX 5090 with the target sequence length and logs peak VRAM.
- `train_adapter.py --smoke-steps 100` runs SFT and DPO smoke steps without CPU fallback.
- LoRA trainable parameter count is nonzero and matches the expected module set.
- The Ollama model is created from the same pinned base used in training.
- `ollama run russellgpt` passes a review artifact test with parser-compatible YAML frontmatter.
- A ledger prompt produces strict JSONL/JSON-LD that validates against the book-knowledge schema/context.
- The verification suite fails on malformed think blocks, malformed YAML, malformed ledger rows, and leaked holdout fixtures.
- Dataset manifest proves checked source IDs, cleaned hashes, and train/validation/test/acceptance separation.

## Panel Notes

- Agent 1 focused on fine-tuning mechanics and found the base mismatch, target-module risk, VRAM optimism, context-length mismatch, and missing effective-batch controls.
- Agent 2 focused on style alignment and found wrong Gutenberg IDs, risky synthetic think targets, style-only DPO ranking, under-specified `S_style`, licensing/provenance gaps, and non-reproducible candidate generation.
- Agent 3 focused on systems/MLOps and found the base mismatch, Windows RTX 5090 dependency gates, Ollama adapter deployment semantics, incomplete model routing, weak CPU regression checks, unload gaps, and adapter-blind cache keys.
- Agent 4 focused on QA/compliance and found missing JSON-LD validation, train/test split discipline, leakage checks, think/YAML grammar conflicts, and negative fixture gaps.
