# Expansion

Skipped this session. The Python audit pipeline calls anthropic.Anthropic() and requires ANTHROPIC_API_KEY in the environment of the audit subprocess. This session generated the sample texts directly (Claude as LLM in conversation) rather than via the live_llm wrapper.

Follow-up: refactor the live_llm boundary so the audit can be driven by an in-conversation Claude instead of a separate API call. Likely shape: an MCP server that proxies messages.create through the harness, or a stage-pause pattern where the audit writes the prompt to disk and waits for Claude to fill the response file.
