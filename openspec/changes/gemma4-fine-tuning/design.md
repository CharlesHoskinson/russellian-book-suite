# Design: Custom Gemma 4 31B Fine-Tuning for Cardano Governance Book Skills

This document describes the technical implementation plan for Curating the dataset, Fine-Tuning the model, Integrating it into Ollama, and Verifying output compliance.

## 1. Requirements (EARS Format)

### REQ-LLM-TUNE-001 — Ubiquitous
The system shall curate a dataset of instruction-response pairs by mapping inputs (prompts, outline contracts) and outputs (final markdown reports, reviews, ledgers) from the workspace history.

### REQ-LLM-TUNE-002 — Ubiquitous
When curating reviews and chapter drafts that lack reasoning logs, the curation system shall generate and inject gold-standard step-by-step reasoning logs within `<think>...</think>` tags to teach the model to reason.

### REQ-LLM-TUNE-003 — Ubiquitous
The training system shall run fine-tuning on the base model `google/gemma-2-27b-it` using 4-bit quantization, gradient checkpointing, and LoRA targeting projection layers to fit within 32GB VRAM.

### REQ-LLM-TUNE-004 — Ubiquitous
The integration system shall use the Ollama `Modelfile` syntax with the `ADAPTER` command to dynamically load the Safetensors adapter over the local `gemma4:31b` base model.

### REQ-LLM-TUNE-005 — Ubiquitous
The verification system shall run a mock chapter review using the custom model, validating that the output starts with `<think>` tags, finishes with valid YAML frontmatter, and completes without timeouts.

---

## 2. Technical Details

### 2.1 Quantization & PEFT parameters
- **Base Model:** `google/gemma-2-27b-it`
- **LoRA configuration:**
  - `r`: 16
  - `lora_alpha`: 32
  - `lora_dropout`: 0.05
  - `target_modules`: `["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]`
- **Trainer:** Hugging Face `SFTTrainer` with sequence length capped at 4,096.

### 2.2 Ollama Modelfile
- Model name: `gemma4-book`
- Config details:
  ```dockerfile
  FROM gemma4:31b
  ADAPTER ./models/gemma4-book-adapter
  PARAMETER num_ctx 8192
  PARAMETER temperature 0.4
  PARAMETER stop "<|im_end|>"
  SYSTEM "You are the custom-tuned Gemma 4 31B model for the Cardano Governance book suite..."
  ```
