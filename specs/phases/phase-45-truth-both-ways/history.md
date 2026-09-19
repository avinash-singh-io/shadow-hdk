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

### [DISCOVERY] 2026-09-20 — G2: two defects under the failure path — BUG-059 and BUG-060
Topics: session-gone, stderr, failure, turn-record, jsonl
Affects-phases: phase-45-truth-both-ways
Affects-specs: none
Detail: Writing ENH-024's tests found that (1) the JSONL session never read the CLI's stderr pipe — the flood test hung for the full 60 s before the reader existed, and Codex's *session gone* had been unreadable — and (2) `Turn.failed` was set by every dialect and read by nothing: a provider's failed turn landed on the record as `completed` with the error sentence as its answer. Both closed in the same group: a stderr reader keeping the last 64 KB, and a failed `Turn` becoming a `Failed` observation so the outcome is `failed` and `failure` can name why. The thread-record test now covers the plain failure too.

---

### [DISCOVERY] 2026-09-20 — G3: BUG-061 — an attribute named `mode` switched the policy
Topics: attributes, judgement, mode, governance, reserved
Affects-phases: phase-45-truth-both-ways
Affects-specs: architecture/runtime.md#the-thread
Detail: Writing the reserved-name test for per-turn words with `{"mode": "full"}` found it was *not* refused: only the step's keys (`posture`, `component`, `inputs`) were reserved, and `context_for` wrote the conversation's `thread`/`turn`/`mode` before the host's attributes, so an attribute of the same name won — and `ModeGovernance` selects its policy by that key. Measured: a `read-only` thread with `attributes={"mode": "full"}` was judged under `full` on every act. Closed by `HOST_RESERVED` (the step's keys and the conversation's), refused at open, turn and resume; the run's own clash check keeps to the step's keys. A contract narrowing for a host that used those names — the migration note says so.

---

### [NOTE] 2026-09-20 — G3: a flag that takes key=value is data, not a code path
Topics: behaviour, codex, template, provider-file
Affects-phases: phase-45-truth-both-ways
Affects-specs: architecture/adapters.md#the-agent-adapter
Detail: Codex takes reasoning effort as a config override (`-c model_reasoning_effort="high"`), not a flag of its own; `BehaviourArg` was `{field, flag}` and could not say it. One optional field, `template` (with `{value}` where the value goes), keeps the mapping in the provider file — any CLI whose flag takes `key=value` uses it — and the runtime stays ignorant of Codex. The loader refuses a template with no `{value}`, since it would drop the value silently.

---

### [DECISION] 2026-09-20 — D138 amended in G4: `read-only` keeps its documented ceiling; the door is `ask`
Topics: modes, contained, web, read-only, ask, egress
Affects-phases: phase-45-truth-both-ways
Affects-specs: architecture/adapters.md#the-modes-adapter
Detail: The first D138 entry called `read-only`'s `contained = false` an inconsistency and narrowed it. Writing the change found two things. (1) It was not an inconsistency but the documented design — `specs/architecture/adapters.md`'s modes table says `read-only` judges "reads, the skills, the person, the web; nothing written or run". (2) `contained` is stamped on every operation of an environment from the environment's proof, so over a `full` environment even `read_file` is `contained = false`, and a `read-only` policy with a contained ceiling offered *nothing* there — `tests/test_a_mode_reaches_the_child.py` said so at once. The narrowing was reverted before it was committed. What stands of D138: `workspace-write` (the silent writing mode) hides an uncontained reach — a reach beside writes is an egress channel; `read-only` allows it — it writes nothing a reach could carry out, and a read-only policy must work over any environment; **`ask` asks before it** (was: refused outright), which is its own definition and Claude Code's default; an `allow` rule for the one tool in `ask` is the served product's door. No vocabulary change; the battery's file unchanged. The lesson is the phase's: a decision made from one file's evidence is checked against the architecture *before* the code moves, not after the suite says so.

---
