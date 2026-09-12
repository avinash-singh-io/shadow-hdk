---
type: Plan
status: accepted
date: 2026-09-12
---

# The substrate — what a harness must provide, grounded, and what ours still lacks

> Written before any code, at the owner's instruction: *references first, ground it, then plan.*
> Every claim below about another product was read on 2026-09-12 from the source linked. The
> gaps are against our own tree as of v0.20.0.

## 1. What the reference implementations converge on

Four products that ship an agent to real users were read for how they shape the thing a host
needs: **Codex** (the App Server behind every surface), **Claude Code** (the CLI and its Agent SDK),
**OpenCode** (agents as modes), and the **Agent Client Protocol** (editors ↔ agents). They agree
on more than they differ.

### 1.1 One harness behind a protocol powers every surface

OpenAI extracted the agent core out of a monolithic CLI into a standalone server with a
documented bidirectional protocol because *"every new surface re-implemented the agent"*, remote
development was impossible, and third-party embedding was painful; the result is *"a single agent
implementation to power the CLI, desktop app, IDE extensions, and web interface"*
([App Server guide](https://codex.danielvaughan.com/2026/04/15/codex-app-server-complete-guide/)).
Anthropic says the same the other way round: the SDK is Python and TypeScript only, and *"to drive
the same agent loop from another language, run the CLI as a subprocess"*
([Agent SDK overview](https://code.claude.com/docs/en/agent-sdk/overview)).

**Consequence for us.** The loop stays in Python. Every other language consumes the protocol — a
process (stdio JSONL) or a socket (HTTP/SSE, WebSocket) with **generated bindings**. Codex ships
`codex app-server generate-ts` / `generate-json-schema`; we already publish fifteen JSON-Schema
contracts and hold them by an invariant. What is missing is a `serve` entry point with a stdio
transport, a TypeScript package generated from those schemas, and the host-held handles
(questions, dials) crossing the protocol — today a host in another language cannot answer a
question.

### 1.2 Thread → Turn → Item, and items stream

Codex's protocol is three nested primitives: **Thread** (durable, resumable, forkable), **Turn**
(one user input plus the agent's work; `turn/start`, `turn/steer`, `turn/interrupt`), **Item**
(`item/started` → `item/*/delta` × N → `item/completed`; kinds: user message, agent message,
reasoning, command, file change, tool call). *"A typical turn produces dozens of `delta`
notifications before the final `item/completed`."* Claude Code's `--include-partial-messages`
yields the same shape (`thinking_delta`, `text_delta`), **measured on the owner's subscription
2026-09-12**: a "think carefully" prompt produced nine `thinking_delta`s, one `text_delta`, and a
70-character thinking *summary* on the final message. The Vercel AI SDK formalises this as
`UIMessage.parts` on one SSE stream.

**Consequence for us.** We have Run and Step (the record) and nothing between them and the
person. The record must stay what it is — durable, complete, checkpointed — and *deltas must not
go on it* (a thousand per turn is noise on a record meant to be replayed). So the missing primitive
is an **ephemeral activity stream beside the record**: partial thinking, partial text, a running
command's output, "composing a tool call". And a **conversation** — thread and turn — is today an
*example* (the coder example's former `session` module) that the studio imports. It is the single most reused
thing and it is not in the harness.

### 1.3 Approvals are requests from the server to the client

Codex: `item/commandExecution/requestApproval`, `item/fileChange/requestApproval`; the client
answers `accept | decline | cancel | acceptWithExecpolicyAmendment`. ACP: `session/request_permission`
with options. Claude Code: a permission prompt with "yes, and don't ask again" scoped per
repository and command.

**Consequence for us.** Our `Asked` is on the record and, since v0.20.0, says what it is about
(D59). It is not yet a *request the wire delivers to a client and takes the answer from*; and the
answer vocabulary is `allow | refuse` — no "and don't ask again", which every product has and which
is a **rule the person adds to the policy at answer time**, not a special case.

### 1.4 Modes are two things wearing one name

| Product | The approval half | The behaviour half | Switch |
|---|---|---|---|
| Claude Code | `default` (manual) · `acceptEdits` · `plan` · `auto` (a classifier judges) · `dontAsk` · `bypassPermissions`; plus allow/ask/deny rules by tool and pattern ([permissions](https://code.claude.com/docs/en/permissions)) | output styles, `--append-system-prompt`, `--model`, `--effort` | `Shift+Tab`, `--permission-mode`, `defaultMode` |
| Codex | `approval_policy` (`on-request` · `never` · granular), `sandbox_mode` (`read-only` · `workspace-write` · `danger-full-access`), permission profiles with filesystem/network rules ([config reference](https://learn.chatgpt.com/docs/config-file/config-reference)) | `model`, `model_reasoning_effort`, `developer_instructions`, `AGENTS.md` | `--profile`, `/approvals` |
| OpenCode | per-agent `permission`: `edit/bash/webfetch/… = ask | allow | deny` ([agents](https://opencode.ai/docs/agents/)) | an **agent** = `prompt` (a markdown file), `model`, `temperature`, `steps`, `description` | `Tab` cycles primary agents |
| ACP | `session/request_permission` | — | `SessionMode{id,name,description}`, `session/set_mode`, `current_mode_update` ([session modes](https://agentclientprotocol.com/protocol/session-modes)) |

The synthesis: **a mode = a policy (what runs, what asks, what is refused) + a behaviour (who the
model is: role, model, effort, temperature, which tools are offered) + a presentation (id, name,
description)** — declared by the host as data, switchable during a session, announced when it
changes. ACP is the protocol shape to copy; OpenCode's *agent-as-markdown-file* is the authoring
shape to copy.

**Consequence for us.** We have the policy half (`Mode` over effect profiles — stronger than any
of theirs, because it judges effects rather than tool names) and none of the rest: no behaviour,
no switching mid-run, no declaration over the wire. And the three policies that match the
environment's modes lived in the coder example's former `workshop` module (moved into the harness in Phase 25/26).

### 1.5 What a harness provides out of the box

From the Agent SDK's own list and Codex's: built-in tools (files, shell, **web search**), hooks,
subagents, MCP, permissions, sessions (resume, fork), skills/commands/memory, plugins, context
management, cost tracking, streaming. Against ours:

| Capability | Ours | Gap |
|---|---|---|
| Governance by effects, leases, the record, the sink | built — the loop | — |
| Files, shell, python in a proven sandbox | built (Phase 22) | a scratch dir in `read-only` (ENH-006) |
| Subagents | built (D51) | — |
| MCP | consumed (a component port) | — |
| Skills | built (Phase 24) | — |
| Cost, tracing | built (meter, OTel) | — |
| Sessions: resume | built (checkpointer) | list / fork / read at the *conversation* level |
| **Streaming / activity** | — | **missing** |
| **Conversation (thread/turn)** | an example | **missing as a primitive** |
| **Modes as policy + behaviour, switchable** | policy only | **missing** |
| **Behaviour for provider-backed agents** | — | **missing** (`AgentPort.open(tools, workspace)` takes none) |
| **Approvals over the wire; "don't ask again"** | on the record only | **missing** |
| **Agent-initiated questions to the person** | the agent writes it in prose | **missing** — Codex/Claude/OpenCode all have a question item |
| Interrupt / steer a turn | `Cancellation` | steer missing |
| Web search, fetch | — | **missing** — the one built-in every product has that we do not |
| Hooks (pre/post) | governance is *pre*; sink/observer are *post* | user code at those points is a port already; no gap worth a mechanism |
| Context management / compaction | planned (roadmap 25) | later |
| Memory | planned (roadmap 25) | later |
| Browser | environment seam admits it (D29) | later |
| Generated bindings, stdio transport, `serve` | schemas published | **missing** |

### 1.6 Two things read that change plans

- **Anthropic's terms** on the Agent SDK page: *"Anthropic does not allow third party developers to
  offer claude.ai login or rate limits for their products … unless previously approved."* Driving
  the *user's own* CLI on the *user's own* machine is what we do; a product that *offers* a
  subscription login to its customers is the case named. This is the owner's to read with a lawyer
  before BYOS ships in a product; it does not change the harness.
- **wigolo** ([repo](https://github.com/KnockOutEZ/wigolo)) is what the owner proposed for
  zero-cost web search: TypeScript, 5.2k stars, public beta, **AGPL-3.0**, ~1.5 GB of local models,
  eighteen public engines scraped through adapters, and — decisively — **it runs as an MCP server**.
  So it is consumed through the MCP component port with *zero* adapter code, in its own process
  (which is also how the AGPL is kept at arm's length from a product's code; a lawyer confirms).
  Its risk is the scraping: engines block datacenter IPs and it says so. A second, lighter option
  is `ddgs` (DuckDuckGo, no key, no models, the same ToS risk). Both are "consume behind a port";
  neither is built.

### 1.7 DSPy

DSPy 3.3 ([dspy.ai](https://dspy.ai/)) turns prompts into typed *signatures* and *compiles* them —
optimisers (GEPA, MIPROv2, BootstrapFewShot) tune the prompt text against **a metric and labelled
examples**, saving the result as JSON. It is not a way to *declare* a role; it is a way to
*improve* one once there is something to score it against. For modes that means: the role a mode
carries is data (a `Behaviour`), and DSPy is a candidate **optimiser behind a port, later** —
taking a behaviour or a skill, examples and a metric, and proposing a better one through the sink
(`Proposal(kind="behaviour")`, the same governed self-evolution as D56). Rule 11 applies: no
optimiser before the evaluator is locked. Not this round.

### 1.8 Ours against Codex's three nouns — an honest comparison

The owner asked whether Run → Step → Event is as good as Thread → Turn → Item. Side by side:

| | Codex App Server | shadow-hdk today | Verdict |
|---|---|---|---|
| The durable container | **Thread**: start, resume, fork, list, read, archive, rollback | **Run** with a checkpointer: park, resume, held children; no list/fork/rollback | theirs is more complete *as a container*; ours is more complete *as a ledger* (every step judged by effects, leased, costed, with provenance and posture) |
| One exchange | **Turn**: `start`, `steer`, `interrupt`, completed with usage | **not on the record** — a turn is a `you`/`agent` note the studio writes; `Cancellation` interrupts, nothing steers | **theirs is better.** A turn boundary is a fact every host needs and ours does not record it |
| The atomic unit | **Item**: `started → delta × N → completed`, typed (message, reasoning, command, file change, tool call) | **Step** (`Invoked → Observed`), typed by the component's effects, with reasoning, usage, children, refusal, question | equal in kind; **theirs streams, ours does not** |
| Approval | a request from server to client, typed per item, four answers | `Asked` on the record with what it is about (D59); two answers | theirs is better shaped for a client; ours is better grounded (the question names effects, not a tool) |
| What it governs | Codex, its own agent | any agent — Claude Code, Codex itself, OpenCode, an in-process pattern — under one policy | **ours is a level up**: theirs *is* an agent behind a protocol; ours is the substrate an agent runs *in* |
| The vocabulary a client holds | three nouns | Run, Step, Event, Observation, Composition, Lease, … | theirs is smaller, which matters for adoption |

So: at the ledger, ours is richer and more principled — governance by effects, leases, a
complete replayable record, provenance, nested runs with their own budgets — and nothing in
Codex's protocol has those. At the *host-facing* surface, theirs is better shaped today: a turn is
first-class, items stream, approvals are requests, and a client developer can hold the whole thing
in their head.

**The decision that closes the gap without a new concept.** (Built: a turn is a *run* of the
thread, not a step — D62 says why.) A conversation is a run; **a turn is a
step of that run**; the agent's tool calls are child steps under it (already so, by `parent`);
activity streams beside each step. Then Thread → Turn → Item *is* Run → Step → child steps, the
record gains turn boundaries for free, `steer` and `interrupt` are operations on the current step,
and the projection a client renders is exactly Codex's shape with our ledger underneath. What it
costs: the provider's session must be held across steps by the `Conversation` object rather than
inside one long-lived `converse` step — which is the right place for it anyway (the registry
socket served for the conversation's lifetime, not per step). The host-facing vocabulary becomes
**Conversation · Turn · Step · Activity** — four nouns, one of them ours.

### 1.9 The container is the harness's to offer, and the words are the industry's

**Thread as a component.** Every product has a durable container — thread (Codex, OpenAI,
LangGraph) or session (ACP, Claude Code) — with resume, fork, list, rollback. It is foundational,
so the harness provides it the way it provides everything: a `Thread` primitive over a
`ThreadStore` port with a sqlite adapter shipped. A product with its own sessions implements the
port over its own tables, or does not use `Thread` and drives turns directly; the runtime never
requires it. Composable: pick it or skip it.

**Terminology.** Where the industry has a term, we use it; where the thing is ours — governance by
effects, the lease, the sink, provenance, posture — we keep the word and document the mapping.
Invented names go. Applied in Phase 25 as one contract change:

| Industry term | Ours today | Decision |
|---|---|---|
| Thread (Codex, OpenAI, LangGraph) / Session (ACP, Claude) | `a_conversation` in an example | **`Thread`**; "session" only for a live provider connection, as MCP and Claude use it |
| Turn | not on the record | **`Turn`** — a step of the thread's run |
| Item, delta (Codex; OpenAI Responses API) | `Step` projection; no deltas | **`Item`** is what a host renders; `Step` stays the kernel's plan unit (a standard word too); **`delta`** for streaming |
| Approval request (Codex `requestApproval`, ACP `request_permission`) | `Asked`, `Questions` | **`ApprovalRequest`**, answered `approve` · `deny` · `approve-and-add-rule` |
| User input request (Codex `requestUserInput`, ACP elicitation) | — | **`InputRequest`** — the agent's own question to the person |
| `session/set_mode`, `set_config_option` (ACP) | "Dials" (proposed) | **`set_mode` / `set_option` on the Thread**; "Dials" dropped |
| reasoning, usage (Responses API) | `Reasoned`, `Spent` | renamed **`reasoning`**, **`usage`** |
| run, step, refused, completed | `Run`, `Step`, `Refused`, `Ended` | already standard — kept |
| budget, limits | `Lease` (ceiling, floor) | **kept**: a reservation carved for children is ours; the facade and TOML say `budget` |
| effect profile, sink, provenance, posture | ours | kept — nothing in the industry names these; they are the uniqueness |

**Where the approval is answered** is the product's choice — a host in the server process or a
client over the wire — and both hold the same handle. The harness delivers the request and takes
the answer; it does not decide who sits there.

## 2. Principles this adds

Principles 1–5 stand. Using the harness for a day produced three more, each already violated once:

6. **The record is complete; the activity is live.** Everything that happened is on the record,
   once, replayable. Everything that is *happening* — a token, a line of output, "composing" — is on
   an ephemeral stream beside it, never checkpointed, never required for correctness. A host may
   ignore one without losing the other.
7. **A host holds handles, not code.** Whatever a person does *during* a run — answer, cancel,
   turn a dial, steer — is a handle the host keeps (`Questions`, `Cancellation`, now `Dials`), and
   every handle crosses the wire, so a host in any language holds the same ones. The parity
   invariant covers handles as well as `RunContext`.
8. **A product's vocabulary is the product's.** The registry's name, the labels on activity
   kinds, the wording of a question, the names of modes: data the host supplies with defaults,
   never a string in the harness a product would have to fork to change.

And one about adoption:

9. **Simple by default, deep by choice.** A harness is a file (`harness.toml`: environment, modes,
   provider, tools, skills) and three lines; the same file drives `shadow-hdk serve` for a host
   in another language. Every port stays open for a product that wants to compose by hand.
10. **Data changes live; code changes restart.** Everything a product would keep in a database —
   modes, behaviours, rules, skills, which tools are on, providers, budgets, the vocabulary — is a
   **registry with a store source**, changed by CRUD at runtime and read at the next step or turn,
   never by editing a file, redeploying or restarting. Only the substrate — contracts, the loop,
   ports, adapters, transports — is code, and only code needs a restart. §3.10 says which is which.

## 3. The design, primitive by primitive

Each is generic; each is behind a port; each crosses the wire; each is configurable data.

### 3.1 Activity (principle 6)

- Kernel: `Activity` — `run_id`, `step`, `kind`, `text`/`bytes`, `at`; kinds shipped:
  `thinking`, `text`, `output`, `composing`; open, a product adds its own.
- Runtime: `RunContext.activity(kind, text)` — emits to a bounded, drop-oldest, ephemeral stream
  (D11's observer discipline: never on the critical path). `run()` gains a sibling iterator or the
  observer port gains `on_activity`; decided in the phase by reading LangGraph's stream modes first.
- Transports: jsonl (`--include-partial-messages` → `thinking_delta`/`text_delta`), ACP (already
  streams), LangChain (`ModelChunk`), the leash (a running command's output through
  `HeldProcess.captured()` at an interval).
- Wire: an SSE stream beside events; the published schemas gain `Activity`.
- Configurable: which kinds a host wants, the interval for output, the labels.

### 3.2 Conversation (a thread of turns)

- Move the coder example's former `session` module's `a_conversation` into the harness as `Conversation`: opens a
  provider with a `Behaviour`, serves the registry, holds the step, `turn()`, `steer()`,
  `interrupt()`, `close()`; resumable by the provider's session id (`Dialect.resume_args`,
  already measured); listable and forkable through the host's checkpointer.
- The registry's name is the host's (`name=`), default `"tools"`.

### 3.3 Modes = policy + behaviour + presentation

- Kernel: `Behaviour(system, append_system, model, effort, temperature, tools_offered)`;
  `ModeSpec(id, name, description, policy, behaviour)`.
- Provider TOML maps `Behaviour` fields to that CLI's flags (`system_prompt_arg`, `model_arg`,
  `effort_arg`, `permission_mode_arg`, …) — a file plus nothing, exactly as `Dialect` already maps
  the transport (D40). A field a provider lacks is reported, never silently dropped.
- `AgentPort.open(tools, workspace, behaviour)`.
- Shipped defaults: `looking` / `confined` / `open`, derived from the environment's mode — moved
  out of the example. A product's modes are its own list, authored as TOML or markdown with
  frontmatter (OpenCode's shape).

### 3.4 Dials (principle 7)

- `Dials` — a host handle like `Questions`: `set(name, value)`, read by the runtime when it builds
  `Context` for each judgement, so `ModeGovernance` sees a new mode on the next step. A mode change
  that alters *behaviour* reopens the provider session with the new profile, resuming the thread.
- On the record: `Dialed(name, value)` — a fact worth replaying.
- Over the wire: `session/set_mode` and `current_mode_update` in ACP's terms; the handle crosses.

### 3.5 Questions, both directions, over the wire

- `Questions` crosses the wire (see and answer from any language) — the parity invariant extended
  to handles.
- The answer vocabulary grows a **rule**: *allow, and add this to the policy* — a `Rule` proposed
  through the sink (governed, like a minted skill), never a runtime special case.
- **Agent-initiated questions**: an `ask_person` component (offered where the host allows) puts a
  question on the record and waits on the same `Questions` handle; the answer is text. Codex,
  Claude Code and OpenCode all have this item; scenario 3 wanted it.

### 3.6 Built-in tools, consumed

- `web_search` and `web_fetch` as **MCP servers consumed behind the component port**: wigolo first
  (zero cost, local, AGPL at arm's length in its own process), `ddgs` as the lighter alternative;
  the effect profile says `reaches`, so `confined` refuses it and `open` allows it — no new rule.
- Nothing is built. A "batteries" TOML lists what a product wants switched on.

### 3.7 The facade (principle 9)

```toml
# harness.toml
[environment]  root = "."  mode = "workspace-write"
[provider]     want = "auto"            # or claude-code | codex | opencode | a key
[modes]        default = "confined"     # looking | confined | open | <your own>
[tools]        web = "wigolo"           # consumed, not built
[skills]       shipped = true
```

```python
from shadow_hdk import Harness

async with Harness.load("harness.toml") as h:
    async for part in h.turn("add a .gitignore and run the tests"):
        ...  # activity and record, in order, as parts
```

```
shadow-hdk serve harness.toml --stdio      # a host in TypeScript talks the protocol
```

The three lines are the whole surface for a product that wants defaults; every port underneath is
what it always was.

### 3.8 Any language

- `shadow-hdk serve`: stdio JSONL (Codex's default) and HTTP/SSE (ours); WebSocket if a
  product asks.
- A TypeScript package generated from the published schemas at build time, held by the same
  invariant that holds the schemas; a thin client (`turn`, `answer`, `setMode`, `interrupt`,
  streams).
- The studio consumes the wire like any other host would — nothing local.

### 3.9 Terminology in code

The table in §1.9, applied: `Thread`, `Turn`, `Item`, `delta`, `ApprovalRequest`,
`InputRequest`, `set_mode`/`set_option`, `reasoning`, `usage`. `Lease` stays; the facade and the
TOML say `budget`. One contract change, first thing in Phase 25.

### 3.10 Live or substrate — what changes without a restart (principle 10)

The mechanism is one the tree already has: a registry is a **union of sources** (D54's shape —
shipped · file · minted · kept · the host's own) and the runtime **refreshes registries at step
boundaries** (`registry.refresh()` has done this for components since Phase 5). Two additions make
every configurable thing live: a **`Store` port** (CRUD plus change notification; sqlite shipped,
a product's database behind it) as one more source for every registry, and the refresh discipline
extended from components to all of them.

| Thing | Live (CRUD, next step/turn) or substrate (code, restart) | How |
|---|---|---|
| Modes — policy + behaviour + presentation | **live** | `ModeRegistry`: shipped · files (`modes/*.md`) · store; a thread's current mode is `set_mode` |
| Behaviours — role, model, effort, temperature, tools offered | **live** | part of the mode registry, or their own; a change reopens the provider session with the new profile, resuming the thread |
| Policy rules — allow / ask / deny, "approve and add a rule" | **live** | `RuleRegistry` feeding governance; a rule added from an approval is a store write through the sink |
| Skills | **live** (Phase 24) | already a registry of sources; the store is one more |
| Which tools are on; MCP servers registered | **live** | the component registry gains a store source; a server registered at runtime connects at the next refresh |
| Providers — which CLI or key a thread uses; provider *definitions* (TOML) | **live** | `Provider` is data (D40); a store row is a provider like a file is; detection is a probe, not a restart |
| Budgets (lease defaults per mode or thread) | **live** | data on the mode; a running thread's lease is what it was granted |
| Vocabulary — registry name, activity labels, question wording, mode names | **live** | data with defaults (principle 8) |
| Environment mode of a thread | **live per thread** (built, D76) | a mode names the environment mode it needs; `set_mode` re-opens the environment (a proof runs again), then reopens the provider on its own session so its catalogue follows |
| The workspace — which directories a thread works on | **live per thread** (built, D76) | one or many roots named at `thread/start`; `thread/add_root` re-opens the environment over the new set, proven again; `WorkspaceChanged` on the record |
| Threads — create, resume, fork, rollback, list, archive | **live** | `ThreadStore` |
| Kernel contracts (event kinds, effect profile fields, schemas) | **substrate** | code; a minor version of every package (D9) |
| The loop (governance, leases, the record, activity) | **substrate** | code |
| Ports — adding one | **substrate** | code |
| Adapters — a new sandbox backend, transport, model, store *implementation* | **substrate** to add; **live** to enable | code to write; a store row to switch on once installed |
| Transports and the server (stdio, HTTP, WebSocket) | **substrate** | code |

Two invariants hold the line: **every registry has a store source** (a test walks the registries)
and **nothing in the live column is read from a file the runtime cannot also read from a store**.
Over the wire (Phase 26) the store's CRUD is exposed as methods — `modes/list`, `modes/create`,
`skills/…`, `rules/…` — so a product's admin UI is a client like any other.

## 4. Phases — accepted by the owner 2026-09-12

Bigger than a hardening round; three phases, each releasable, in `deps` order. The studio goes
through the wire in 26, once the handles cross; in 25 it consumes the primitives in-process.

| # | Name | deps | Delivers |
|---|---|---|---|
| 25 | **The host's controls** | 24 | The terminology (1.9, 3.9) as the first contract change; Activity (3.1); `Thread` and `Turn` (3.2, 1.9); Modes = policy + behaviour (3.3); `set_mode`/`set_option` (3.4); approval and input requests with rules (3.5); **the `Store` port and every registry live (3.10)**; the studio consuming them — collapsed item runs, streamed thinking and text, a mode selector, an input-request item |
| 26 | **Any language** | 25 | `serve` with stdio; handles over the wire; **the store's CRUD as methods**; generated TypeScript; the studio rewritten on the wire only; parity invariant over handles |
| 27 | **Batteries and the facade** | 25 | web search/fetch consumed; `harness.toml` + `Harness.load`; the coder and host examples reduced to the facade; the DSPy optimiser port *specified*, not built |

Context engineering and collaboration (today's 25/26) move to 29/30 — Phase 28 is the workspace, opened 2026-09-12 from the owner's review; nothing in them depends on
being earlier. The roadmap says so.

## 4a. Simple to use, deep by choice — how the architecture makes both true

The principle: **the simple surface is composition of the same parts, never a second engine.**
Six layers, each built only on the one below; a product enters at any layer and goes one deeper
only when it needs to.

```
 6  Server      shadow-hdk serve harness.toml                 ← any language, same file
 5  Facade      Harness.load("harness.toml"); thread.turn(...)     ← three lines
 4  Profiles    harness.toml · modes/*.md · providers/*.toml       ← data, no code
 3  Adapters    seatbelt · OpenSandbox · MCP · LangChain · jsonl/ACP · sqlite · OTel · wigolo
 2  Runtime     the loop: governance by effects, leases, the record, threads/turns, approvals, activity
 1  Ports       Model · Component · Governance · Sink · Observer · Clock · Agent · Isolation · ThreadStore
 0  Contracts   events, effects, behaviours, modes — one set of JSON schemas
```

The ladder a product climbs — each rung is the previous plus one knob:

1. **Data only.** `harness.toml` and `Harness.load()`: environment mode, a mode list, a provider,
   tools, skills. Nothing to write.
2. **Override one thing in code.** `Harness.load(..., governance=MyPolicy())` — one port swapped,
   the rest default.
3. **Compose the ports yourself.** `Ports(...)`, as the examples do today.
4. **Write an adapter.** A new sandbox, tool source or provider: a file behind a port; the loop is
   untouched.
5. **Bring your own store, approval UI, mode list.** Implement a port — or do not use the
   component.

Two guarantees keep "easy" and "deep" one system rather than two, and both are invariants:
**the facade uses only public port APIs** (nothing is reachable at rung 1 that is not at rung 3),
and **every key in `harness.toml` maps to a port or a profile** (no behaviour hidden in the
loader). This is how Django's settings, Rails' conventions and Kubernetes' manifests stay both
simple and deep.

## 5. What is not proposed

- Building a search engine, a browser, a memory, an optimiser: consumed when their phase comes.
- A "classifier judges" auto mode: a `GovernancePort` backed by a model is a one-file adapter when
  a product wants it; nothing in the loop changes.
- Changing the record's shape: activity is beside it, not in it.

## Sources read

- Codex App Server: [complete guide](https://codex.danielvaughan.com/2026/04/15/codex-app-server-complete-guide/), [config reference](https://learn.chatgpt.com/docs/config-file/config-reference), [app-server README](https://github.com/openai/codex/blob/main/codex-rs/app-server/README.md)
- Claude Code: [permissions and modes](https://code.claude.com/docs/en/permissions), [Agent SDK overview](https://code.claude.com/docs/en/agent-sdk/overview)
- OpenCode: [agents](https://opencode.ai/docs/agents/)
- Agent Client Protocol: [session modes](https://agentclientprotocol.com/protocol/session-modes)
- DSPy: [dspy.ai](https://dspy.ai/)
- wigolo: [repo](https://github.com/KnockOutEZ/wigolo)
- Vercel AI SDK: [message parts](https://sdk.vercel.ai/docs/ai-sdk-ui/chatbot-with-tool-calling)
- Measured here: Claude Code 2.1.235 `-p --include-partial-messages` emits `thinking_delta`/`text_delta` and a thinking summary (two calls, 8¢, 2026-09-12)
