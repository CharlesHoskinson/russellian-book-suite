# OpenSpec Change Context: Custom Gemma 4 31B Fine-Tuning for Cardano Governance Book Skills

This document compiles the Proposal, Technical Design, and Tasks checklist for the `gemma4-fine-tuning` change in the Cardano Governance `russellian-book-suite` workspace. It is intended for comprehensive multiagent review by GPT-5.5.

---

## 1. Proposal

### Intent
Align the local LLM dispatch path (`llm-infra`) with the high reasoning and quality standards of the Claude subagent dispatch path. By training a custom `russellgpt` model (**RussellGPT**) using QLoRA fine-tuning on our local RTX 5090 GPU, we will improve the model's adherence to the Russellian academic style, ensure strict format validation (like YAML frontmatter and JSON-LD ledgers), reduce the input context footprint by hardcoding persona rules, and eliminate empty response and timeout errors.

### Scope
In scope:
- Crawling the workspace to curate a multi-task fine-tuning dataset containing chapter drafts, persona reviews, and ledger updates.
- Synthesizing clean final outputs and stripping any reasoning blocks from target inputs to allow native thinking during inference.
- Quantizing and fine-tuning `google/gemma-4-31b-it` using Hugging Face PEFT (LoRA) and TRL on native Windows PyTorch.
- Packaging the fine-tuned adapter and loading it directly in Ollama using a custom `Modelfile` with the `ADAPTER` command.
- Modifying `adapter.py` to route calls through the new `russellgpt` model by default.
- Building a verification suite (`verify_finetune.py`) to test reasoning block outputs and YAML compliance.

Out of scope:
- Modifying the core logic of the seven `russellian-book-suite` skills.
- Full weight-merging and GGUF quantization (avoided in favor of dynamic LoRA adapters).
- Cloud-based training pipelines.

### Approach
A Python script crawls the active workspace to build a training dataset, mapping task prefixes (e.g. `[TASK: ChapterReview]`) to prompts and outputs. A training wrapper script unloads Ollama models and fine-tunes the base model in 4-bit precision using native Windows PyTorch + transformers + peft + trl. The resulting LoRA adapter is loaded directly over `gemma4:31b` via an Ollama Modelfile configuration, and verified against warm latency benchmarks and format gates.

---

## 2. Technical Design

### Requirements (EARS Format)

*   **REQ-LLM-TUNE-001 — Ubiquitous**
    The system shall curate a dataset of instruction-response pairs by mapping inputs (prompts, outline contracts) and outputs (final markdown reports, reviews, ledgers) from the workspace history.
*   **REQ-LLM-TUNE-002 — Ubiquitous**
    If outputs contain reasoning blocks or `<think>` tags, the curation system shall strip them from the target training text to prevent learning post-hoc rationales and maintain compatibility with existing YAML parsers.
*   **REQ-LLM-TUNE-003 — Ubiquitous**
    The curation system shall use the 12 programmatic style linters in `russellian-style` to assign a composite scalar preference score $S_{style}$ to generated outputs, aligning with the linter API and weights registry.
*   **REQ-LLM-TUNE-004 — Ubiquitous**
    The curation system shall construct a DPO preference dataset of `(prompt, chosen, rejected)` triplets using lexicographical ranking where candidates are first gated by schema validity, completeness, and lack of training leakage before applying style-based ranking.
*   **REQ-LLM-TUNE-005 — Ubiquitous**
    The training system shall run fine-tuning on the base model `google/gemma-4-31B-it` (pinned HF revision `8d2f7a9341498b3f27de10b50b503d289196b014`) using 4-bit NF4 double quantization, gradient checkpointing, batch size of 1, and LoRA targeting backbone layers to fit within 32GB VRAM.
*   **REQ-LLM-TUNE-006 — Ubiquitous**
    The training system shall execute a two-stage pipeline: (1) SFT Warmup on a verified allow-list of Bertrand Russell Project Gutenberg texts, and (2) DPO preference alignment using the correctness-gated dataset.
