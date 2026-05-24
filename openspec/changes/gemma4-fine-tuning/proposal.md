# Proposal: Custom Gemma 4 31B Fine-Tuning for Cardano Governance Book Skills

## Intent
Align the local LLM dispatch path (`llm-infra`) with the high reasoning and quality standards of the Claude subagent dispatch path. By training a custom `russellgpt` model (**RussellGPT**) using QLoRA fine-tuning on our local RTX 5090 GPU, we will improve the model's adherence to the Russellian academic style, ensure strict format validation (like YAML frontmatter and JSON-LD ledgers), reduce the input context footprint by hardcoding persona rules, and eliminate empty response and timeout errors.

## Scope
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

## Approach
A Python script crawls the active workspace to build a training dataset, mapping task prefixes (e.g. `[TASK: ChapterReview]`) to prompts and outputs. A training wrapper script unloads Ollama models and fine-tunes the base model in 4-bit precision using native Windows PyTorch + transformers + peft + trl. The resulting LoRA adapter is loaded directly over `gemma4:31b` via an Ollama Modelfile configuration, and verified against warm latency benchmarks and format gates.
