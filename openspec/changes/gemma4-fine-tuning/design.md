# Design: Custom Gemma 4 31B Fine-Tuning for Cardano Governance Book Skills

This document describes the technical implementation plan for Curating the dataset, Fine-Tuning the model, Integrating it into Ollama, and Verifying output compliance.

## 1. Requirements (EARS Format)

### REQ-LLM-TUNE-001 — Ubiquitous
The system shall curate a dataset of instruction-response pairs by mapping inputs (prompts, outline contracts) and outputs (final markdown reports, reviews, ledgers) from the workspace history.

### REQ-LLM-TUNE-002 — Ubiquitous
When curating reviews and chapter drafts that lack reasoning logs, the curation system shall generate and inject gold-standard step-by-step reasoning logs within `<think>...</think>` tags to teach the model to reason.

### REQ-LLM-TUNE-003 — Ubiquitous
The curation system shall use the 12 programmatic style linters in `russellian-style` to assign a composite scalar preference score $S_{style}$ to generated outputs:
$$S_{style}(c) = \sum_{i} w_{R, i} \cdot R_i(c) - \sum_{j} w_{P, j} \cdot P_j(c) + P_{length}(c)$$

### REQ-LLM-TUNE-004 — Ubiquitous
The curation system shall construct a DPO preference dataset of `(prompt, chosen, rejected)` triplets where the `chosen` candidate has the highest $S_{style}$ score and the `rejected` candidate has the lowest.

### REQ-LLM-TUNE-005 — Ubiquitous
The training system shall run fine-tuning on the base model `google/gemma-2-27b-it` using 4-bit quantization, gradient checkpointing, and LoRA targeting language backbone layers to fit within 32GB VRAM.

### REQ-LLM-TUNE-006 — Ubiquitous
The training system shall execute a two-stage pipeline: (1) SFT Warmup on a public-domain Bertrand Russell corpus, and (2) DPO preference alignment using the linter-graded dataset.

### REQ-LLM-TUNE-007 — Ubiquitous
The integration system shall use the Ollama `Modelfile` syntax with the `ADAPTER` command to dynamically load the Safetensors adapter over the local `gemma4:31b` base model.

### REQ-LLM-TUNE-008 — Ubiquitous
The verification system shall run a mock chapter review using the custom model, validating that the output starts with `<think>` tags, finishes with valid YAML frontmatter, and completes without timeouts.

---

## 2. Technical Details

### 2.1 Two-Stage Training Details
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

### 2.2 PEFT & Quantization Configuration
- **Base Model:** `google/gemma-2-27b-it`
- **LoRA configuration:**
  - `r`: 64
  - `lora_alpha`: 128
  - `lora_dropout`: 0.05
  - `target_modules`: Language backbone layers:
    `"*.language_model.*.q_proj"`, `"*.language_model.*.k_proj"`, `"*.language_model.*.v_proj"`, `"*.language_model.*.o_proj"`, `"*.language_model.*.gate_proj"`, `"*.language_model.*.up_proj"`, `"*.language_model.*.down_proj"`
- **Trainer:** Hugging Face `trl.DPOTrainer` with context length capped at 4,096.

### 2.3 Ollama Modelfile
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

