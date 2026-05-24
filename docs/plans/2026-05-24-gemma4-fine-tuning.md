# Plan: Custom Gemma 4 31B Fine-Tuning (RussellGPT)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a local, robust, and cost-free training pipeline to fine-tune `google/gemma-4-31B-it` (styled as **RussellGPT**) and deploy it as a local drop-in replacement for the Claude subagent path.

**Tech Stack:** Python >=3.11, Native Windows PyTorch, `transformers`, `peft`, `trl`, `bitsandbytes`, `ollama` CLI, `pytest`.

**Spec:** `docs/specs/2026-05-24-gemma4-finetuning-design.md` (or OpenSpec `design.md`).

---

## File structure

We will work in both the `llm-infra/` project and the `russellian-book-suite/` repository.

```
C:/governance/llm-infra/
├── Modelfile
├── pyproject.toml
├── scripts/
│   ├── curate_dataset.py
│   ├── train_adapter.py
│   └── verify_finetune.py
├── src/
│   └── llm_infra/
│       ├── adapter.py
│       ├── cache.py
│       └── persona_dispatch.py
└── tests/
    └── test_verify_finetune.py
```

---

### Task 0: Preflight and Environment Verification

**Files:**
- Create: `llm-infra/scripts/preflight_check.py`

- [ ] **Step 1: Write `llm-infra/scripts/preflight_check.py`**
  Verify PyTorch CUDA build, GPU driver, Blackwell/Ada capability, bf16 support, and bitsandbytes 4-bit loading.
  
  ```python
  import sys
  import torch
  
  def run_preflight():
      print("Running PyTorch CUDA preflight checks...")
      if not torch.cuda.is_available():
          print("FAIL: CUDA is not available to PyTorch.")
          sys.exit(1)
      print(f"CUDA Version: {torch.version.cuda}")
      print(f"PyTorch Version: {torch.__version__}")
      device_name = torch.cuda.get_device_name(0)
      print(f"Device Name: {device_name}")
      capability = torch.cuda.get_device_capability(0)
      print(f"Device Capability: {capability}")
      if not (capability[0] >= 8):
          print("WARN: GPU architecture capability is less than Ampere/Ada/Blackwell.")
      
      try:
          import bitsandbytes as bnb
          print(f"bitsandbytes version: {bnb.__version__}")
      except ImportError:
          print("FAIL: bitsandbytes is not installed or importable.")
          sys.exit(1)
          
      print("PASS: Preflight validation successful.")
      sys.exit(0)

  if __name__ == "__main__":
      run_preflight()
  ```

- [ ] **Step 2: Execute Preflight Script**
  ```powershell
  python C:/governance/llm-infra/scripts/preflight_check.py
  ```
  Expected exit code is 0.

---

### Task 1: Dataset Curation Script (`curate_dataset.py`)

**Files:**
- Create: `llm-infra/scripts/curate_dataset.py`

- [ ] **Step 1: Write SFT Curation and Allow-List validation**
  Implement Project Gutenberg downloader using the `scrapling-fetch` wrapper. The allowlist contains the corrected IDs:
  - *The Problems of Philosophy* (ID: 5827)
  - *The Analysis of Mind* (ID: 2529)
  - *Mysticism and Logic and Other Essays* (ID: 25447)
  - *Proposed Roads to Freedom* (ID: 690)
  - *Our Knowledge of the External World* (ID: 37090)
  - *Introduction to Mathematical Philosophy* (ID: 41654)
  - *The Problem of China* (ID: 13940)
  
  Include deterministic start/end regex sentinels to strip Gutenberg headers/footers. Segment text into paragraph chunks (200-500 words) and pack them into continuous sequence blocks of 4096 tokens.

- [ ] **Step 2: Write Correctness-First DPO Candidate Generator**
  Generate $N=4$ candidates per prompt at temperature $T=0.7$. Implement a strict schema linter and duplicate checker to act as the primary correctness gate. Triplets must be generated only from candidates that pass all correctness gates (YAML schema, JSONL context boundaries, leakage checks).

- [ ] **Step 3: Write Linter style scoring ($S_{style}$)**
  Import `russellian-style` style linters from `skill_api.py`. Implement the versioned normalized scoring formula:
  $$S_{style}(c) = - (\text{hedges} + \text{passives} + \text{ai\_vocab} + \text{uniformity\_penalty}) \times 1000 / \text{word\_count} + \text{burstiness}$$
  
  Chosen/Rejected options are chosen from the highest and lowest style scores among the correctness-passed candidates.

- [ ] **Step 4: Execute Curation Dry-Run**
  ```powershell
  python C:/governance/llm-infra/scripts/curate_dataset.py --verify --max-books 1
  ```
  Expected output: Dataset curation completes successfully, writing `dataset_dpo.jsonl` with valid splits and no leakage.

---

### Task 2: Fine-Tuning Pipeline (`train_adapter.py`)

