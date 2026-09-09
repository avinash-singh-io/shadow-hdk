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
