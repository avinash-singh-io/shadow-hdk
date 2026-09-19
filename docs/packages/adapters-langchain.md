# `shadow_hdk.adapters.langchain`

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

## Any inference provider — the OpenAI-compatible path

Most hosts speak OpenAI's chat API. `LangChainModel("openai:<model>", base_url=…, api_key=…)`
reaches every one of them; the key comes from an environment variable the *product* reads (D41:
the kit asks, never reads a credential itself). The table is what a host needs, nothing more:

| host | `base_url` | model spelling |
|---|---|---|
| OpenAI | *(default)* | `openai:gpt-…` |
| HuggingFace Inference Providers | `https://router.huggingface.co/v1` | `openai:<org>/<model>:<provider>` |
| OpenRouter | `https://openrouter.ai/api/v1` | `openai:<vendor>/<model>` |
| Together AI | `https://api.together.xyz/v1` | `openai:<org>/<model>` |
| Groq | `https://api.groq.com/openai/v1` | `openai:<model>` |
| vLLM (self-hosted) | `http://<host>:8000/v1` | `openai:<model as served>` |
| LM Studio (local) | `http://localhost:1234/v1` | `openai:<model as loaded>` |
| Ollama (local) | *(its own integration)* | `ollama:<model>` |
| Anthropic | *(its own integration)* | `anthropic:claude-…` |

Nothing else in the kit knows which of these is in use: the record, the meter, governance, the
environment and the wire see a `ModelPort`. What the provider reports — tokens, and since 0.34
what its cache did (`input_token_details.cache_read` / `cache_creation`) — comes through the
translation; what it does not report is `None`.

## The desktop: a local model beside a subscription CLI

On a laptop the two ports sit side by side, and a product chooses per thread:

```python
from shadow_hdk.adapters.langchain import LangChainModel
from shadow_hdk.providers import ready
from shadow_hdk.serve import a_thread

# inference by a local model — the kit's own loop runs it (ModelAgent, D98)
async with a_thread(root, model=LangChainModel("ollama:llama3.1")) as thread: ...

# agency by whichever coding CLI is signed in — the loop is the CLI's (D43)
found = await ready()               # or ready("codex"); raises NoProvider naming what would fix it
async with a_thread(root) as thread: ...
```

Both are one `Thread`: the same record, the same modes, the same questions and spend. Which key,
which endpoint, which CLI is the product's configuration; the kit's substrate is the same.
