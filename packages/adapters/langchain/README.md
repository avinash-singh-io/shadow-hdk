# shadow-hdk-adapters-langchain

One `ModelPort`, every provider LangChain integrates:

```python
LangChainModel("openai:gpt-…")
LangChainModel("anthropic:claude-…")
LangChainModel("ollama:llama3.1")
LangChainModel("openai:deepseek-ai/DeepSeek-V4-Flash:deepinfra",
               base_url="https://router.huggingface.co/v1", api_key=…)
```

Providers are optional extras, so the base install pulls no vendor SDK. We write a direct adapter
only where LangChain has nothing — ACP is the case, and it is Phase 4.

**Unknown is `None`, never `0`.** A provider that will not report what a call cost says so, and the
meter stops claiming to know the total rather than inventing a zero.
