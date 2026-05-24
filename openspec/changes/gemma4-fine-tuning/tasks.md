# Tasks

## 1. Data Preparation
- [ ] 1.1 Create dataset curation script `curate_dataset.py` in `llm-infra/scripts/` (REQ-LLM-TUNE-001)
- [ ] 1.2 Implement prompt reconstruction by mapping outline contracts and output pages (REQ-LLM-TUNE-001)
- [ ] 1.3 Add logic to synthesize and inject gold-standard `<think>` logs for historical runs (REQ-LLM-TUNE-002)
- [ ] 1.4 Import `russellian-style` linters to calculate the composite preference score $S_{style}$ (REQ-LLM-TUNE-003)
- [ ] 1.5 Generate candidate pool, rank outputs, and build DPO preference triplets (REQ-LLM-TUNE-004)
- [ ] 1.6 Export formatted training data to `dataset_dpo.jsonl` (REQ-LLM-TUNE-004)
- [ ] 1.7 Add Gutenberg downloader and preprocessor to fetch and clean Bertrand Russell's corpus of 7 books (REQ-LLM-TUNE-006)

## 2. Model Training Configuration
- [ ] 2.1 Create training execution script `train_adapter.py` (REQ-LLM-TUNE-005)
- [ ] 2.2 Configure 4-bit BitsAndBytes quantization loader (REQ-LLM-TUNE-005)
- [ ] 2.3 Implement SFT Warmup stage on Project Gutenberg Bertrand Russell corpus (REQ-LLM-TUNE-006)
- [ ] 2.4 Implement DPOTrainer stage utilizing the linter-graded dataset (REQ-LLM-TUNE-006)
- [ ] 2.5 Configure high-rank LoRA parameters ($r=64$, $\alpha=128$, custom target regex) (REQ-LLM-TUNE-005)
- [ ] 2.6 Enable gradient checkpointing and memory-mapped optimizers (REQ-LLM-TUNE-005)
- [ ] 2.7 Add pre-training GPU hooks to unload active Ollama inference instances (REQ-LLM-TUNE-005)

## 3. Ollama Integration
- [ ] 3.1 Write the custom Ollama `Modelfile` using the `ADAPTER` command (REQ-LLM-TUNE-007)
- [ ] 3.2 Set parameter configs for context window (`num_ctx 8192`) and temperature (REQ-LLM-TUNE-007)
- [ ] 3.3 Add default system prompts mapping to target task instructions (REQ-LLM-TUNE-007)
- [ ] 3.4 Modify default model configurations in `adapter.py` to target the custom `gemma4-book` model (REQ-LLM-TUNE-007)

## 4. Verification & Testing
- [ ] 4.1 Write verification test script `verify_finetune.py` (REQ-LLM-TUNE-008)
- [ ] 4.2 Validate output reasoning block parsing and YAML format gates (REQ-LLM-TUNE-008)
- [ ] 4.3 Measure warm inference metrics on RTX 5090 to ensure zero CPU regression (REQ-LLM-TUNE-008)
