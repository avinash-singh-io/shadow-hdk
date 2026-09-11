---
type: Roadmap
---

# Roadmap — shadow-hdk

> **Start Date**: 2026-09-10

## Vision

A governed, composable agent runtime any system can adopt by implementing six ports — from one
deterministic agent with a few tools to dynamic multi-agent work acting on the physical world —
growing only by adapters and pattern files, never by runtime branches.

## Order

**Ordering is computed from each phase's `deps`, never from this list.** A phase runs when what it
needs exists; where two are free at once, the one that closes a gap in the runtime's own story comes
first.

**Adopters do not appear in this document.** The harness is a library: it is finished when its own
contracts hold, not when somebody has used them. Which release of which product a phase happens to
unblock is a fact about that product, and it lives in the shared roadmap
(`intent-ecosystem/vision/10-the-roadmap.md`) with the joins on `intent-ecosystem/lanes/board.md`.
Keeping it there is what stops this plan from being re-ordered by somebody else's schedule — and
what stops a capability from being called done because one caller happens not to need the rest of
it.

## Where this stands — 2026-09-12

**Phases 0–24 are done** and v0.20.0 is released. Then the harness was *used* for a day — five
real tasks through the studio on a subscription — and that found seven bugs (all closed) and a
shape the reference implementations agree on and we lacked: a **turn** on the record, **activity**
streaming beside it, **modes** that carry a behaviour and switch mid-run, **questions** that a host
in any language can answer and that the agent itself can raise. `specs/planning/the-substrate.md`
is the grounded plan; phases 25–27 below are it. Context engineering and collaboration move to
28 and 29 unchanged.

### Where this stood — 2026-09-11

**Phases 0–24 are done**, merged and released; the latest is **v0.18.0** (Phase 24): 1,153 tests,
mypy strict over 198 files, seventeen distributions, all MIT. The consumable line is reached: a
host hands in its own governance, record, checkpointer and view and runs a brief through a key or
the subscription signed in on its machine, in-process or over the wire at parity; a
subscription-backed agent reasons on the record, acts through the run's own environment inside the
OS sandbox, and its process dies with the host's.

**Doing that found the most serious defect this runtime has had**, and it is worth stating in the
plan because it re-ordered the plan. Three adapters, in three packages that cannot import each
other, declared `reads/writes: {workspace}` for operations that reach the whole machine — a plain
subprocess honours nothing but its working directory. Governance judged those declarations and
approved, correctly, a lie. The enforcement was never wrong; the input was. It is fixed three times
and guarded once: `test_every_narrow_scope_is_enforced.py` makes *a narrow scope must name what
makes it true* a build failure rather than a habit.

**The lesson generalises, and it is the reason the next phases look the way they do.** Confinement
is a property of the **environment** an agent runs in, not of individual tools — the model every
mature agent already uses (a mode: read-only, workspace-write, full; enforced once, true for every
operation). Three separate tool adapters each holding an opinion about the same boundary was the
architecture that produced the bug.

**What was surveyed, late.** Before Phase 21 a proper survey was done of what already exists — it
should have preceded Phase 3 and did not. The finding: the *loop* here is the one thing nobody else
has (governance by effects with a partial order, leases carved to children, a runtime with no write
path, subscription providers, physical devices, embeddable in-process), and nearly everything
around it is commodity that mature projects do better. So the line is drawn: **build the loop,
consume the rest**. Sandboxing is the first thing consumed.

