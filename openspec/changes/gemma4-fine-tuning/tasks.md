# Tasks

## 1. Data Preparation
- [ ] 1.1 Create dataset curation script `curate_dataset.py` in `llm-infra/scripts/` (REQ-LLM-TUNE-001)
- [ ] 1.2 Implement prompt reconstruction by mapping outlines, prompts, and completed output pages (REQ-LLM-TUNE-001)
- [ ] 1.3 Add logic to synthesize and inject gold-standard `<think>` logs for historical runs (REQ-LLM-TUNE-002)
- [ ] 1.4 Export formatted training data to `dataset.jsonl` (REQ-LLM-TUNE-001)

## 2. Model Training Configuration
- [ ] 2.1 Create training execution script `train_adapter.py` (REQ-LLM-TUNE-003)
- [ ] 2.2 Configure 4-bit BitsAndBytes quantization loader (REQ-LLM-TUNE-003)
- [ ] 2.3 Implement LoRA configuration targeting all projection layers with $r=16$ (REQ-LLM-TUNE-003)
- [ ] 2.4 Enable gradient checkpointing and sequence length optimization (REQ-LLM-TUNE-003)
- [ ] 2.5 Add pre-training GPU hooks to unload active Ollama inference instances (REQ-LLM-TUNE-003)

## 3. Ollama Integration
- [ ] 3.1 Write the custom Ollama `Modelfile` using the `ADAPTER` command (REQ-LLM-TUNE-004)
- [ ] 3.2 Set parameter configs for context window (`num_ctx 8192`) and temperature (REQ-LLM-TUNE-004)
- [ ] 3.3 Add default system prompts mapping to target task instructions (REQ-LLM-TUNE-004)
- [ ] 3.4 Modify default model configurations in `adapter.py` to target the custom `gemma4-book` model (REQ-LLM-TUNE-004)

## 4. Verification & Testing
- [ ] 4.1 Write verification test script `verify_finetune.py` (REQ-LLM-TUNE-005)
- [ ] 4.2 Validate output reasoning block parsing and YAML format gates (REQ-LLM-TUNE-005)
- [ ] 4.3 Measure warm inference metrics on RTX 5090 to ensure zero CPU regression (REQ-LLM-TUNE-005)