**Files:**
- Create: `llm-infra/scripts/train_adapter.py`

- [ ] **Step 1: Write pre-training Ollama VRAM Eviction hook**
  Queries Ollama's active models via HTTP request `GET http://localhost:11434/api/ps` and unloads any running models by calling `POST http://localhost:11434/api/generate` with `keep_alive: 0` or running `ollama stop <model>`.

- [ ] **Step 2: Write the VRAM Memory Profiler**
  Runs a 100-step dummy forward-backward pass using a context size of 4096 and records peak VRAM usage via `torch.cuda.max_memory_allocated()`. If VRAM usage exceeds 30GB, automatically scale LoRA down to `r=32` and cap context sequence length at 2048.

- [ ] **Step 3: Implement SFT and DPO Training Loop**
  Use `trl.SFTTrainer` and `trl.DPOTrainer` with:
  - Base model: `google/gemma-4-31B-it` (pinned Hugging Face revision: `8d2f7a9341498b3f27de10b50b503d289196b014`).
  - NF4 4-bit quantization with Double Quantization.
  - `per_device_train_batch_size=1`, `gradient_accumulation_steps=8`.
  - `paged_adamw_8bit` optimizer, `use_cache=False`.
  - PEFT configurations: `r=64`, `lora_alpha=128`, `target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]` (suffix-only).
  - DPOTrainer configuration: set `model_ref=None` to share weights and prevent OOM.
  - Assert that `trainable_parameters > 0`.

- [ ] **Step 4: Run Training Smoke Test**
  ```powershell
  python C:/governance/llm-infra/scripts/train_adapter.py --smoke-steps 10
  ```
  Expected output: Runs 10 SFT and 10 DPO steps without OOM or CPU offloading.

---

### Task 3: Ollama Modelfile and Routing Integration

**Files:**
- Create: `llm-infra/Modelfile`
- Modify: `llm-infra/src/llm_infra/adapter.py`
- Modify: `llm-infra/src/llm_infra/persona_dispatch.py`
- Modify: `llm-infra/src/llm_infra/cache.py`

- [ ] **Step 1: Write `llm-infra/Modelfile`**
  ```dockerfile
  FROM gemma4:31b
  ADAPTER ./models/russellgpt-adapter
  PARAMETER num_ctx 4096
  PARAMETER temperature 0.4
  PARAMETER stop "<|im_end|>"
  SYSTEM "You are the custom-tuned Gemma 4 31B model (RussellGPT) for the Cardano Governance book suite..."
  ```

- [ ] **Step 2: Add pre-strip reasoning block filter in `adapter.py`**
  Modify `make_ollama_call` to strip `<think>...</think>` tags using a regex pattern BEFORE returning the final output text.
  
  ```python
  import re
  
  def strip_thinking(text: str) -> str:
      return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
  ```

- [ ] **Step 3: Centralize Model Configuration**
  Update `DEFAULT_MODEL` in `adapter.py` and `run_persona_via_ollama` default `model` parameters to `"russellgpt"`. Support `OLLAMA_MODEL` environment variable overrides.

- [ ] **Step 4: Make DiskCache Adapter-Aware**
  Compute the hashes of:
  - The adapter folder `models/russellgpt-adapter` (using contents of `adapter_model.safetensors` and `adapter_config.json`).
  - The `Modelfile`.
  - The Ollama model digest via `GET http://localhost:11434/api/show`.
  
  Inject these hash variables directly into the `DiskCache` cache key hashing function.

---

### Task 4: Automated Verification Gate (`verify_finetune.py`)

**Files:**
- Create: `llm-infra/scripts/verify_finetune.py`
- Create: `llm-infra/tests/test_verify_finetune.py`

- [ ] **Step 1: Write the Base Equivalence Check**
  Verify that `gemma4:31b` matches the ID `6316f0629137` / digest `sha256:6316f0629137d6e4cc7b9f87451006e98716b14249a5b6c8ba876bf7d848ccf4` and parameter attributes match `31.3B`.

- [ ] **Step 2: Write Positive Schema Validators**
  Bypass disk cache. Query `russellgpt` to review a draft, asserting that the output parses as valid YAML frontmatter and conforms to the ledger JSONL/JSON-LD schemas.

- [ ] **Step 3: Write Negative Validation Fixtures**
  Inject failing inputs: malformed think blocks, nested think blocks, invalid YAML format. Assert that the verification suite throws validation exceptions.

- [ ] **Step 4: Write Leakage checks and Residency test**
  Verify that test prompts are absent from the training partition. Run `ollama ps` to assert `russellgpt` is 100% resident in GPU VRAM (0% CPU offload) and that warm latency tokens/sec matches expectations.

- [ ] **Step 5: Run Full Verification Suite**
  ```powershell
  python C:/governance/llm-infra/scripts/verify_finetune.py --model russellgpt
  ```
  Expected output: All positive, negative, base equivalence, VRAM residency, and leakage assertions pass successfully.
