---
type: Research
date: 2026-09-14
status: for the owner's read — the plan follows it
topics: [ownership, entry-points, ports, streaming, turns, persistence, wire, testing, intent-studio]
---

# What a harness development kit owes its products — and where this one falls short

**The question** (the owner, 2026-09-14): a product may own its conversation and use only the
kit's parts; or use the kit's threads and turns and supply its own database; Intent Studio
already consumes the kit — is it consuming it *the right way*, what is missing, what is
mismatched, and what should a generic HDK's architecture be.

**The method.** Three sources, read against each other: the field (the eight runtimes of
`2026-09-14-how-comparable-runtimes-do-it.md`); the kit as it stands at **v0.28.0**; and
**Intent Studio's actual consumption** — fifteen backend modules under
`intent/orchestration/harness/` and `intent/runner/` (backend `213e0a4b`), read for every place
the product wrote *around* the kit rather than *on* it. What a product had to invent is the
most honest list of what the kit lacks.

## 1. The principle

A development kit is not a framework: it does not own the product's shape. **Every layer is
usable without the layer above it, and every piece of state lives behind a port.** A product
enters where its ownership begins:

| entry point | who owns the conversation | who owns the rows | who is there |
|---|---|---|---|
| `run()` — the governed loop | the product (its own messages) | the product | Intent Studio's web conversation (`HarnessCaptureEngine`) |
| `Thread` — turns as runs | the kit's record | either (`ThreadStore`) | Intent Studio's subscription turn, the runner |
| `Harness` — in-process facade | the kit | the kit's or the product's (`store=`, `threads=`, `checkpointer=`) | a Python product with one process |
| `serve` — the app server | the kit | either, one url or handed in | the React example; a product in any language |

Scenario 1 (the product owns everything and takes parts) is the first row; scenario 2 (the
kit's threads over the product's database) is the last two with the three stores handed in.
The recommended shape for most products is the last row *behind the product's backend*: the
product keeps users and its own tables, the harness keeps threads, turns, the record and parked
runs, and the product's tables hold only the join (user ↔ thread id) — one app server behind
every surface (Phase 29).

## 2. The audit — sixteen things a kit owes, and where we stand

Severity is *for Intent Studio consuming it the right way*: **P1** it is writing around the kit
today, or will as soon as it deploys as one app server; **P2** a product will meet it in its
first year; **P3** hygiene.

