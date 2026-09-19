---
type: History
status: in-progress
---

# phase-45-truth-both-ways — History

> Append-only. Entry types: `[DECISION]` `[SCOPE_CHANGE]` `[DISCOVERY]` `[FEATURE]` `[ARCH_CHANGE]` `[EVALUATOR]` `[NOTE]`.

### [NOTE] 2026-09-20 — Phase 45 planned: the rest of what the product asked for, under the substrate rule
Topics: admission, substrate, usage, session-gone, behaviour, attributes, modes, ci
Affects-phases: phase-45-truth-both-ways
Affects-specs: none
Detail: Six rows admitted under the rule *would a second, different host use it unchanged, and does it belong to a port or vocabulary the kit owns?* — ENH-023, ENH-024, ENH-028, ENH-032, ENH-037, ENH-038 — plus the owed Claude Code half of Phase 36's live proof and one new invariant. ENH-039 (a fetch battery) waits on D138's door being used; ENH-027 stays excluded by the owner's word. The owner confirmed 2026-09-20 that `ModelPort` (inference) and `AgentPort` (agency) stay two ports under one surface (D98) and that the kit is a substrate — recorded as a standing rule.

---

### [DECISION] 2026-09-20 — D138: a reach from the serving process is an egress channel; the confined ceilings say contained, and the door is a mode
Topics: modes, contained, web, egress, read-only, ceiling
Affects-phases: phase-45-truth-both-ways
Affects-specs: architecture/adapters.md#the-modes-adapter
Detail: The `ddgs` battery vouches `web_search` `reaches = true, contained = false` — true, the read runs in the serving process. The shipped `workspace-write` and `ask` ceilings allow a reach only when contained, so it is refused; the product's workaround (re-vouching `contained = true`) is the patchwork the substrate rule forbids. Read against the modes' own environments, the ceilings are *right*: a confined environment proves the network denied for commands, and an in-process reach would carry the workspace out past that proof — an egress channel, which is why Codex disables `network_access` on its workspace-write by default and why D137 names an allowlisted proxy as the field's answer. One inconsistency found on the way: `read-only`'s ceiling said `contained = false`, wider than `workspace-write` on that axis and contradicting its own environment — corrected to `true` (a narrowing of a shipped policy; the migration note says so). The composable door already exists as data: a product mode with ceiling `contained = false` and `ask_above.contained = true` has an uncontained reach *asked* and a contained one allowed — proven by a test and written into the modes guide. No vocabulary change; the battery's file unchanged.

---

### [DECISION] 2026-09-20 — D139: a turn's failure is typed on the record and raised typed
Topics: session-gone, failure, turn-record, refusal, wire, dialect
Affects-phases: phase-45-truth-both-ways
Affects-specs: architecture/runtime.md#the-thread, architecture/wire.md#the-thread-crossed
Detail: A thread resumed on a session id its CLI no longer has ended as an anonymous failed turn; a product could not tell "the resume broke" from "the turn broke" and had to guess whether to fork. Now `TurnRecord.failure` names why a turn failed from a small vocabulary (`session_gone` first — the vocabulary may grow by measured kinds only), `Thread.turn` raises `SessionGone(thread_id, session_id, provider)` when the stream ends so an in-process host catches it, and the wire answers `error.data.kind = "session_gone"` with both ids. How a CLI says it is a provider-file value — `session_gone_matches`, substrings of the failure text or stderr, measured on 2026-09-20 for both CLIs — never a code path. Measured: Claude Code puts it in `result.errors[]` with `is_error: true` and exit 0; Codex puts it on stderr with nothing on stdout, which is how BUG-059 (stderr opened as a pipe and never read) was found.

---

### [DECISION] 2026-09-20 — D140: a turn's words are the turn's
Topics: attributes, judgement, context, resume, thread
Affects-phases: phase-45-truth-both-ways
Affects-specs: architecture/runtime.md#the-thread
Detail: `Thread.open(attributes=)` writes the product's words to the record and every judgement's context (D82); `resume` rebuilt the conversation from the record's alone and `turn` took none, so a fact the product learnt after opening — the workspace, the run in scope — never reached a judgement (ENH-037, measured by the product). `turn(attributes=)` merges the turn's words over the record's for that turn's judgements only and never writes them back; `resume(attributes=)` replaces the record's and the record shows the change. Reserved names (`thread`, `turn`, `mode`) refused as at open. On the wire: `turn/start {attributes}`, `thread/resume {attributes}`, additive on protocol 3.

---

### [DECISION] 2026-09-20 — D141: unknown, never zero, for cache tokens
Topics: usage, cache-tokens, spent, unmetered
Affects-phases: phase-45-truth-both-ways
Affects-specs: architecture/runtime.md#the-thread
Detail: `Usage.cache_read_tokens` and `cache_write_tokens` are `None` where a provider does not report them (10 §5 R2, as for the other fields); `Spent` counts them across turns and `unmetered` says a call reported no tokens at all. A product's "cached" figure is then a measurement or an honest unknown, never a zero that means "the cache did no work". The fields' names are the kit's; each dialect maps its own (`cached_input_tokens`/`cache_write_input_tokens` on Codex; `cache_read_input_tokens`/`cache_creation_input_tokens` on Claude Code; `input_token_details.cache_read`/`cache_creation` in LangChain).

---
