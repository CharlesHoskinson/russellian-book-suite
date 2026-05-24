# Design: Custom Gemma 4 31B Fine-Tuning for Cardano Governance Book Skills

This document describes the technical implementation plan for Curating the dataset, Fine-Tuning the model, Integrating it into Ollama, and Verifying output compliance.

## 1. Requirements (EARS Format)

### REQ-LLM-TUNE-001 — Ubiquitous
The system shall curate a dataset of instruction-response pairs by mapping inputs (prompts, outline contracts) and outputs (final markdown reports, reviews, ledgers) from the workspace history.

### REQ-LLM-TUNE-002 — Ubiquitous
If outputs contain reasoning blocks or `<think>` tags, the curation system shall strip them from the target training text to prevent learning post-hoc rationales and maintain compatibility with existing YAML parsers.

### REQ-LLM-TUNE-003 — Ubiquitous
The curation system shall use the 12 programmatic style linters in `russellian-style` to assign a composite scalar preference score $S_{style}$ to generated outputs, aligning with the linter API and weights registry.

### REQ-LLM-TUNE-004 — Ubiquitous
The curation system shall construct a DPO preference dataset of `(prompt, chosen, rejected)` triplets using lexicographical ranking where candidates are first gated by schema validity, completeness, and lack of training leakage before applying style-based ranking.

### REQ-LLM-TUNE-005 — Ubiquitous
The training system shall run fine-tuning on the base model `google/gemma-4-31b-it` (pinned by digest) using 4-bit NF4 double quantization, gradient checkpointing, batch size of 1, and LoRA targeting backbone layers to fit within 32GB VRAM.

### REQ-LLM-TUNE-006 — Ubiquitous
The training system shall execute a two-stage pipeline: (1) SFT Warmup on a verified allow-list of Bertrand Russell Project Gutenberg texts, and (2) DPO preference alignment using the correctness-gated dataset.

### REQ-LLM-TUNE-007 — Ubiquitous
The integration system shall compile the model using `ollama create russellgpt -f Modelfile` with the `ADAPTER` command to load the Safetensors adapter over the pinned local `gemma4:31b` base model (ID: `6316f0629137`).

### REQ-LLM-TUNE-008 — Ubiquitous
The verification system shall run compliance tests validating reasoning block parsing, YAML frontmatter position, JSONL/JSON-LD ledger schemas, exact training leakage, and GPU residency.

---

## 2. Technical Details

### 2.1 Two-Stage Training Details
1.  **Stage 1: SFT Warmup:** Fine-tune `google/gemma-4-31b-it` via Causal LM (1 epoch, LR $1 \times 10^{-5}$) on a compiled corpus of Bertrand Russell's public-domain works. The curation script must verify downloaded files against this checked allow-list:
    *   *The Problems of Philosophy* (ID: 5827)
    *   *The Analysis of Mind* (ID: 25292)
    *   *Mysticism and Logic and Other Essays* (ID: 25447)
    *   *Proposed Roads to Freedom* (ID: 690)
    *   *Our Knowledge of the External World* (ID: 37090)
    *   *Introduction to Mathematical Philosophy* (ID: 41654)
    *   *The Problem of China* (ID: 74747)
    *   *Workflow:* Fetch books via the `scrapling-fetch` skill, strip Gutenberg headers/footers via sentinels, segment into paragraph blocks (~200–500 words), and pack tokens to 4,096 boundaries.
2.  **Stage 2: DPO Alignment:** Train SFT-warmed weights using `trl.DPOTrainer` on prompt triplets generated at temperature $T=0.7$ and ranked by correctness-first gates (1 epoch, LR $5 \times 10^{-6}$, $\beta=0.06$). Reference logprobs are calculated by disabling the adapter to save memory.

### 2.2 PEFT & Quantization Configuration
- **Base Model:** `google/gemma-4-31b-it` (must match the architecture of `gemma4:31b` ID: `6316f0629137`)
- **LoRA configuration:**
  - `r`: 64
  - `lora_alpha`: 128
  - `lora_dropout`: 0.05
  - `target_modules`: `["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]` (suffix-only target modules to prevent PEFT matching failures; verified via preflight parameter count check)
- **Trainer:** Hugging Face `trl.DPOTrainer` with context length capped at 4,096 tokens.

### 2.3 Ollama Modelfile
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