*   **REQ-LLM-TUNE-007 — Ubiquitous**
    The integration system shall compile the model using `ollama create russellgpt -f Modelfile` with the `ADAPTER` command to load the Safetensors adapter over the pinned local `gemma4:31b` base model (ID: `6316f0629137`, digest `sha256:6316f0629137d6e4cc7b9f87451006e98716b14249a5b6c8ba876bf7d848ccf4`).
*   **REQ-LLM-TUNE-008 — Ubiquitous**
    The verification system shall run compliance tests validating reasoning block parsing, YAML frontmatter position, JSONL/JSON-LD ledger schemas, exact training leakage, and GPU residency.

### Technical Details

#### Two-Stage Training Details
1.  **Stage 1: SFT Warmup:** Fine-tune `google/gemma-4-31B-it` (pinned HF revision `8d2f7a9341498b3f27de10b50b503d289196b014`) via Causal LM (1 epoch, LR $1 \times 10^{-5}$) on a compiled corpus of Bertrand Russell's public-domain works. The curation script must verify downloaded files against this checked allow-list:
    *   *The Problems of Philosophy* (ID: 5827)
    *   *The Analysis of Mind* (ID: 2529)
    *   *Mysticism and Logic and Other Essays* (ID: 25447)
    *   *Proposed Roads to Freedom* (ID: 690)
    *   *Our Knowledge of the External World* (ID: 37090)
    *   *Introduction to Mathematical Philosophy* (ID: 41654)
    *   *The Problem of China* (ID: 13940)
    *   *Workflow:* Fetch books via the `scrapling-fetch` skill, strip Gutenberg headers/footers via sentinels, segment into paragraph blocks (~200–500 words), and pack tokens to 4,096 boundaries.
2.  **Stage 2: DPO Alignment:** Train SFT-warmed weights using `trl.DPOTrainer` on prompt triplets generated at temperature $T=0.7$ and ranked by correctness-first gates (1 epoch, LR $5 \times 10^{-6}$, $\beta=0.06$). Reference logprobs are calculated by disabling the adapter to save memory.

#### PEFT & Quantization Configuration
- **Base Model:** `google/gemma-4-31B-it` (pinned Hugging Face revision `8d2f7a9341498b3f27de10b50b503d289196b014`; must match the architecture, weights, and parameters of the local Ollama base `gemma4:31b` ID: `6316f0629137` / digest `sha256:6316f0629137d6e4cc7b9f87451006e98716b14249a5b6c8ba876bf7d848ccf4`)
- **LoRA configuration:**
  - `r`: 64
  - `lora_alpha`: 128
  - `lora_dropout`: 0.05
  - `target_modules`: `["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]` (suffix-only target modules to prevent PEFT matching failures; verified via preflight parameter count check)
- **Trainer:** Hugging Face `trl.DPOTrainer` with context length capped at 4,096 tokens.

#### Ollama Modelfile
- Model name: `russellgpt`
- Config details:
  ```dockerfile
  # Pins local base model gemma4:31b (ID: 6316f0629137)
  FROM gemma4:31b
  ADAPTER ./models/russellgpt-adapter
  PARAMETER num_ctx 4096
  PARAMETER temperature 0.4
  PARAMETER stop "<|im_end|>"
  SYSTEM "You are the custom-tuned Gemma 4 31B model (RussellGPT) for the Cardano Governance book suite..."
  ```

---

## 3. Tasks Checklist