| | phases | state |
|---|---|---|
| done | 0 – 19 | merged and released |
| done | 20 — providers | two seams (D39); a provider is a file (D40); asked never read (D41); the socket (D42); the loop stays theirs (D43); the relay (D44) |
| done | 21 — the visible agent | `Reasoned` (D45); steps folded once, crossing the wire folded (D46); a large result held, never written (D47) |
| done | 22 — the environment | one concept with a mode (D48); local on the OS sandbox, proven (D49); isolated behind a Box, two denials (D50); three adapters deleted |
| done | 23 — a host, in-process and in any language | the agent runs where the record is (D51); the socket authenticated (D52); a child dies with its process (D53); a host example; parity held by invariants — **the consumable line, reached** |
| done | 24 — the skill registry | a skill says what it is for and where it came from (D54); the registry is a component, so choosing is on the record and reaches every host (D55); minting proposes, keeping is the host's (D56) |
| the owner's | 25 — context engineering · 26 — collaboration | not started; the four phases the owner asked for end here |
| `[~]` | OPC-UA, ROS 2 (epic 0007) | need a server and a ROS distribution |

**Decisions settled so far:** D1–D38 as before; D39 inference and agency are two seams, D40 a
provider is data, D41 the harness asks and never reads a credential, D42 every effect routes through
the run's registry whoever asked, D43 the loop stays the provider's, D44 the registry is offered on a
loopback socket through a relay (phase 20); D45–D47 the visible agent (phase 21); D48–D50 the
environment (phase 22); D51 the agent runs where the record is, D52 the socket is authenticated,
D53 a child dies with its process (phase 23); D54 a skill says what it is for, D55 the registry is
a component, D56 minting proposes and keeping is the host's (phase 24).

**Still with the owner:** ADR-1 and ADR-2, and landing Phase 20.

## Timeline

