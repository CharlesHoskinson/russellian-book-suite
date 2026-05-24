# OpenSpec Change Context: Custom Gemma 4 31B Fine-Tuning for Cardano Governance Book Skills

This document compiles the Proposal, Technical Design, and Tasks checklist for the `gemma4-fine-tuning` change in the Cardano Governance `russellian-book-suite` workspace. It is intended for comprehensive multiagent review by GPT-5.5.

---

## 1. Proposal

### Intent
Align the local LLM dispatch path (`llm-infra`) with the high reasoning and quality standards of the Claude subagent dispatch path. By training a custom `russellgpt` model (**RussellGPT**) using QLoRA fine-tuning on our local RTX 5090 GPU, we will improve the model's adherence to the Russellian academic style, ensure strict format validation (like YAML frontmatter and JSON-LD ledgers), reduce the input context footprint by hardcoding persona rules, and eliminate empty response and timeout errors.

### Scope
In scope:
- Crawling the workspace to curate a multi-task fine-tuning dataset containing chapter drafts, persona reviews, and ledger updates.
- Synthesizing or generating high-quality `<think>...</think>` reasoning traces for historical run outputs.
- Quantizing and fine-tuning `gemma-2-27b-it` using Hugging Face PEFT (LoRA) and TRL on native Windows PyTorch.
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
    When curating reviews and chapter drafts that lack reasoning logs, the curation system shall generate and inject gold-standard step-by-step reasoning logs within `<think>...</think>` tags to teach the model to reason.
*   **REQ-LLM-TUNE-003 — Ubiquitous**
    The curation system shall use the 12 programmatic style linters in `russellian-style` to assign a composite scalar preference score $S_{style}$ to generated outputs:
    $$S_{style}(c) = \sum_{i} w_{R, i} \cdot R_i(c) - \sum_{j} w_{P, j} \cdot P_j(c) + P_{length}(c)$$
*   **REQ-LLM-TUNE-004 — Ubiquitous**
    The curation system shall construct a DPO preference dataset of `(prompt, chosen, rejected)` triplets where the `chosen` candidate has the highest $S_{style}$ score and the `rejected` candidate has the lowest.
*   **REQ-LLM-TUNE-005 — Ubiquitous**
    The training system shall run fine-tuning on the base model `google/gemma-2-27b-it` using 4-bit quantization, gradient checkpointing, and LoRA targeting language backbone layers to fit within 32GB VRAM.
*   **REQ-LLM-TUNE-006 — Ubiquitous**
    The training system shall execute a two-stage pipeline: (1) SFT Warmup on a public-domain Bertrand Russell corpus, and (2) DPO preference alignment using the linter-graded dataset.
*   **REQ-LLM-TUNE-007 — Ubiquitous**
    The integration system shall use the Ollama `Modelfile` syntax with the `ADAPTER` command to dynamically load the Safetensors adapter over the local `gemma4:31b` base model.
*   **REQ-LLM-TUNE-008 — Ubiquitous**
    The verification system shall run a mock chapter review using the custom model, validating that the output starts with `<think>` tags, finishes with valid YAML frontmatter, and completes without timeouts.

### Technical Details

#### Two-Stage Training Details
1.  **Stage 1: SFT Warmup:** Fine-tune `google/gemma-2-27b-it` via Causal LM (1 epoch, LR $1 \times 10^{-5}$) on a compiled corpus of Bertrand Russell's public-domain prose-heavy works from Project Gutenberg:
    *   *The Problems of Philosophy* (ID 5827)
    *   *The Analysis of Mind* (ID 2529)
    *   *Mysticism and Logic and Other Essays* (ID 17020)
    *   *Proposed Roads to Freedom* (ID 690)
    *   *Our Knowledge of the External World* (ID 37090)
    *   *Introduction to Mathematical Philosophy* (ID 37060)
    *   *The Problem of China* (ID 13940)
    *   *Workflow:* Download raw texts using the `scrapling-fetch` skill, strip Project Gutenberg licensing boilerplate via start/end sentinels, segment into paragraph blocks (~200–500 words), and pack tokens to 4,096 boundaries.
