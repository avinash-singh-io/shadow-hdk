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

## 0. The admission rule — how a thing gets into the kit

Intent Studio is the *evidence* in this note, never the *reason*. A thing enters the kit only
when **(a)** at least two of the eight runtimes of the field have it, or **(b)** it is a port
every product would otherwise reimplement — and **never** when it is a product concept. Every
Q below passes (a) or (b) and is named in the field's words (D61: thread, turn, principal,
approval — not intent, claim, persona). What Intent Studio is (a record of claims, a confirm
card, a runner on a laptop) stays in Intent Studio; what the kit gets is the generic thing its
workaround stood in for. Section 5 names what was refused for the same rule. Two invariants
hold the line in the tree: the kernel imports nothing but pydantic (`test_stands_alone`), and
the bare harness runs with no product word in it (`test_bare_harness`).

| Q | the field has it | a port every product needs |
|---|---|---|
| Q1 the governed turn | the Agents SDK's `Runner.run` per turn over the product's session; the Agent SDK's `query()`; ADK's `Runner.run_async` on the product's session service | — |
| Q2 the agent streams | every runtime streams text and reasoning | — |
| Q3/Q17 a question outliving the request | LangGraph's `interrupt` — the request ends with `__interrupt__`, a later request resumes; Managed Agents' sessions | — |
| Q4 contracts shipped | — | every product with its own store |
| Q5 tokens on the record | Codex's thread usage, LangGraph's thread metadata, ADK's session state | — |
| Q6 routed governance | the Agent SDK's per-tool permission rules; Codex's execpolicy per command | — |
| Q7 a parked run behind our port | Mastra's interchangeable storage; the Agents SDK's session protocol | every product not on our two backends |
| Q8 a stream that survives a drop | LangGraph Server's `join` on a run's stream; Codex's WebSocket reconnect | — |
| Q9 sessions that idle out | Codex unloads a thread after 30 min; Managed Agents' session lifetime | — |
| Q10–Q13 | corrections and contracts every kit owes | — |

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
| Q3 | **A question outlives the request** — a live CLI's ask answered on a later request, the act performed once with consent | **D80 (0.28.0)** keeps the question on the record and resumes the parked act by `settle` — **when the host died**. A turn ended *on purpose* (the request returned, the reader cancelled) withdraws its questions (D59) and clears them from the record | The product built the on-purpose case itself: `_CardAsks` (deny on the spot, tell the CLI a card will ask) and `parked.py` (staged acts by intent, in memory, lost on restart). **Corrected on the second read**: D80 covers the crash; the deliberate park — *end this turn now, keep the question, settle it on a later request* — is **Q17**, LangGraph's `interrupt` shape, and the kit does not have it. Until it does, a request/response product keeps the request open while the card is up (as the React example does over its stream) | `engine.py::_CardAsks`, `parked.py` | **P1** |
| Q4 | **Its contracts, shipped** — a product proves its own store, governance or components hold the port | `shadow_hdk.runtime.testing` ships the doubles; the contract suites lived in the kit's own tests (`tests/adapters/contract/`) — not in the wheel; **shipped in Phase 30 as `shadow_hdk.testing.contracts`** | A product implementing `ThreadStore` over its tables cannot run `ThreadStoreContract` without copying our tests; the product wrote its own scripted `AgentPort` double (0043 P2) because none ships | tests/ · board 0043 | **P1** |
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
| Q17 | **A park on purpose** — `turn/start {on_question: "park"}`: the turn ends `parked` at the first question, the question on the record, the provider closed (a CLI is reopened on its session id later), `settle` on any later request runs the act from its checkpoint and the next turn is told | D80's machinery — `pending`, `settle`, the note folded into the next prompt — exists for the crash | The turn-end clearing (`still = pending − this turn's`) treats every end as a withdrawal; an on-purpose park is a fourth outcome the turn must know it is taking; the interim for a request/response product is a long-lived stream per turn | `runtime/threads.py::turn` | **P1** |
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

1. **The governed turn** (Q1), **a park on purpose** (Q17) and **the agent streams** (Q2): `Turn`/`Conversation` factored out of
   `Thread`; `AgentComponent` streams through `ModelPort.stream` and puts its text and reasoning
   on `activity`; `LangChainModel.stream` keeps reasoning and merges chunks; `turn(when=, on_question="park")` ends the turn `parked` with the question kept, for a product that answers on the next request. *Then `StreamingLangChainModel`, `_OneMode`, `_CardAsks`, `parked.py` and the thread-per-turn go from the product.*
2. **Tokens and running time on the record** (Q5, Q10): `Spent.input_tokens/output_tokens`; the
   thread's seconds are its turns' running legs.
3. **The contracts shipped** (Q4) and **a `Questions` port** (the correction above): `shadow_hdk.testing.contracts` importable, provider doubles shipped; `Approvals` implements `Questions`.
4. **A routed governance** (Q6) and **typed refusals** (Q11): `Routed(by_component={...}, else=…)`; a published vocabulary of `error.data` kinds, the TypeScript client raising them.
5. **A parked run behind our port** (Q7) and **the record versioned** (Q12): a kernel `RunStore` with the LangGraph saver as its one adapter today; `ThreadRecord.version`, `ActRule.version`; the migration note.
6. **Sessions that idle out** (Q9) and **a stream that survives a drop** (Q8): an idle policy on `Thread` (close the provider after N minutes, reopen on the next turn on its session id); events numbered per thread and `thread/events {since}` for a reconnect; `Last-Event-ID` on the SSE door.

Q13 (a Python client; the TS client on npm) and Q14–Q16 are named, not scheduled: Q13 waits on
the runner protocol (join J5) and the owner's word on npm; Q14–Q16 are P3.

**Done — 0.29.0 (Phase 30, D87–D94)**: groups 1–6 as planned; the guide is `docs/consuming.md`.

**What Intent Studio does in the same period, to consume it right**: pin the release; keep a
resident thread per intent on a `ThreadStore` over its Postgres (Q3 — `_CardAsks` and
`parked.py` go); set `principal` from its backend (D82); drop `StreamingLangChainModel` when
group 1 lands; read tokens off `Spent` when group 2 does; prove its stores with the shipped
suites when group 3 does.

## 7. How Intent Studio consumes the kit properly — the target integration

Intent Studio is a Python backend (FastAPI, Postgres, its own intents, messages, users,
workspaces, personas and platform settings), a web client, and a runner on the person's
machine. The right integration keeps every one of those the product's, and takes the kit at the
door where the product's ownership ends. In the kit's words, not the product's.

### 7.1 The ownership map

| the product owns | the kit owns | the join |
|---|---|---|
| users, workspaces, permissions, tenancy | nothing — it sees a `principal` and `attributes` (`workspace`, `intent`) on every judgement (D82) | the backend sets them on `Thread.open`; rules a person keeps are scoped to them by the kit |
| intents and messages (the record of claims), the confirm card, the trail's rendering | threads, turns, items, activity, the questions open, what was spent (D62, D80, D84) | `intent.thread_id` — one column; the message a person sees is a turn's prompt plus its items |
| its policy (the record's constitution), its verbs (record tools), its gate (the sink) | the governed loop, effects, the environment's sandbox, the shipped modes and their judgement, rules (D65, D85), the provider surface (D41), the approval mechanism (D58, D80) | the product's ports handed to `Ports`; the machine's mode from platform settings |
| modes and rules as platform settings | `ModeRegistry` / `ActRules` reading them live through a `Store` source (D66) | one small `Store` adapter over the settings rows — or the kit's Postgres tables beside them |
| the runner's presence and its up-channel | the environment on the laptop, the governed turn, a parked job that survives (D79/D80 on `sqlite:///`) | until Q13, the product's own channel; the record stays on the server |

