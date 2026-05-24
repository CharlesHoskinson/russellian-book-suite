# Tasks

## 1. Data Preparation
- [ ] 1.1 Create dataset curation script `curate_dataset.py` in `llm-infra/scripts/` (REQ-LLM-TUNE-001)
- [ ] 1.2 Implement prompt reconstruction by mapping outline contracts and output pages without synthetic `<think>` blocks (REQ-LLM-TUNE-002)
- [ ] 1.3 Add Gutenberg downloader and metadata preprocessor using `scrapling-fetch` (REQ-LLM-TUNE-006)
- [ ] 1.4 Implement strict eBook allow-list validations (verify ID, title, author, and hashes on download for IDs 5827, 25292, 25447, 690, 37090, 41654, 74747) (REQ-LLM-TUNE-006)
- [ ] 1.5 Implement `russellian-style` linter wrapper to calculate composite $S_{style}$ metric (REQ-LLM-TUNE-003)
- [ ] 1.6 Implement lexicographical ranking for DPO candidates: gate first by schema validity, completeness, and non-leakage, then apply style ranking (REQ-LLM-TUNE-004)
- [ ] 1.7 Add leakage checks across prompts, outputs, and ledgers; export train/val/test/acceptance split manifest to `dataset_dpo.jsonl` (REQ-LLM-TUNE-004)

## 2. Model Training Configuration
- [ ] 2.1 Create training execution script `train_adapter.py` targeting base model `google/gemma-4-31b-it` (REQ-LLM-TUNE-005)
- [ ] 2.2 Implement GPU/CUDA preflight assertions (CUDA availability, device capability, PyTorch CUDA build, bitsandbytes 4-bit load, and bf16 support) (REQ-LLM-TUNE-005)
- [ ] 2.3 Implement pre-training VRAM eviction hooks (unload active Ollama models, poll `/api/ps`, assert free VRAM with `nvidia-smi`) (REQ-LLM-TUNE-005)
- [ ] 2.4 Implement `--dry-run-memory-profile` preflight (asserts sequence length 4096 fits under 32GB VRAM using NF4 quant, gradient checkpointing, and `model_ref=None` sharing weights) (REQ-LLM-TUNE-005)
- [ ] 2.5 Run SFT Warmup stage on Project Gutenberg Bertrand Russell corpus (REQ-LLM-TUNE-006)
- [ ] 2.6 Run DPOTrainer stage utilizing the correctness-gated dataset (REQ-LLM-TUNE-006)
- [ ] 2.7 Configure high-rank LoRA parameters ($r=64$, $\alpha=128$, suffix-only target modules) and assert non-zero parameter counts (REQ-LLM-TUNE-005)

## 3. Ollama Integration & Deployment
- [ ] 3.1 Write the custom Ollama `Modelfile` linking base `gemma4:31b` (ID: `6316f0629137`) and target adapter `./models/russellgpt-adapter/` (REQ-LLM-TUNE-007)
- [ ] 3.2 Set parameter configs for context window (`num_ctx 4096`) and temperature (REQ-LLM-TUNE-007)
- [ ] 3.3 Add default system prompts mapping to target task instructions (REQ-LLM-TUNE-007)
- [ ] 3.4 Deploy model locally using `ollama create russellgpt -f Modelfile` (REQ-LLM-TUNE-007)
- [ ] 3.5 Update central configuration to select model `russellgpt` by default and route all Ollama endpoints (REQ-LLM-TUNE-007)

## 4. Verification & Compliance Gating
- [ ] 4.1 Write verification test script `verify_finetune.py` with caching disabled (REQ-LLM-TUNE-008)
- [ ] 4.2 Implement pre-strip reasoning block filter in `adapter.py` to prevent `<think>` blocks from polluting YAML/JSONL parsers (REQ-LLM-TUNE-002)
- [ ] 4.3 Validate parser compatibility with existing book-review and report tooling (REQ-LLM-TUNE-008)
- [ ] 4.4 Add negative test cases (malformed think blocks, invalid YAML, invalid JSONL schema) and verify compiler fails (REQ-LLM-TUNE-008)
- [ ] 4.5 Run residency checks (`ollama ps`) to verify `russellgpt` is 100% resident in GPU VRAM and measure warm tokens/sec (REQ-LLM-TUNE-008)