| # | a kit owes | we have | missing or mismatched | evidence | sev |
|---|---|---|---|---|---|
| Q1 | **The governed turn as a primitive** — one provider turn, judged and recorded, without the record container | `Thread.turn` only; `Thread.open` requires a `ThreadStore`, a root, a record | A product that owns its conversation and drives a CLI opens a `Thread` *per turn* over `InMemoryThreads` with a one-entry fake mode registry (`_OneMode`) to get a governed turn — the kit imposing its container | `engine.py::_subscription_turn` | **P1** |
| Q2 | **The agent streams** — its words as activity while it writes, its reasoning kept | `AgentComponent` calls `complete`, never `stream`; `LangChainModel.stream` drops `reasoning` and reads tool calls off single chunks | The product wrote `StreamingLangChainModel` to stream *underneath* `complete` and fold chunks back; the kit-side half is the open lane-H row (join J5, ENH-065) | `model.py` | **P1** |
| Q3 | **A question outlives the request** — a live CLI's ask answered on a later request, the act performed once with consent | **D80 (0.28.0)**: the question on the record, the parked act resumed from the checkpointer by `settle`, the agent told | The product built this itself on 0.27.2: `_CardAsks` (deny on the spot, tell the CLI a card will ask) and `parked.py` (staged acts by intent, in memory, lost on restart). **Not a gap now — an adoption item**: it needs the product to keep the thread record (a `ThreadStore` over its tables, or the kit's Postgres) instead of `InMemoryThreads` per turn | `engine.py::_CardAsks`, `parked.py` | **P1** (adopt) |
| Q4 | **Its contracts, shipped** — a product proves its own store, governance or components hold the port | `shadow_hdk.runtime.testing` ships the doubles; the contract suites live in `tests/adapters/contract/suites.py` — not in the wheel | A product implementing `ThreadStore` over its tables cannot run `ThreadStoreContract` without copying our tests; the product wrote its own scripted `AgentPort` double (0043 P2) because none ships | tests/ · board 0043 | **P1** |
| Q5 | **Tokens on the record** — a subscription is *tokens counted, no price* | `Usage` carries tokens per call; `Spent` (D84) carries steps · seconds · cents | A thread's tokens are not on its record; the product folds `usage` events itself into `LLMUsage` per turn | `engine.py::_record_subscription`, `kernel/threads.py::Spent` | **P1** |
| Q6 | **Governance composed, not subclassed** — two policies judging different components (the record's constitution, the machine's mode) | `ModeGovernance`, `Narrowed` (a second gate that only narrows), `RuleGovernance` | The product wrote `TwoGovernments(GovernancePort)` routing by `context.attributes["component"]`; a *routed* governance combinator (by component name or by port) is one small shipped piece | `machine.py` | **P2** |
| Q7 | **A parked run behind a port of ours** — not the runtime library's | `Store` and `ThreadStore` are kernel ports with suites; the checkpointer is LangGraph's `BaseCheckpointSaver`, typed `Any` through the kit | A product not on SQLite/Postgres must bring a LangGraph saver; the runtime library leaks into the persistence contract | `stores.py`, `RunOptions.checkpointer: Any` | **P2** |
| Q8 | **A stream that survives a drop** — a page on a train, a phone in a lift | SSE with one path back; `thread/resume` re-reads the record and re-presents questions | Events of the turn *in flight* are lost on a reconnect: no `Last-Event-ID`, no replay of a turn's events since a sequence; the product's runner built its own batched, retrying up-channel (`channel.py`, "the queue is the reconnect") for the opposite direction | `wire/serve.py`, `runner/channel.py` | **P2** |
| Q9 | **Resident sessions that idle out** — one app server, many people, one CLI process per open thread | A thread holds its provider session open for its whole opening; `_reopen_provider` (D76) can resume a CLI on its own session id | N open threads = N resident CLI subprocesses until the sessions close; Codex unloads a thread after 30 min idle and reloads on demand — the mechanism to reopen exists, the idle policy does not | `runtime/threads.py` | **P2** |
| Q10 | **The wall budget counts running time** | `LeaseMeter` on a `Thread` counts seconds from the opening; D33 says parked time is not a run's | A thread left open overnight with one turn has spent its hour by sitting there (the React header read `58 min` left two minutes after `60`); the budget should count the turns' running legs, as a run's does | `Spent.seconds`, D84 | **P2** (a correction) |
| Q11 | **Typed refusals on the wire** — a product switches on *what* was refused, not on a sentence | JSON-RPC errors with `code` (`REFUSED`, `GONE`, version mismatch), `message`, `data = the exception's class name` | `ThreadHeld`, `TurnRunning`, `KeyError` cross as class names in `data` — usable, undocumented, and not a published vocabulary; the TypeScript client exposes `message` only | `wire/peer.py`, `client.ts` | **P2** |
| Q12 | **The record versioned** | `ThreadRecord` dumped as JSON with defaults — forward-compatible (0.28.0 added five fields, every old record loads) | No `version` on the record; a product mapping it to *columns* learns of a moved shape from a failing insert; a pre-D82 rule is unscoped (for everyone) and nothing says so — the React example's silent write was one | `kernel/threads.py`, the demo's store | **P2** |
| Q13 | **A client for every language the product runs in** | TypeScript (by path, unpublished); Python in-process only; `connect_to` is a test helper | A second Python process — the runner — talking to the server built its own protocol (`runner/channel.py`, `runner/client.py`, join J5); the TS client is not on npm | `runner/` · the demo's `file:` dependency | **P2** |
| Q14 | **Structured output** — the agent answers in a schema the product names | `derivation` for typed tables; tool calls carry JSON; nothing asks the agent for a typed final answer | The product parses the reply's prose (`reply` is "the model's last words"); Codex, the Agents SDK and ADK all take an output schema | `engine.py` | **P3** |
| Q15 | **Hooks around a tool call** — observe or veto with the product's own code before and after an act, without writing a governance port | governance (judge), sink (proposals), observer (events), `Narrowed` | The Agent SDK's hooks and Codex's execpolicy let a product intercept by code; ours does it by a port — deliberate (D23: policy is data), but a *callable governance* helper (`judge = my_function`) is the missing convenience | — | **P3** |
| Q16 | **Operations at scale** — many processes, one store | one holder per thread (D81), health, admin listings | No cross-process notification (a second app server cannot stream a thread the first holds — by design, one holder), no process-wide turn limit, no metrics endpoint (OTEL exists) | D86 | **P3** |

## 3. What Intent Studio wrote around the kit — the honest list

Read module by module (backend `213e0a4b`, on `shadow-hdk==0.27.2`):

