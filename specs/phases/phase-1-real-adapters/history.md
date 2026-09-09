---
type: History
phase: 1-real-adapters
---

# Phase 1 — history

Append-only. Newest at the bottom.

| Entry type | Meaning |
|---|---|
| `[DECISION]` | a choice made, with what it rules out |
| `[ARCH_CHANGE]` | a structural change to the code or the specs |
| `[DISCOVERY]` | something the code or a library turned out to be |
| `[CORRECTION]` | a previous entry or plan proven wrong |

---

### [ARCH_CHANGE] 2026-09-10 — branched from Phase 0, because nothing merges
Topics: branches, chain
Affects-specs: specs/phases/phase-1-real-adapters/overview.md

`phase-1-real-adapters` is cut from `phase-0-the-runtime` at `0e39c70`, not from `staging`. Nothing
merges without the owner, so the chain of phase branches is what carries the code forward: Phase 2
will branch from this one, and so on until the owner lands the lot. Each phase's `history.md` records
its parent, so the chain is readable without `git log --graph`.

### [DECISION] 2026-09-10 — what this machine can really test, and what it must not
Topics: providers, ollama, api-keys, live-tests

Measured before planning rather than assumed:

| | |
|---|---|
| `ollama` binary | installed, **not serving** — started locally for this phase |
| a model on disk | **`gemma4`**, already pulled — so a live check costs no download |
| `langchain-core` | 1.6.2, present transitively through langgraph |
| `langchain` | **absent** — `init_chat_model` lives there, so the adapter depends on it |
| `mcp` SDK | **absent** — the adapter depends on it |
| `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` | **both set in the environment** |

**The keys are set and the suite will not use them.** Spending someone's money is not a decision a
test suite gets to make, and the owner is asleep. Live tests run against **local Ollama only**;
OpenAI, Anthropic and HuggingFace are exercised through a fake `BaseChatModel` that satisfies
langchain's own interface — which is the right test anyway, because what is being tested is *our
translation*, not their servers.

Nothing is downloaded either. A model that is not already on disk is a multi-gigabyte fetch on
someone else's machine overnight, so `gemma4` is what the live check uses because `gemma4` is what
is there.

### [DECISION] 2026-09-10 — D14: a port may grow a method, with a default
Topics: ports, streaming, contracts, d9, d14
Affects-specs: specs/architecture/decisions.md

`09` §3 says a **port** is added with a refuse-not-crash default. It does not say what happens when
an existing port grows a **method**, which is what `stream` is. The same rule, one level down:

> A method added to a port ships with a default implementation on a mixin the adapter can inherit.
> An adapter that ignores it keeps working; one that can do better overrides it.

For `stream`, the default calls `complete` and yields a single chunk carrying the whole response.
That is honest — a non-streaming provider genuinely produces its answer all at once — and it means
the five adapters written in Phase 0 need no edit.

By D9 this is still a **contract change**: every package takes a minor bump together, and it earns a
row under *Pins* on the board, because the join with the product lane is the only place two lanes
can break each other.

---

### [CORRECTION] 2026-09-10 — the owner supplied a HuggingFace token; live checks moved off Ollama
Topics: providers, huggingface, secrets, live-tests

The plan said local Ollama. Mid-phase the owner supplied `INTENT_HF_TOKEN` and
`deepseek-ai/DeepSeek-V4-Flash:deepinfra`, and asked for HuggingFace instead. Done — and it is the
better test anyway: HF Inference Providers is **OpenAI-compatible**, so the live path now exercises
the same code as OpenAI, Together, Groq, vLLM and most self-hosted servers, rather than one vendor's
own client.

**The token is not in this repository and will not be.** It lives in a `0600` file in the session
scratchpad, outside the worktree; code and specs name only the *variable*. A sweep for
`hf_[A-Za-z0-9]{20,}` runs over everything before each commit of this phase.

The Ollama server this session started was stopped; nothing was downloaded.

**Live tests are deselected by default** — `addopts = "-m 'not live'"` — because they cost money and
a suite should not decide to spend someone's. `uv run pytest -m live` opts in. CI has no token and
runs the fake path.

### [ARCH_CHANGE] 2026-09-10 — Groups 0 and 1: the port grew a method, and one adapter reaches every provider
Topics: streaming, modelport, langchain, usage, pricing, g0, g1

