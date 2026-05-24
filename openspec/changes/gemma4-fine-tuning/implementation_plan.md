# Implementation Plan - Custom Gemma 4 31B Fine-Tuning (RussellGPT)

This implementation plan outlines the setup, training, deployment, and validation of the custom `russellgpt` model (**RussellGPT**), derived from `gemma4:31b` / `google/gemma-4-31B-it`. This custom model will serve as a local, private, and cost-free drop-in replacement for the Claude subagent path.

## User Review Required

> [!IMPORTANT]
> **VRAM Eviction and Memory Optimization:** Fine-tuning a 31B model requires unloading the active Ollama inference instances (`ollama unload gemma4:31b` or sending `keep_alive: 0`) to free VRAM. The training script requires the full 32GB of the RTX 5090 VRAM.
>
> **Blackwell/Ada GPU Preflight Gates:** We use native Windows PyTorch. The training script will execute a preflight verification checking CUDA compatibility, double quantization capabilities (bitsandbytes), `bf16` support, and a single-batch training pass.
>
> **No Cache in Verification:** To prevent stale cache hits from masking adapter performance regressions, all verification stages bypass the disk cache.

---

## Proposed Changes

We will introduce dataset curation, training, and integration components in the `llm-infra` package.

### Component: `llm-infra`

#### [NEW] [curate_dataset.py](file:///C:/governance/llm-infra/scripts/curate_dataset.py)
A Python script to curate the dataset: SFT warmup texts and DPO triplets.
- **SFT Curation:** Polite rate-limited downloads from Project Gutenberg using the built-in scraper, stripping header/footers using regex sentinels, segmenting into paragraph units, and packing to 4,096 context windows. Files are validated against a checked allow-list (verifying ID, title, author, and content hashes on download):
  - *The Problems of Philosophy* (ID: 5827)
  - *The Analysis of Mind* (ID: 2529) [CORRECTED]
  - *Mysticism and Logic and Other Essays* (ID: 25447)
  - *Proposed Roads to Freedom* (ID: 690)
  - *Our Knowledge of the External World* (ID: 37090)
  - *Introduction to Mathematical Philosophy* (ID: 41654)
  - *The Problem of China* (ID: 13940) [CORRECTED]
- **DPO Curation:** Generates $N$ candidates per prompt using the base model at $T=0.7$.
- **Correctness-First Lexicographical Gating:** Rejects any candidates failing schema validity, completeness, provenance checks, or containing leakage. Only candidates passing all correctness gates are scored by the style metric.
- **Style Metric ($S_{style}$):** Imports `russellian-style` linters via `skill_api.py`. Evaluates issues normalized per 1,000 words. Calculates:
  $$S_{style}(c) = - (\text{hedging\_count} + \text{passive\_voice\_count} + \text{ai\_vocabulary\_count} + \text{rhythm\_uniformity\_penalty}) \times 1000 / \text{word\_count} + \text{burstiness\_score}$$
- **Split & Leakage Discipline:** Partition prompts into `train`/`val`/`test`/`acceptance` prior to candidate generation. Performs exact and near-duplicate leakage checks across splits.

#### [NEW] [train_adapter.py](file:///C:/governance/llm-infra/scripts/train_adapter.py)
Training execution pipeline supporting SFT Warmup and `DPOTrainer` (`trl` library) under 32GB VRAM.
- **GPU Preflight Verification:** Asserts CUDA, `torch.cuda.get_device_capability()`, Blackwell/Ada capability, `bf16` support, and `bitsandbytes` 4-bit loading. Runs a 100-step VRAM profile to detect OOM/fallback and aborts if unsafe.
- **Base Model Alignment Verification:** Asserts that the base model `google/gemma-4-31B-it` (pinned HF revision `8d2f7a9341498b3f27de10b50b503d289196b014`) maps model details (attention headers, dimensions, architecture) compatibly with the local Ollama model config before launching training.
- **Memory Optimization:**
  - `per_device_train_batch_size=1`
  - `gradient_accumulation_steps=8`
  - NF4 4-bit quantization with double quantization (`bnb_4bit_use_double_quant=True`)
  - `bf16` compute precision
  - `paged_adamw_8bit` optimizer
  - Gradient checkpointing with `use_cache=False`
  - `model_ref=None` in `DPOTrainer` (forces reference logprobs to share weights with the base model, saving ~20GB of weight duplication overhead)
