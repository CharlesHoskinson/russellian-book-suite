# Gemma 4 Fine-Tuning Plan — Panel Audit (2026-05-24)

Review target: `docs/plans/2026-05-24-gemma4-fine-tuning.md` (+ `design.md`)
Panel: Fine-Tuning Engineer, MLOps/Deployment Architect, Data Curation/Style, QA/Compliance — dispatched as parallel read-only agents.
Method: read plan + design + prior `audit.md`; verified claims against the live HF repo, Ollama (`ollama show`), `nvidia-smi`, the venv, the `russellian-style` API, and live Gutenberg pages.

This audit is of the **revised** plan (the prior `audit.md` rejected an earlier `gemma-2-27b` version). The Gemma-2→Gemma-4 base swap silently invalidated two of the prior audit's accepted fixes; those plus regressions are the focus.

## Verdict: Reject pending corrections (10 blockers, ~13 important). All corrections applied to the plan; the two factual defects also fixed in `design.md`.

---

## Blockers

| # | Finding | Evidence | Correction (applied in plan) |
|---|---------|----------|------------------------------|
| B1 | **Phantom HF revision.** Pinned `8d2f7a93…` returns HTTP 404 and is absent from the 6-commit history (`fcf2302, ba74f5b, 145dc25, 439edf5, e51e7dc, 419b2ef`). | HF API + `commits/main`; plan:131, design REQ-005/§2.1/§2.2 | Re-pin to verified HEAD `fcf2302760ae9c6e528a8dbba9dd636e56848237`; verify against GGUF provenance. |
| B2 | **Multimodal target-module collision.** Base is `Gemma4ForConditionalGeneration` (vision tower). Suffix-only `q/k/v_proj` also match the SigLIP encoder (`out_proj`/`fc1`/`fc2` don't collide). | HF Gemma4 docs; plan Task 2 §"suffix-only" | Load `AutoModelForCausalLM` (→`Gemma4ForCausalLM`) or scope to `language_model.model.layers.*`; assert trainable>0. |
| B3 | **Ollama ADAPTER unsupported for gemma4.** Ollama's safetensors ADAPTER path supports only up to Gemma 2; multimodal adapter also carries vision tensors. | docs.ollama.com/import; ollama #15697, PR #6327 | Replace with `merge_and_unload()`→fp16→`convert_hf_to_gguf`→`llama-quantize Q4_K_M`; `FROM ./gguf`, no ADAPTER. |
| B4 | **NF4↔Q4_K_M quant mismatch.** Adapter calibrated to NF4 rounding error is numerically wrong applied over Q4_K_M. | design §2.2 + env fact | Merge dequantizes to fp16 before merge (neutralizes), then re-quantize (folds into B3). |
| B5 | **Wrong stop token.** `<|im_end|>` is ChatML/Qwen, absent from Gemma vocab → never stops. | plan Task 3 / design §2.3 | `PARAMETER stop "<end_of_turn>"` (+`<start_of_turn>`). |
| B6 | **Gradient checkpointing dropped.** REQ-005 requires it; Task 2 omits it → OOM at 31B/4096 on 32 GB. | design REQ-005 vs plan Task 2 Step 3 | Add `gradient_checkpointing=True` + `gradient_checkpointing_enable(use_reentrant=False)`. |
| B7 | **Preflight is a bare `import`.** Step text claims a 4-bit-load check; code only imports bnb — can't catch a wheel without sm_120 kernels. | plan Task 0 code | Real NF4 load + one-batch backward on CUDA; hard-fail on sm_120/bf16. |
| B8 | **No dependency-install task.** venv has no torch; default pip = non-sm_120 build. | env fact | New Task -1: cu128 wheel + pinned peft/trl/bnb/accelerate. |
| B9 | **`S_style` references nonexistent API.** `passives`→real key is `active-voice`; `uniformity_penalty` has no implementation; `burstiness` is a Fano-factor float (dimensionally inconsistent). | `skill_api.py` registry | Use `active-voice`; drop `uniformity_penalty`; define burstiness scalar; versioned `StyleScore` w/ weights + failure policy. |
| B10 | **DPO not correctness-first.** Step 3 ranks by style within a pool missing completeness + factuality/provenance gates (REQ-004). | plan Task 1 vs design REQ-004 | 5-tier lexicographic gate (schema→completeness→factuality→leakage→style); min margin δ; skip if <2 pass. |

## Important

- **Routing incomplete:** `persona_dispatch.py:105` hardcodes `model="gemma4:31b"`; updating only `adapter.py` leaves paths on the base. → update both + `OLLAMA_MODEL` env + matrix test.
- **Cache key omits `think`** (silently dropped at the cache boundary) and adapter SHA/Modelfile/digest. → thread through `_cache_key`/get/put.
- **VRAM eviction underspecified:** no poll-until-empty, no `nvidia-smi` free-VRAM assert (base ~19 GB of 32). → poll `/api/ps` + assert ≥28 GB free.
- **`model_ref` is wrong** — TRL param is `ref_model=None`.
- **VRAM profiler uses a dummy model** → fallback is dead code. → profile the real quantized model + reset_peak_memory_stats.
- **DPO `beta=0.06` and stage LRs dropped** from the code spec. → restore; add warmup/cosine.
- **Base equivalence ≠ weight provenance:** Ollama digest doesn't prove the GGUF came from the trained HF revision. → record source SHA sidecar (`MODEL_PINS.md`) and assert.
- **Compliance not decomposed:** one prose clause vs four named gates (YAML position / JSONL rows / JSON-LD context / report schema).
- **Nested-think regex bug:** non-greedy strip leaves residuals; negative fixture must feed RAW output to the validator. → loop-until-stable strip.
- **Leakage too narrow:** exact-prompt only; needs near-duplicate across prompts/outputs/rationales + split-manifest comparison; split must be created in curation before generation.
- **Residency latency-based:** `health.py` can't detect partial offload. → parse `ollama ps` `size_vram==size` + tokens/sec excluding load.
- **Cache bypass not enforced** structurally in verification. → `cache=False` + spy assertion.
- **Cross-repo import unspecified:** `sibling_skills/loader.py` defaults to `~/.claude/skills`, not the skill. → set `SIBLING_SKILLS_ROOT` or pip-install.

## Confirmed correct (not changed)
- All seven Gutenberg IDs verified against live pages (prior audit's wrong IDs 17020/37060 are fixed).
- Gemma 4 is real (released 2026-04-02); `google/gemma-4-31B-it` exists; `gemma4:31b` ID `6316f0629137` matches the base-equivalence check.
- DPO `ref_model=None` + adapter-disable reference strategy is sound; correctness-first lexicographic ordering is the right model.