| the product's module | what it does | the kit's answer |
|---|---|---|
| `model.py` `StreamingLangChainModel` | streams under `complete`, folds chunks, keeps reasoning | **Q2** — the kit's agent should stream; then this class goes |
| `engine.py` `_CardAsks` + `parked.py` | denies a live ask on the spot, stages the act, performs it on the card's *yes*; in memory, by intent | **Q3** — D80 does this on the record and across restarts; the product keeps the thread instead of a thread per turn |
| `engine.py` `_subscription_turn`, `_OneMode` | a `Thread` per turn over `InMemoryThreads` with a one-entry mode registry | **Q1** — a governed turn primitive; until then, a resident thread per intent on the product's `ThreadStore` (which Q3 also wants) |
| `engine.py` `_record_subscription` | folds `usage` events into tokens per turn | **Q5** — tokens on `Spent` |
| `machine.py` `TwoGovernments` | two policies routed by component | **Q6** — a shipped combinator |
| `permissions.py`, `modes.py` | modes and rules as product rows, judged through the kit's `mode_from_document`/`ActRule` | **right** — this is scenario 1 done well; a `Store` adapter over the same rows would let `ModeRegistry` read them live, optional |
| `governance.py` `ConversationPolicy`, `components.py` `RecordTools`, `sink.py` `RecordSink` | the product's policy, verbs and gate behind the kit's ports | **right** — exactly the seam `adapters.md` describes |
| `runner/channel.py`, `runner/client.py`, `runner/session.py` | a runner: the kit's environment here, the record on the server, its own up-channel, `InMemorySaver` per job (ENH-067) | **Q13** (a Python client and a "remote sink/observer" shape) and **Q7/Q3** (a parked job that survives the runner restarting) |
| `agent.py` `Subscription` | `detect` at every turn, `open_with` on the provider file, the slot's model and effort as `Behaviour` | **right** — D41, D64 as intended |
| the product's own `GraphCheckpointModel` (Postgres) | the old loop's checkpointer, kept beside the kit's | **Q7** — one port of ours, the product's Postgres behind it |

Six of ten are the kit's to close; four are the product consuming it as designed. The product
did nothing wrong — it wrote what the kit did not yet have, and said so in every docstring.

## 4. Corrections — things in the kit that read as wrong on this audit

- **Q10** the thread's wall budget counts idle time (above).
- **`Approvals` is two things in one object** — the runtime's `ask` and the host's `answer`/
  `pending` — which is why the product *subclassed* it to change the runtime side (`_CardAsks`).
  The runtime should take a small `Questions` port (ask → answer) and the host's handle implement
  it; a product then hands in its own without inheriting ours.
- **`checkpointer: Any`** everywhere the runtime passes it — the sign of Q7.
- **The wire's error `data`** is a class name by accident of `peer.py`, not a contract (Q11).
- **A rule made before D82 is for everyone** and nothing marks it (Q12): the migration note a
  release should carry, and a `version` on records and rules.
- **`Thread` has grown a wide surface** (holder, principal, budget, pending, settle, when) — not
  wrong, but Q1's factoring is also what keeps it legible: a `Turn` that runs, a `Thread` that
  keeps.

## 5. What is not missing — and should stay that way

An authorisation engine (the product's plugs into the governance port and sees the principal —
D82); a message model (the record is events and items; a product's message is a turn's prompt
plus its items — by design, D62); rate limiting, metrics endpoints, CORS (the product's platform
and backend — D86); a UI (the React example is a client, never a part). Naming these keeps the
kit a kit.

## 6. The shape of the plan, for the owner's decision

Six groups, in the order Intent Studio meets them; each one RED-first, mutation-checked, its
records, the four zeros, branch → CI → staging → main; a release at the end (a contract change
again, so a *Pins* row):

1. **The governed turn** (Q1) and **the agent streams** (Q2): `Turn`/`Conversation` factored out of
   `Thread`; `AgentComponent` streams through `ModelPort.stream` and puts its text and reasoning
   on `activity`; `LangChainModel.stream` keeps reasoning and merges chunks. *Then `StreamingLangChainModel`, `_OneMode` and the thread-per-turn go from the product.*
2. **Tokens and running time on the record** (Q5, Q10): `Spent.input_tokens/output_tokens`; the
   thread's seconds are its turns' running legs.
3. **The contracts shipped** (Q4) and **a `Questions` port** (the correction above): `shadow_hdk.testing.contracts` importable, provider doubles shipped; `Approvals` implements `Questions`.
4. **A routed governance** (Q6) and **typed refusals** (Q11): `Routed(by_component={...}, else=…)`; a published vocabulary of `error.data` kinds, the TypeScript client raising them.
5. **A parked run behind our port** (Q7) and **the record versioned** (Q12): a kernel `RunStore` with the LangGraph saver as its one adapter today; `ThreadRecord.version`, `ActRule.version`; the migration note.
6. **Sessions that idle out** (Q9) and **a stream that survives a drop** (Q8): an idle policy on `Thread` (close the provider after N minutes, reopen on the next turn on its session id); events numbered per thread and `thread/events {since}` for a reconnect; `Last-Event-ID` on the SSE door.

Q13 (a Python client; the TS client on npm) and Q14–Q16 are named, not scheduled: Q13 waits on
the runner protocol (join J5) and the owner's word on npm; Q14–Q16 are P3.

**What Intent Studio does in the same period, to consume it right**: pin the release; keep a
resident thread per intent on a `ThreadStore` over its Postgres (Q3 — `_CardAsks` and
`parked.py` go); set `principal` from its backend (D82); drop `StreamingLangChainModel` when
group 1 lands; read tokens off `Spent` when group 2 does; prove its stores with the shipped
suites when group 3 does.