| Phase | Name | Status | deps | Key Deliverables |
|-------|------|--------|------|------------------|
| 0 | The runtime — the bare test goes green | **DONE** · `phase-0-the-runtime` | — | `run(composition, ports)`; compile to LangGraph; the governed step; leases, events, proposals, children; the agent as a component with the `single` pattern; `basic` adapters incl. `callable`; testing doubles; replay determinism; the benchmark |
| 1 | Real adapters, streaming, modes | **DONE** · `phase-1-real-adapters` | 0 | `adapters/langchain` (one `ModelPort` over LangChain's providers — OpenAI-compatible, Anthropic, Ollama, HuggingFace, …) with `stream`; `adapters/mcp` (annotations → half a profile); `adapters/modes`; the demo on real components |
| 2 | The spike | **DONE** · `phase-2-the-spike` | 0 | half a day over `agent-client-protocol`: does a refused tool call end a CLI's turn cleanly; does ACP report usage |
| 3 | The workspace and code | **DONE** · `phase-3-workspace-and-code` | 1 | `adapters/workspace` (files within a root, `writes: {workspace}`); `adapters/sandbox_subprocess` (run code with limits; `contained` per deployment) — the agent writes files, pages and code |
| 4 | The ACP bridge | **DONE** · `phase-4-the-acp-bridge` | 1, 2 | Codex or Claude Code as a component, resident for the session |
| 5 | The RecordingServer | **DONE** · `phase-5-the-recording-server` | 1, 4 | an MCP server exposing the registry to a child agent; every call an observation with `posture: observed` |
| 6 | The compiler, complete | **DONE** · `phase-6-the-compiler-complete` | 0 | nested composites as subgraphs, checkpoint namespaces, `resume`, cancellation, host checkpointers |
| 7 | Sub-agents | **DONE** · `phase-7-sub-agents` | 6 | spawn · send · release; held children; branch-level cancel; `run.*` events |
| 8 | Patterns, skills, replay | **DONE** · `phase-8-patterns-skills-replay` | 7 | `plan-and-execute`, `orchestrator-workers`, `critic-pair`, `reflect-until`; skill file loader; compaction component; recorded model port; catalogue compaction (`describe`) |
| 9 | The wire | **DONE** · `phase-9-the-wire` | 6, 7 | `serve` (JSON-RPC 2.0 over HTTP/2 + SSE), `--stdio`; schemas published. The tag is the owner's and is now **`v0.12.0`** — twelve contract changes have moved every package under D9 since this row was written |
| 10 | Effect rules | **DONE** · `phase-10-effect-rules` | 0 | rules as rows over profiles, intersection, the narrowing check as a library, mode files |
| 11 | Contained sandboxes | **DONE here** · live proofs `[~]` Linux · `phase-11-contained-sandboxes` | 3 | gVisor, Firecracker as `contained: true` components |
| 12 | Derivation | **DONE** · `phase-12-derivation` | 0 | total expressions over typed tables, fixed-point arithmetic, re-executable grounds |
| 13 | Leases on effects, driver supply chain | **DONE** (mechanism; policy `[~]` ADR-1) | 7, 9 | `EffectPort` takes a lease; keys, signatures, receipts, revocation |
| 14 | Telemetry | **DONE** | 0 | OpenTelemetry observer; file sink |
| — | **The environment** (epic 0007) | **DONE** for phases 15 and 16; OPC-UA and ROS 2 `[~]` | 3, 7, 13 | protocol adapters for devices — MQTT, OPC-UA, ROS 2 — sensors as `reads: {world}`, actuators as irreversible writes; controlled vs observed posture |
| 17 | The audit's P0s | **DONE** · `phase-17-the-audit` | 16 | the lease survives a park (D33); an assistant message carries its tool calls; resume over the wire, `initialize` required, callbacks timed out, `serve` loopback-only (D34); the gate widened to every package |
| 18 | The audit's P1s | **DONE** · `phase-18-the-p1s` | 17 | the workspace confined against hard links; a step owns its process tree (D35); containment proven by what is denied (D36); a parent keeps its children across a park (D37); a parked step resumes where it parked and the human's answer decides (D38); the ACP purse charges the step and a deaf child is killed; five agent promises kept; packaging pinned and typed; **CI made to run at all** |
| 19 | The P2s | **DONE** · `phase-19-the-p2s` | 18 | BUG-016 the adapter cache; BUG-013 a derivation answers rather than raises; BUG-014 a crash costs the record nothing; TD-004 every port held to its contract; TD-005 growth bounded or argued; TD-006 a stop signal is not an ordinary exception (contract 0.13.0); TD-007 plumbing, its policy the owner's; TD-008 the documents, kept honest by an invariant |
| 20 | Providers | **DONE** · `phase-20-providers` | 4, 5 | two seams — bring your own key, or your own subscription; a provider is a file; the socket closes around a child's effects |
| 21 | The visible agent | **DONE** · `phase-21-the-visible-agent` | 20 | `Reasoned`, the twelfth event kind; a projection of the stream any client renders as agent steps, over SSE and in-process; deferred tool schemas; large-result offloading |
| 22 | The environment | **DONE** · `phase-22-the-environment` | 21 | one concept with a mode, enforced by the environment; local on the OS sandbox; isolation consumed, not built; three adapters become one |
| 23 | A host, in-process and in any language | **DONE** · `phase-23-a-host-in-any-language` | 21, 22 | a real host consumes the runtime; the wire held to parity; socket authentication; the live proof on demand — **the consumable line** |
| 24 | The skill registry | **DONE** · `phase-24-the-skill-registry` | 23 | skills predefined, minted in a run, proposed for keeping through the sink; progressive disclosure |
| 25 | The host's controls | planned | 24 | the industry's terms (thread, turn, item, delta, approval request); activity beside the record; `Thread` as a component with turns on the record; modes = policy + behaviour + presentation, `set_mode`; approval and input requests, with "add a rule"; the `Store` port — every registry live, no restart |
| 26 | Any language | planned | 25 | `serve` over stdio and HTTP; every host handle crosses the wire; the store's CRUD as methods; TypeScript generated from the schemas; the studio on the wire only |
| 27 | Batteries and the facade | planned | 25 | web search and fetch consumed; `harness.toml` and `Harness.load()`; the optimiser port specified |
| 28 | Context engineering | planned | 21, 22 | compaction that triggers itself; Code Mode over the socket; memory consumed |
| 29 | Collaboration | planned | 23, 24 | agents as peers; a second agent protocol as a file plus one adapter; the next providers measured |

## What comes next — the consumable line

**The harness is generic.** Nothing below is about coding. An *environment* is wherever effects
land — a filesystem and a shell for one agent, a browser for another, the physical world for a
third (D29). *Skills* are a registry of things an agent can do, predefined or minted during a run
and proposed for keeping. *The visible agent* is any model's reasoning on any run. The first host
happens to be a Python application embedding the runtime in-process; the wire (D21) makes the same
runtime reachable from any language, and Phase 23 holds the two to parity.

**The line is drawn at Phase 23.** Past it the runtime is consumable and grows by adapters and
files; the phases after it are capability, not readiness.

| Phase | Name | Deps | What it makes true |
|---|---|---|---|
| **21** | **The visible agent** | 20 | A twelfth event kind, `Reasoned`: what the model thought, on the stream beside what it did — the same record a person reads as *agent steps*. A **projection** of the event stream shaped for a client to render (steps, nested sub-agents, spend, refusals, questions), served over SSE by the wire and available in-process as an async iterator. **Deferred tool schemas**: a registry of two hundred tools costs a name and a line each until one is chosen. **Large-result offloading**: an observation over a threshold lands in the environment as a file and the stream carries a handle and a preview. These three are what a benchmarked competitor credits for a 30–75% cost advantage over a managed loop; they are cheap here. |
| **22** | **The environment** | 21 | `workspace`, `sandbox_subprocess` and `contained` become **one concept with a mode** — `read-only`, `workspace-write`, `full` — enforced by the environment, true for every operation in it, and the effect profile derived from environment × mode × operation once (BUG-018's class, closed by shape rather than by invariant). `LocalEnvironment` on the OS sandbox (seatbelt on macOS; Landlock on Linux) — the model the mature coding agents use. `SandboxEnvironment` **consuming** an existing sandbox platform behind the `IsolationBackend` seam with the root mounted in, isolation proven by what is denied (D36). The hand-rolled gVisor and Firecracker wrappers are deleted. Widening — *may I read elsewhere?* — is an `Ask`. |
| **23** | **A host, in-process and in any language** | 21, 22 | The runtime consumed by a real host: its own governance, sink and checkpointer handed in; the visible-agent projection rendered by its UI; a subscription provider or a key, its choice. The **wire held to parity** with in-process — every event kind, the projection, resume, and the registry offered outward — so a host in another language is not a second-class one. Socket authentication (D44's debt). The live proof runnable on demand. This is the consumable line. |
| 24 | The skill registry | 23 | Skills as a **registry** rather than a directory: predefined, minted during a run, and *proposed for keeping* through the sink — which is what makes self-evolution a governed act rather than a side effect. Progressive disclosure: a skill costs a name and a line until it is chosen. Promotion is a host decision. |
| **25** | **The host's controls** | 24 | What every product that ships an agent has and we measured we lacked (`the-substrate.md` §1). **Activity**: an ephemeral stream beside the record — partial thinking, partial text, a running command's output, "composing" — never checkpointed (principle 6). **Conversation**: the thread-of-turns moved out of the example into the harness; a turn is a *step* of the conversation's run, so Thread → Turn → Item is Run → Step → child steps with no new concept; `steer` and `interrupt`. **Modes** = policy + `Behaviour` (role, model, effort, temperature, tools offered) + presentation, authored as data, the provider file mapping behaviour to that CLI's flags; the three defaults per environment mode shipped, not exampled. **Dials**: a host handle turned mid-run; `Dialed` on the record. **Questions both ways**: "allow, and add this rule" proposed through the sink; `ask_person` for the agent's own questions. The studio consumes all of it: collapsed step runs, streamed thinking and text, a mode selector, a question item. |
| **26** | **Any language** | 25 | `shadow-hdk serve` over stdio JSONL (Codex's default) and HTTP/SSE; **every host handle crosses the wire** — questions, dials, cancellation — and the parity invariant covers handles; a TypeScript package generated from the published schemas at build time; the studio rewritten to consume the wire and nothing local, which is how a product in another language would. |
| 27 | Batteries and the facade | 25 | `web_search` and `web_fetch` consumed as MCP servers behind the component port (wigolo first, `ddgs` as the light alternative), `reaches` so the modes already judge them. `harness.toml` — environment, modes, provider, tools, skills — and `Harness.load()`: three lines for a product that wants defaults, every port open underneath (principle 9); the coder and host examples reduced to it. The optimiser port (DSPy behind it, later) *specified*, not built — Rule 11 first. |
| 28 | Context engineering | 21, 22 | Compaction that triggers itself (D18's meta-tool made automatic at a threshold). **Code Mode**: a script the agent writes runs in the environment and calls the run's registry directly — which the socket (D42, D44) already permits — so only what it prints enters context. Memory consumed as a component, never built. |
| 29 | Collaboration | 23, 24 | Agents as peers: a second agent protocol as a transport (D40 makes it a file plus one adapter); a run that delegates to another host's run over the wire; Codex and the next three providers measured rather than transcribed. |

## Epics

| Epic | Phases |
|---|---|
| 0001 the bare harness | 0, 1, 2 |
| 0002 the workspace, and driving another agent | 3, 4, 5 |
| 0003 composition at scale | 6, 7, 8, 9 |
| 0004 governance as rows | 10 |
| 0005 the body | 11, 13 |
| 0006 derivation | 12 |
| 0007 the environment | 15, 16 |
| — the audit | 17, 18, 19 |
| 0009 bring your own provider | 20 |
| 0010 the visible agent | 21 |
| 0011 the environment | 22 |
| 0012 a host, in any language | 23 |
| 0013 the skill registry | 24 |
| 0014 context engineering | 25 |
| 0015 collaboration | 26 |

Only 0001 is created at founding; each later epic is brainstormed once when reached, its decisions
already settled by `09` where `09` speaks.

## Guiding Principles
1. Ship working software in every phase; each phase leaves every package releasable
2. `deps` order the phases; nothing else does, and no adopter's schedule does
3. Defer scope, not quality — red tests first, contracts round-trip, the benchmark runs
4. A new capability is an adapter or a pattern file; a runtime branch on a name is a defect
5. **Build the loop; consume the rest.** Before an adapter is written, what already exists is surveyed and the survey is recorded. The loop — governance by effects, leases, the sink, the record — is the only thing this repository exists to build; a sandbox, a browser, a memory, a protocol is something it exists to *govern*, and is consumed behind a port. The survey that should have preceded Phase 3 was done before Phase 21, and it re-ordered the plan.
6. **The record is complete; the activity is live.** Everything that happened is on the record, once, replayable. Everything that is *happening* — a token, a line of output — is on an ephemeral stream beside it, never checkpointed, never required for correctness.
7. **A host holds handles, not code.** What a person does *during* a run — answer, cancel, turn a dial, steer — is a handle the host keeps, and every handle crosses the wire, so a host in any language holds the same ones.
8. **A product's vocabulary is the product's.** The registry's name, the labels on activity, the wording of a question, the names of modes: data the host supplies with defaults, never a string a product would have to fork to change.
9. **Simple by default, deep by choice.** A harness is a file and three lines; the same file drives `serve` for a host in another language; every port stays open for a product that composes by hand.
10. **Data changes live; code changes restart.** Modes, behaviours, rules, skills, tools, providers, budgets, vocabulary are registries with a store source, changed by CRUD at runtime and read at the next step; only contracts, the loop, ports, adapters and transports are code, and only code needs a restart.