### 1. Data Preparation
- [ ] 1.1 Create dataset curation script `curate_dataset.py` in `llm-infra/scripts/` (REQ-LLM-TUNE-001)
- [ ] 1.2 Implement prompt reconstruction by mapping outline contracts and output pages without synthetic `<think>` blocks (REQ-LLM-TUNE-002)
- [ ] 1.3 Add Gutenberg downloader and metadata preprocessor using `scrapling-fetch` (REQ-LLM-TUNE-006)
- [ ] 1.4 Implement strict eBook allow-list validations (verify ID, title, author, and hashes on download for IDs 5827, 2529, 25447, 690, 37090, 41654, 13940) (REQ-LLM-TUNE-006)
- [ ] 1.5 Implement `russellian-style` linter wrapper to calculate composite $S_{style}$ metric (REQ-LLM-TUNE-003)
- [ ] 1.6 Implement lexicographical ranking for DPO candidates: gate first by schema validity, completeness, and non-leakage, then apply style ranking (REQ-LLM-TUNE-004)
- [ ] 1.7 Add leakage checks across prompts, outputs, and ledgers; export train/val/test/acceptance split manifest to `dataset_dpo.jsonl` (REQ-LLM-TUNE-004)

### 2. Model Training Configuration
- [ ] 2.1 Create training execution script `train_adapter.py` targeting base model `google/gemma-4-31B-it` (pinned HF revision `8d2f7a9341498b3f27de10b50b503d289196b014`) (REQ-LLM-TUNE-005)
- [ ] 2.2 Implement GPU/CUDA preflight assertions (CUDA availability, device capability, PyTorch CUDA build, bitsandbytes 4-bit load, and bf16 support) (REQ-LLM-TUNE-005)
- [ ] 2.3 Implement pre-training VRAM eviction hooks (unload active Ollama models, poll `/api/ps`, assert free VRAM with `nvidia-smi`) (REQ-LLM-TUNE-005)
- [ ] 2.4 Implement `--dry-run-memory-profile` preflight (asserts sequence length 4096 fits under 32GB VRAM using NF4 quant, gradient checkpointing, and `model_ref=None` sharing weights) (REQ-LLM-TUNE-005)
- [ ] 2.5 Run SFT Warmup stage on Project Gutenberg Bertrand Russell corpus (REQ-LLM-TUNE-006)
- [ ] 2.6 Run DPOTrainer stage utilizing the correctness-gated dataset (REQ-LLM-TUNE-006)
- [ ] 2.7 Configure high-rank LoRA parameters ($r=64$, $\alpha=128$, suffix-only target modules) and assert non-zero parameter counts (REQ-LLM-TUNE-005)

### 3. Ollama Integration & Deployment
- [ ] 3.1 Write the custom Ollama `Modelfile` linking base `gemma4:31b` (ID: `6316f0629137`, digest `sha256:6316f0629137d6e4cc7b9f87451006e98716b14249a5b6c8ba876bf7d848ccf4`) and target adapter `./models/russellgpt-adapter/` (REQ-LLM-TUNE-007)
- [ ] 3.2 Set parameter configs for context window (`num_ctx 4096`) and temperature (REQ-LLM-TUNE-007)
- [ ] 3.3 Add default system prompts mapping to target task instructions (REQ-LLM-TUNE-007)
- [ ] 3.4 Deploy model locally using `ollama create russellgpt -f Modelfile` (REQ-LLM-TUNE-007)
- [ ] 3.5 Update central configuration to select model `russellgpt` by default and route all Ollama endpoints (REQ-LLM-TUNE-007)

### 4. Verification & Compliance Gating
- [ ] 4.1 Write verification test script `verify_finetune.py` with caching disabled (REQ-LLM-TUNE-008)
- [ ] 4.2 Implement pre-strip reasoning block filter in `adapter.py` to prevent `<think>` blocks from polluting YAML/JSONL parsers (REQ-LLM-TUNE-002)
- [ ] 4.3 Validate parser compatibility with existing book-review and report tooling (REQ-LLM-TUNE-008)
- [ ] 4.4 Add negative test cases (malformed think blocks, invalid YAML, invalid JSONL schema) and verify compiler fails (REQ-LLM-TUNE-008)
- [ ] 4.5 Run residency checks (`ollama ps`) to verify `russellgpt` is 100% resident in GPU VRAM and measure warm tokens/sec (REQ-LLM-TUNE-008)