2.  **Stage 2: DPO Alignment:** Train SFT-warmed weights using `trl.DPOTrainer` (or `trl.IPOTrainer`) on prompt triplets generated at temperature $T=0.7$ and scored via the composite style linter formula (1 epoch, LR $5 \times 10^{-6}$, $\beta=0.06$).

#### PEFT & Quantization Configuration
- **Base Model:** `google/gemma-2-27b-it`
- **LoRA configuration:**
  - `r`: 64
  - `lora_alpha`: 128
  - `lora_dropout`: 0.05
  - `target_modules`: Language backbone layers:
    `"*.language_model.*.q_proj"`, `"*.language_model.*.k_proj"`, `"*.language_model.*.v_proj"`, `"*.language_model.*.o_proj"`, `"*.language_model.*.gate_proj"`, `"*.language_model.*.up_proj"`, `"*.language_model.*.down_proj"`
- **Trainer:** Hugging Face `trl.DPOTrainer` with context length capped at 4,096.

#### Ollama Modelfile
- Model name: `russellgpt`
- Config details:
  ```dockerfile
  FROM gemma4:31b
  ADAPTER ./models/gemma4-book-adapter
  PARAMETER num_ctx 8192
  PARAMETER temperature 0.4
  PARAMETER stop "<|im_end|>"
  SYSTEM "You are the custom-tuned Gemma 4 31B model (RussellGPT) for the Cardano Governance book suite..."
  ```

---

## 3. Tasks Checklist

### 1. Data Preparation
- [ ] 1.1 Create dataset curation script `curate_dataset.py` in `llm-infra/scripts/` (REQ-LLM-TUNE-001)
- [ ] 1.2 Implement prompt reconstruction by mapping outline contracts and output pages (REQ-LLM-TUNE-001)
- [ ] 1.3 Add logic to synthesize and inject gold-standard `<think>` logs for historical runs (REQ-LLM-TUNE-002)
- [ ] 1.4 Import `russellian-style` linters to calculate the composite preference score $S_{style}$ (REQ-LLM-TUNE-003)
- [ ] 1.5 Generate candidate pool, rank outputs, and build DPO preference triplets (REQ-LLM-TUNE-004)
- [ ] 1.6 Export formatted training data to `dataset_dpo.jsonl` (REQ-LLM-TUNE-004)
- [ ] 1.7 Add Gutenberg downloader and preprocessor using the `scrapling-fetch` skill to fetch and clean Bertrand Russell's corpus of 7 books (REQ-LLM-TUNE-006)

### 2. Model Training Configuration
- [ ] 2.1 Create training execution script `train_adapter.py` (REQ-LLM-TUNE-005)
- [ ] 2.2 Configure 4-bit BitsAndBytes quantization loader (REQ-LLM-TUNE-005)
- [ ] 2.3 Implement SFT Warmup stage on Project Gutenberg Bertrand Russell corpus (REQ-LLM-TUNE-006)
- [ ] 2.4 Implement DPOTrainer stage utilizing the linter-graded dataset (REQ-LLM-TUNE-006)
- [ ] 2.5 Configure high-rank LoRA parameters ($r=64$, $\alpha=128$, custom target regex) (REQ-LLM-TUNE-005)
- [ ] 2.6 Enable gradient checkpointing and memory-mapped optimizers (REQ-LLM-TUNE-005)
- [ ] 2.7 Add pre-training GPU hooks to unload active Ollama inference instances (REQ-LLM-TUNE-005)

### 3. Ollama Integration
- [ ] 3.1 Write the custom Ollama `Modelfile` using the `ADAPTER` command (REQ-LLM-TUNE-007)
- [ ] 3.2 Set parameter configs for context window (`num_ctx 8192`) and temperature (REQ-LLM-TUNE-007)
- [ ] 3.3 Add default system prompts mapping to target task instructions (REQ-LLM-TUNE-007)
- [ ] 3.4 Modify default model configurations in `adapter.py` to target the custom `russellgpt` model (REQ-LLM-TUNE-007)

### 4. Verification & Testing
- [ ] 4.1 Write verification test script `verify_finetune.py` (REQ-LLM-TUNE-008)
- [ ] 4.2 Validate output reasoning block parsing and YAML format gates (REQ-LLM-TUNE-008)
- [ ] 4.3 Measure warm inference metrics on RTX 5090 to ensure zero CPU regression (REQ-LLM-TUNE-008)