### 7.2 The composition — one per backend process

- **Enter at `Thread`, in-process** — not `serve` over the wire (the backend is Python and already
  a process). One `ServeHost`-shaped composition per process: the three stores on the product's
  Postgres by url (`stores_for(DATABASE_URL)` — the kit's own `shadow_hdk_*` tables beside the
  product's; no port code to write) or, if the product wants its own tables, a `ThreadStore` over
  `agent_thread` proving `ThreadStoreContract` (Q4). The product's `GraphCheckpointModel` goes:
  the kit's Postgres saver on the same database is the one checkpointer.
- **A resident thread per intent**, not a thread per turn: `Thread.open(principal=user_id,
  attributes={"workspace": …, "intent": …}, budget=…, holder=this process)` once, its id on the
  intent; `Thread.resume` on the next request (a CLI resumes on its session id — D76); the
  thread closed when the process is done with it, and unloaded when idle once Q9 lands.
- **The model kind stays scenario 1** — `run()` per message over the product's own `Ports`
  (`ConversationPolicy`, `RecordTools`, `RecordSink`, `LangChainModel.over(chat)`) — this is
  right today and stays; the streaming wrapper goes when Q2 lands.
- **The CLI kind is the resident thread** — the provider found by `detect`, opened by `open_with`
  on the thread's registry (`SocketOffer`), the slot's model and effort as the mode's `Behaviour`
  — exactly `agent.py` today, minus `_OneMode` (the thread reads a real `ModeSpec` from the
  registry) and minus the thread per turn.
- **Two governments as one port**: `TwoGovernments` stays until Q6 ships `Routed(...)`; then it is
  three lines of configuration.

### 7.3 A question, end to end

Today (0.28.0): keep the request open while the card is up — the backend's realtime stream
already carries events; the person's *yes* reaches `host.approvals.answer(handle)` from another
endpoint on the same process, and the turn continues. A restart with a card up is D80: the
question comes back with `Thread.resume`, `settle` performs the act, the agent is told. After
Q17: `turn(text, on_question="park")` — the request returns at the first question, the record
holds it, any later request settles it. `_CardAsks` and `parked.py` go either way.

### 7.4 What is measured, and where

Steps, seconds, cents from `Spent` (D84); tokens from the `usage` events until Q5 puts them on
`Spent`; the budget per intent as `budget=` on `Thread.open` (a persona's metered build); a
person's *approve and don't ask again* as `ApproveAndAddRule` — the rule scoped to them by the
kit, and to the intent through `scope = "intent:<id>"` if the product wants it narrower.

### 7.5 The runner

The runner's shape — the record on the server, the files here — is not the wire's; it is
scenario 1 on the laptop with the product's channel as sink and observer, and stays so until
Q13. What 0.28.0 gives it now: `stores_for("sqlite:///…")` for a parked job that survives the
runner restarting (ENH-067), a resident `Thread` per job on it, and `Thread.settle` for the
answer that comes back with the next job.

### 7.6 Don'ts — what the current consumption does that the kit should not need

Subclassing `Approvals` to change the runtime's side; a `Thread` per turn over `InMemoryThreads`;
a fake mode registry to carry a behaviour; an in-memory staged-act store beside the kit's
checkpointer; two checkpointers on one database; parsing the reply's prose for structure (Q14
is the honest answer; until then the product's own `Proposal` verbs are the structure). Each of
these is a row in section 2, and the plan closes them in the order the product meets them.