**D14 in practice.** `ModelPort.stream` ships with a default on the protocol body: call `complete`,
yield the whole answer as one chunk. Every adapter written in Phase 0 needed no edit, and the
default is *honest rather than pretend* — a provider that answers all at once really does produce
one chunk, and chopping it into fake deltas would make a run look like it streamed when it did not.
By D9 this is a contract change, so all five packages moved to **0.2.0** together.

**One adapter, every provider.** `LangChainModel` over `init_chat_model`, with vendors as optional
extras so the base install pulls no SDK. What the file actually *is* is a translation — messages,
tool schemas, tool calls, usage, both ways — and that is what the fake tests exercise.

**Tokens are the provider's fact; money is the product's.** No provider reports cents, and the
harness holds no rate card: a rate card is policy about *this tenant's contract*, which `09` §8 puts
on the other side of the boundary. So `cost_cents` is `None` — *unknown* — unless a host supplies a
`price` callback, and the meter then says it cannot total rather than adding zero. Asserted on the
real wire: HF reports `input_tokens`/`output_tokens` and no price at all.

**Measured, live, against `deepseek-ai/DeepSeek-V4-Flash:deepinfra`:** text returns; usage reports
10 input / 4 output tokens and `cost_cents: None`; a tool call round-trips with its id and arguments;
a stream arrives and concatenates to the answer. 4 live tests, 4 passed.

### [DISCOVERY] 2026-09-10 — a real stream is mostly empty frames, and a test asserted the provider
Topics: streaming, live-tests, mutation-check

The first live streaming test asserted `len(chunks) > 2` and failed. **The measurement said the
assertion was wrong, not the code**: over this route the model sends five frames of which exactly
one carries words. So the faithful translation is one text chunk plus a final one, and a test that
demands a provider stream token-by-token is testing somebody else's server. Rewritten to assert what
the *adapter* guarantees; multi-chunk streaming is proven against the fake, where the deltas are
ours to choose.

The empty frames are dropped rather than passed on — four empty deltas in the record would make a
run look like it streamed. A mutation that stopped filtering them **left the suite green**, because
the fake had been too tidy to produce any; the only test covering it was the live one, which a
normal run deselects. That is the fourth vacuous test a mutation check has found, and the fix was
again a better test: a fake that sends what the real provider sends.

### [DISCOVERY] 2026-09-10 — a stale `__pycache__` made a mutation look like a defect
Topics: mutation-check, tooling

After restoring a mutated file, the suite still failed and the source on disk was demonstrably
correct — `inspect.getsource` at run time showed the right code. Inserting a `print` made it pass,
which is the signature of a stale bytecode cache rather than a bug: the restore-by-copy and the
`.pyc` disagreed. **The mutation harness now clears `__pycache__` after every restore.** Half an
hour spent because a tool lied, and worth the entry so the next occurrence costs a minute.

Also fixed while here: `aclosing` around the provider's generator, so the HTTP stream under it
closes the moment we stop reading. It removed a real teardown error from httpcore2 that appeared on
every live streaming call.

---

### [ARCH_CHANGE] 2026-09-10 — Group 3: a mode is a ceiling and an ask line
Topics: modes, governance, layering, meet, g3

`Mode(name, ceiling, ask_above)` and `ModeGovernance(modes, default, key)`. Two modes, ten, or one
called `auto` is a different **mapping**, not different code — the runtime knows no mode names, and
this adapter knows only the ones a product hands it. The four in the tests (`read`, `build`, `act`,
`auto`) are examples, not a vocabulary the adapter imposes.

**An unknown mode refuses and says which name it did not recognise.** The dangerous failure here is
silent widening: a typo in a mode name resolving to whatever the default happens to be. A mutation
that made it fall back to the default fails the suite.

**`ask_above=None` means never ask** — a thing a product may legitimately want, and the adapter will
not second-guess it, but it has to be *said* rather than inherited from a neighbouring mode.

**A layer can only narrow, and that is arithmetic.** `layer(base, over)` is `EffectProfile.meet`,
which the kernel already property-tests as a greatest lower bound, so "a team may tighten what it
was given and never loosen it" is not a review comment. A hypothesis property asserts it over
arbitrary profiles, and a mutation that takes the layer's ceiling instead of the meet fails.

When a step is asked about, the question **names the field that crossed the line** — reads more than
usual, reaches outside, is irreversible — so a person being asked is told what they are answering.

Five mutations, all failing. The mutation harness now clears `__pycache__` after each restore.
