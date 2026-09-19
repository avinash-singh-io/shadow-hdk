---
type: Phase
status: complete
tags: [usage, cache-tokens, session-gone, failure, behaviour, codex, claude-code, attributes, judgement, modes, contained, web, ci, python-3.14, invariants, providers]
deps: [phase-44-tools-as-code]
---

# Phase 45 — truth both ways

## Goal

Everything a product asked the kit for on 2026-09-19 that survived the admission rule — *would a
second, different host use it unchanged, and does it belong to a port or vocabulary the kit
owns?* — built generically, and the phase that first runs under the owner's standing rule that the
kit is a substrate: primitives any product composes, never a feature for one.

The items have one shape, which names the phase. **The kit tells a host the truth about its
provider** — what a turn really cost (cache tokens, ENH-023); why a turn really failed (a typed
`session_gone`, ENH-024); that a second CLI honours the behaviour a mode asked for (Codex `model`
and `effort`, ENH-028, measured). **And a host tells the kit its truth** — the words a judgement is
made by can change after a thread opened (per-turn `attributes`, ENH-037). One decision is settled
rather than patched: a web read from the serving process under a confined mode (ENH-038) — the
vocabulary stands, the ceiling is right, and the composable door is a mode, not a re-vouched
effect. Underneath: the Python matrix the code already passes (ENH-032, D132), the vendor-name
invariant that turns "a provider is a file" from discipline into a failing test, and the owed
Claude Code half of Phase 36's live proof.

## Decisions settled in this phase

Recorded in `history.md` as they are made; listed in `specs/decisions/index.md`.

- **D138 — A web read from the serving process, under the shipped modes: `workspace-write`
  hides it, `read-only` allows it, `ask` asks — and the door is `ask` plus an `allow` rule.**
  The battery's `contained = false` is true and stays. `workspace-write`, the silent writing
  mode, hides an uncontained reach (a reach beside writes is an egress channel). `read-only`
  allows it, as its documented definition says — look, and look at the web; it writes nothing a
  reach could carry out, and a read-only policy must work over any environment, a `full` one
  included, where nothing is proven contained. `ask` asks before it (before 0.34 it refused
  outright, which left a served product no door but re-vouching the effect): "every write, run or
  delete inside the workspace is asked about" is its definition and Claude Code's default. A row
  `component = "web_search", decision = "allow", mode = "ask"` then stands in for the person. No
  vocabulary change. *(Amended in G4 — the first draft narrowed `read-only`; the architecture and
  the suite said no.)*
- **D139 — A turn's failure is typed on the record and raised typed.** `TurnRecord.failure`
  names why a turn failed from a small vocabulary (`session_gone` first); `Thread.turn` raises
  `SessionGone(thread_id, session_id, provider)` at the end of the stream; the wire's error kind
  `session_gone` carries both ids. How a CLI says it is a provider-file value
  (`session_gone_matches`), never code.
- **D140 — A turn's words are the turn's.** `attributes=` on `turn` merges over the record's for
  that turn's judgements and is never written back; `resume(attributes=)` replaces the record's
  and the record says so. Reserved names refused, as at open.
- **D141 — Unknown, never zero, for cache tokens.** `Usage.cache_read_tokens` /
  `cache_write_tokens` are `None` where a provider does not report them; `Spent` counts them and
  `unmetered` covers their absence as it covers the others'.

## Scope

**In:**

- ENH-023 — `Usage.cache_read_tokens`, `Usage.cache_write_tokens`; `Dialect.cache_read_tokens_at`
  / `cache_write_tokens_at`; `codex.toml` (`usage.cached_input_tokens`,
  `usage.cache_write_input_tokens`, measured 2026-09-11) and `claude-code.toml`
  (`usage.cache_read_input_tokens`, `usage.cache_creation_input_tokens`, measured 2026-09-20);
  LangChain's `usage_metadata.input_token_details` (`cache_read`, `cache_creation`); `Spent`
  counting them; the meter; the record's JSON; the published contracts and the TypeScript types.
- ENH-024 — `Turn.session_gone`; `Dialect.session_gone_matches` and `failed_text_at` for Claude
  Code (`errors`, a list); the JSONL session drains stderr (Codex says *no rollout found* there —
  and an undrained pipe is a deadlock waiting for a chatty CLI, BUG-059); `TurnRecord.failure`;
  `SessionGone`; the wire kind; the TypeScript client; `docs/for-a-product.md` §8 rewritten.