- **PEFT / LoRA Configuration:**
  - `r=64`, `lora_alpha=128`, `lora_dropout=0.05`
  - `target_modules`: `["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]` (suffix-only target modules to avoid matching errors).
  - Asserts trainable parameters are non-zero.
  - Fallback matrix: If peak VRAM profiling exceeds 30GB, automatically fallback to `r=32` and sequence length 2048.

#### [NEW] [Modelfile](file:///C:/governance/llm-infra/Modelfile)
Ollama Modelfile template to register our custom model.
- Pins base model `gemma4:31b` (ID: `6316f0629137`, digest `sha256:6316f0629137d6e4cc7b9f87451006e98716b14249a5b6c8ba876bf7d848ccf4`) and loads the trained adapter.
- Configures `num_ctx 4096` to match the SFT/DPO context limit, temperature `0.4`, stop tokens, and system instructions.

#### [MODIFY] [adapter.py](file:///C:/governance/llm-infra/src/llm_infra/adapter.py)
- Update default model tag `DEFAULT_MODEL` to `"russellgpt"`.
- Implement a pre-strip regex filter that strips reasoning blocks (`<think>...</think>`) from raw model output before parsing YAML frontmatter or JSON-LD.
- Integrate cache key helpers (`get_adapter_hash`, `get_file_hash`, and `get_model_digest`).

#### [MODIFY] [persona_dispatch.py](file:///C:/governance/llm-infra/src/llm_infra/persona_dispatch.py)
- Update default model parameter to `"russellgpt"` to align all endpoints.
- Allow overriding default Ollama model via `OLLAMA_MODEL` environment variable.

#### [MODIFY] [cache.py](file:///C:/governance/llm-infra/src/llm_infra/cache.py)
- Make cache keys adapter-aware: key off model name, prompt, temperature, `num_predict`, `num_ctx`, plus the model's Ollama digest, the adapter's SHA256 directory hash, the `Modelfile` hash, and `think`.

#### [NEW] [verify_finetune.py](file:///C:/governance/llm-infra/scripts/verify_finetune.py)
Automated compliance gate execution script with caching disabled:
- **Base Equivalence Gate:** Verifies that the local Ollama model ID for `gemma4:31b` matches `6316f0629137` / digest `sha256:6316f0629137d6e4cc7b9f87451006e98716b14249a5b6c8ba876bf7d848ccf4`. Asserts the model architecture is `gemma4` and parameters count is exactly compatible with `google/gemma-4-31B-it`.
- **Positive Validation:** Verifies successful parsing of review artifacts, valid YAML frontmatter formatting, and compliance with the book-knowledge JSONL ledger schema.
- **Negative Validation:** Feeds malformed YAML, nested `<think>` blocks, and malformed ledger rows, asserting the validation suite correctly flags and fails them.
- **Leakage Gate:** Checks test/acceptance prompt inputs against training splits to enforce strict evaluation boundaries.
- **Hardware residency check:** Calls `ollama ps` to assert `russellgpt` is 100% GPU resident (no CPU offloading) and verifies warm throughput (tokens/second) meets baseline standards.

---

## Verification Plan

### Automated Tests
1. Run dataset curation and validation:
   ```powershell
   python C:/governance/llm-infra/scripts/curate_dataset.py --verify
   ```
2. Execute the preflight GPU assertion and VRAM profile:
   ```powershell
   python C:/governance/llm-infra/scripts/train_adapter.py --dry-run-memory-profile
   ```
3. Run the compliance and regression verifier suite:
   ```powershell
   python C:/governance/llm-infra/scripts/verify_finetune.py --model russellgpt
   ```

### Manual Verification
- Verify that `ollama ps` lists `russellgpt` occupying GPU VRAM without CPU leakage during execution.