- ENH-028 — `BehaviourArg.template` so a flag that takes `key=value` can be said in data
  (`-c model_reasoning_effort="{value}"`); `codex.toml` maps `model` and `effort`; measured live on
  Codex 0.154.0; `unmapped_behaviour` shrinks accordingly.
- ENH-037 — `Conversation.turn(attributes=)`, `Thread.turn(attributes=)`,
  `Thread.resume(attributes=)`; `turn/start {attributes}`, `thread/resume {attributes}`; the TS
  client.
- ENH-038 — D138: `ask` asks before an uncontained reach; a test over the four shipped policies
  and the `allow`-rule door; the modes guide says how; a migration note.
- ENH-032 — the `check` job over 3.12 · 3.13 · 3.14; `.python-version` 3.14; the classifiers;
  `requires-python` unchanged.
- The vendor-name invariant: no `claude`, `codex`, `openai`, `anthropic`, `ollama`, `opencode`
  in the *code* of `kernel/` and `runtime/` (docstrings and comments excepted).
- Phase 36's live proof on Claude Code (`test_a_cli_plans_through_the_socket.py` run with the
  Claude Code provider; the measurement recorded).
- Docs: the two ports and one surface stated plainly in `docs/for-a-product.md`; the
  OpenAI-compatible endpoints table (OpenRouter, Together, Groq, vLLM, LM Studio, HuggingFace)
  and a local-desktop example in `docs/packages/adapters-langchain.md`; the 0.34 note under `docs/migrations/`.

**Out:** ENH-039 (a `fetch` battery — waits on D138's mode being used), ENH-027 (OpenCode, the
owner's exclusion), ENH-021 (the demo's re-pin), TD-013, the egress proxy (D137), anything only
one product would use.

## Deliverables

| Deliverable | Verification |
|---|---|
| cache tokens end to end | the dialect tests on recorded streams; the LangChain translation test; `Spent` arithmetic; contracts and TS regenerated without drift |
| `session_gone` typed on the record, raised, on the wire | a session double saying the measured text; the wire's error kind; the record's `failure` |
| Codex behaviour mapped | the argv test from the provider file; the live measurement (`-m live`) with its output recorded |
| per-turn attributes | a judgement seeing the turn's words and not the next turn's; resume replacing the record's; the wire |
| D138 | the shipped `read-only` ceiling; a product-defined mode asking for an uncontained reach; the migration note |
| the Python matrix | the `check` job green on all three |
| the vendor-name invariant | `tests/invariants` green and a mutation caught |
| the live proofs | `uv run pytest -m live tests/test_a_cli_plans_through_the_socket.py` on Claude Code, and the Codex behaviour measurement, both recorded in the history |

## Acceptance criteria

1. A Claude Code and a Codex turn's `Spent` carry cache read and write tokens from the measured
   fields; a LangChain model with `input_token_details` reports them; a provider without them
   leaves `None` on `Usage` and `unmetered` says so on `Spent`.
2. A thread resumed on a session id its CLI no longer has ends the turn `failed` with
   `failure == "session_gone"`, raises `SessionGone` in process, and answers
   `error.data.kind == "session_gone"` with `thread_id` and `session_id` on the wire — for both
   measured CLIs, from their provider files alone.
3. `Thread.open(behaviour=Behaviour(model=…, effort=…))` on Codex launches with `-m <model>` and
   `-c model_reasoning_effort="<effort>"`; `unmapped_behaviour` names neither; measured live.
4. A rule scoped `attribute:value` given on `turn(attributes=)` decides that turn's acts and not
   the next turn's; `resume(attributes=)` changes what later turns are judged by and the record
   shows the new words.
5. Under shipped `workspace-write` an uncontained reach is refused, under `read-only` allowed,
   under `ask` asked — and allowed by one `allow` rule; the `ddgs` battery's file is unchanged.
6. CI's `check` job runs on 3.12, 3.13 and 3.14; the dev environment is 3.14.
7. The invariant fails on a vendor name in runtime code (mutation shown) and passes on the tree.
8. The four-zero gate on 3.12 and 3.14; protocol 3 unchanged (every addition a field or a kind);
   the count does not drop.
