---
type: Research
---

# How comparable runtimes do it — persistence, threads, interrupts, tenancy, config, local + cloud

> **Date**: 2026-09-14 · **Why**: before the kit takes on production concerns (a store choice,
> durable parked runs, thread concurrency, identity, live batteries), see what the systems that
> play the same role chose — and where they agree. **Scope**: the *runtime / kit* level, not the
> product level (the product patterns are in `intent-ecosystem/vision/13` §2). Read from primary
> documentation on the date above; sources at the end. The harness stays generic: nothing here is
> Intent Studio's shape — it is the shape any product would need.

## The systems compared

| system | what it is | why it is comparable |
|---|---|---|
| **LangGraph Server / Platform** | the hosted form of the library the harness runs on: assistants, threads, runs, a store, cron | the same graph code runs locally (`langgraph dev`) and hosted; explicit answers on persistence, concurrency, auth |
| **OpenAI Agents SDK** (Python) | an agent loop with a `Session` protocol for conversation history | the storage question answered as a protocol with many backends |
| **Google ADK** | agents + a `Runner` over `SessionService`, `ArtifactService`, `MemoryService` | identity is *in* the session model |
| **OpenAI Codex app-server** | the JSON-RPC server behind every Codex surface (CLI, IDE, app, cloud) — thread · turn · item | the shape the harness's wire copied (D67); durable threads; approvals as server→client requests |
| **Claude Managed Agents** | Anthropic's hosted harness: agent, environment, session, events; self-hosted sandboxes | the "loop on the server, tools on your machine" shape, done at scale |
| **Claude Agent SDK / Claude Code** | the local loop; permission modes, rules, hooks, `canUseTool` | the most worked-out permission evaluation order in the field |
| **Mastra** (TypeScript) | agents, workflows, memory with interchangeable storage | storage per domain; suspend/resume persisted |
| **Goose** (Block, Rust) | a local agent: `goosed` server shared by the desktop app and the CLI, extensions as MCP servers | the local-server-plus-clients shape; sessions in SQLite |

## 1 · Persistence

| system | how |
|---|---|
| LangGraph | a *checkpointer* saves state at every superstep; `InMemory` for tests, `SQLite` "for single-process workloads", `Postgres` or Redis "for multi-process deployments"; the Platform runs on Postgres. A separate *store* for cross-thread memory, namespaced. |
| OpenAI Agents SDK | `Session` is a four-method protocol (`get_items`, `add_items`, `pop_item`, `clear_session`); shipped: SQLite, SQLAlchemy (any RDBMS), Redis, MongoDB, Dapr, an encrypted wrapper, and OpenAI-hosted conversations; "custom implementations following the protocol" are expected. |
| Google ADK | `SessionService`: `InMemory`, `Database` (any SQLAlchemy URL — sqlite, postgres, mysql — "with row-level locking for concurrent safety"), `VertexAi`. |
| Codex app-server | threads "survive process restarts and can be resumed by ID"; `thread/read` returns the full history; threads unload from memory after 30 minutes idle and are reloaded on demand. |
| Managed Agents | sessions are "append-only, durable event logs stored completely outside the container … survive container crashes and harness restarts". |
| Mastra | storage providers "interchangeable — libsql in development, postgres in production, and your code works the same"; *composite* storage picks a backend per domain (workflows, memory, observability). |
| Goose | one SQLite `sessions.db` behind a connection pool, for a single user's machine. |

**Consensus.** Every multi-user system exposes persistence as a small interface with *shipped*
implementations, SQLite for one process and a relational database for many. SQLite is a
development and single-node default everywhere; nowhere is it the ceiling. The interfaces are
small (four to six methods) — which is what makes the backends interchangeable.

**The kit today.** Two ports of the same size — `Store` (put · get · delete · list · version) and
`ThreadStore` (create · get · save · list) — with SQLite and in-memory implementations. Right
shape; only one backend, and no way to choose it from `harness.toml`. A third persisted thing,
the parked run's checkpoint, is `InMemorySaver` per wire session (see §2).

## 2 · Interrupts that survive — the parked run

| system | how |
|---|---|
| LangGraph | `interrupt()` is persisted with the checkpoint; a human-in-the-loop pause survives restarts and is resumed by thread id with the answer. |
| Mastra | workflow `suspend()` writes a snapshot; `resume()` rehydrates it — "durable snapshots that must be available when a run resumes". |
| Managed Agents | the session's event log is the durable thing; a session "resumes cleanly after pauses". |
| Codex app-server | an approval is a server→client JSON-RPC request answered `accept` · `decline` · `cancel` · `acceptWithExecpolicyAmendment`; the thread is durable, the pending request is bound to the live turn. |
| Claude Agent SDK | `canUseTool` is a callback in the live query; a resumed session starts a new query. |

**Consensus.** Where a pause is meant to outlive a connection, the paused state is written by the
*same* persistence the conversation uses. Where it is bound to a live connection (Codex, the Agent
SDK), the pending question dies with the connection and the thread is resumed afresh.

**The kit today.** The record says `parked`; the resumable state is in a per-session in-memory
checkpointer. A page closed on an approval card loses the run. The kit already depends on
`langgraph-checkpoint-sqlite` (dev) and LangGraph ships Postgres checkpointers: the checkpointer
should follow the store choice.

## 3 · Two people, one thread — concurrency

| system | how |
|---|---|
| LangGraph Server | "double texting" is named and has four strategies per run: `reject`, `enqueue` (default), `interrupt`, `rollback`. |
| Google ADK | row-level locking in `DatabaseSessionService`. |
| Codex app-server | a *thread manager* with per-thread state and per-connection subscriptions: many clients may **subscribe** to one thread over WebSocket; stdio is single-client. |

**The kit today.** "no thread … is open on this wire" — one session opens a thread; nothing stops a
second session (or process) resuming the same thread and getting a second provider on the same CLI
session. There is no named strategy.

## 4 · Identity and tenancy

| system | how |
|---|---|
| LangGraph Server | `@auth.authenticate` turns a request into an identity (`identity`, `permissions`, any custom fields such as `org_id`); `@auth.on.<resource>.<action>` handlers **stamp** `owner` metadata at creation and **return a filter** on read/search — per-user isolation by metadata, on threads, assistants, crons and the store (by namespace). |
| Google ADK | `app_name` and `user_id` are fields of the session itself; state is scoped `user:` / `app:` / session / `temp:`. |
| Mastra | memory is scoped by `resourceId` (the person) and `threadId`. |
| Managed Agents | sessions belong to the API account; **vaults** keep credentials out of the sandbox entirely (a credential proxy injects them into outbound requests). |
| Codex app-server | local: none needed; enterprise: one shared server, WebSocket, signed JWT per developer. |

**Consensus.** The runtime never authenticates a person itself — that is the product's — but its
records **carry the owner** and every read is **filtered by it**. Tenancy is a key on the
session/thread, not a process boundary.

**The kit today.** Identity is the product's (right). But the thread shape carries no principal
(`Context.principal` exists; only the older `run` shape sets it), and rules and modes are rows with
no owner or scope — a rule from one person's *approve & don't ask again* applies to every thread
in the process. Multi-tenancy today is by process: one harness (and store) per tenant.

## 5 · Configuration — what is live, what needs a restart

| system | how |
|---|---|
| LangGraph Server | an *assistant* is a versioned configuration stored in the database, created and changed over the API — live. The graph *code* is the deployment. |
| Codex app-server | a `config` domain over the protocol: `config/read`, `config/value/write`, `config/batchWrite`; layered config files; MCP servers configured the same way. |
| Claude Agent SDK | the permission mode is switchable mid-session (`setPermissionMode`); rules live in `settings.json` at user / project / local scope and in managed settings that flow from the organisation. |
| Goose | extensions (MCP servers) are enabled per session. |

**Consensus.** Policy-level things — modes, rules, which tools are on — are data, changed through
the API while the process runs; the deployment (code, listeners, where the store is) is the thing
that restarts.

**The kit today.** Modes, rules, skills and switches are live rows (D66) — matches. Batteries are
opened once per process from `[tools] batteries` — the one registry on the wrong side. Budget
defaults are a file key only.

## 6 · Local and cloud — the same runtime in two places

| system | how |
|---|---|
| Codex | one app-server behind every surface; locally over stdio or WebSocket; the local server **connects outward** to a relay for Remote Control; cloud runs the same harness in a VM. |
| Claude Code / Agent SDK | the loop runs where the files are; Remote Control and self-hosted runners **poll outbound**; the transcript is kept server-side to resume elsewhere. |
| Managed Agents (self-hosted sandbox) | the *inverse*: the loop stays on Anthropic's side, an **environment worker** on your infrastructure polls a queue over outbound HTTPS, executes tools in `/workspace`, posts results; conversation state stays with the control plane; file tools are confined to `allowed_roots` / `read_only_roots`. |
| LangGraph | the same graph runs under `langgraph dev` and under the hosted server; persistence is what changes. |
| Goose | a local server (`goosed`) shared by an Electron app and a CLI; sessions local. |

**Consensus.** Both shapes exist in production at scale — *loop on the machine* (Codex, Claude
Code, Goose) and *loop in the control plane, tools on the machine* (Managed Agents self-hosted).
What they share: **no inbound connections to the machine**, a **queue with a lease** as the
heartbeat, the **record kept where it can be resumed from anywhere**, and **one runtime binary**
that is the same locally and hosted. `vision/13` adopted the first shape (B) for the BYO
subscription and keeps the second as the cloud runner; the research supports that as the
mainstream choice, with Anthropic's self-hosted sandbox as the strongest example of the other.

**The kit today.** One runtime, importable in-process (the runner) and servable (the cloud runner)
— matches. What the product's server needs from it — to be the *sink*, the *policy source*, the
*ledger* and the *queue* — is exactly the ports: `Sink`, `Store`/`ThreadStore`, the governance
port, the observer. The ports exist; what is missing is choosing their implementation at deploy
time without Python.

## 7 · The permission model — how a call is judged

| system | how |
|---|---|
| Claude Agent SDK | a fixed order: hooks → deny rules → ask rules → permission mode → allow rules → `canUseTool`. Deny rules hold even in `bypassPermissions`; some actions are never auto-approved (critical-path removals); modes: `default`, `dontAsk`, `acceptEdits`, `plan`, `bypassPermissions`, `auto` (a classifier). Rules are by tool name and path pattern. |
| Codex | approvals per command / patch, with `acceptWithExecpolicyAmendment` — an approval that also writes a rule. |
| Managed Agents | file tools confined to `allowed_roots`; bash is not. |

**Consensus.** Rules before modes, the person last; an approval can mint a rule; some things no
mode auto-approves. Rules are keyed by *tool name and path* everywhere.

**The kit.** Judgement is by **effects** (six fields), not by name — more general than any of the
above, and the reason an unknown tool is still judged. The order (rules consulted after the mode
says *ask*, D65; a deny rule holds) matches. Two things the field has that the kit does not name:
*never-auto-approved* actions independent of mode, and rules scoped by path within a root.

## What follows for the kit — proposals, not decisions

Each is generic; none is Intent Studio's. Ordered by how much production it unblocks.

| # | proposal | what the field does | what changes in the kit |
|---|---|---|---|
| P1 | **A store choice at deploy time** — `[store] url = "sqlite:///…" \| "postgresql://…"`; a `[postgres]` extra implementing `Store`, `ThreadStore` **and the checkpointer** against one database; `ServeHost(store=…, threads=…, checkpointer=…)` in-process | every system: small interface, shipped SQLite + Postgres | new adapter under the existing contract suites; `serve/config.py` reads a URL; no wire change |
| P2 | **Durable parked runs** — the checkpointer follows the store (SQLite file today; Postgres with P1) | LangGraph, Mastra, Managed Agents | `ServeHost` hands the checkpointer to threads; an approval survives a reload and a restart |
| P3 | **A thread concurrency rule** — a lease on a thread in the store ("open on this process until…"), and a named strategy for a second `turn/start` while one runs: `reject` \| `enqueue` (default) \| `interrupt` | LangGraph's four strategies; ADK's row locks; Codex's subscriptions | `ThreadStore` gains `lease`/`release`; `turn/start {multitask}`; the wire refuses or queues by name |
| P4 | **Identity on the thread; scope on the rows** — `thread/start {principal, scope}` carried into every judgement and stamped on the record; `ModeSpec` and `ActRule` gain `scope` (a principal or a tenant) and the registries filter by it; a rule minted from a card is scoped to who answered | LangGraph's owner metadata + filters; ADK's `user_id`; Mastra's `resourceId` | small schema additions (contract change, minor bump); the product's backend supplies the principal it already has |
| P5 | **Batteries live** — the battery registry read like the others; `[tools] batteries` becomes the initial set; a row or a file switches one on or off at the next thread | Goose per-session extensions; Codex config methods | `open_batteries` moves from host open to thread open, held per thread or per process by refcount |
| P6 | **Budget as thread data, spend on the record** — `thread/start {budget}`; spent steps/seconds/cents on `ThreadRecord` (ENH-013) | Managed Agents meters per session | closes ENH-013 |
| P7 | **Named never-auto-approved actions and path-scoped rules** — an effect profile flag a mode cannot widen; `ActRule.inputs` path patterns anchored to a root | Claude Agent SDK's critical paths and `Edit(//path)` rules | kernel + modes adapter |
| P8 | **Operations** — a health endpoint, an admin listing of sessions/threads, per-run tokens (the documented debt) | every hosted system | `wire/serve.py` |

What the field does **not** do, and the kit should keep: judgement by effects rather than names;
the person as a component (`ask_person`) beside the person as a port; a mode as a document that
names its own sandbox mode; the record as the one truth every surface renders.

## Sources

- LangGraph: [double texting](https://docs.langchain.com/langgraph-platform/double-texting) · [authentication & access control](https://docs.langchain.com/langsmith/auth) · [langgraph.checkpoint reference](https://reference.langchain.com/python/langgraph.checkpoint) · [checkpointers, threads and recovery (2026)](https://eastondev.com/blog/en/posts/ai/20260424-langgraph-agent-architecture/)
- OpenAI Agents SDK: [Sessions](https://openai.github.io/openai-agents-python/sessions/)
- Google ADK: [Session](https://adk.dev/sessions/session/)
- Codex app-server: [developers.openai.com/codex/app-server](https://developers.openai.com/codex/app-server) · [the protocol, a complete guide (2026-04)](https://codex.danielvaughan.com/2026/04/15/codex-app-server-complete-guide/) · [openai/codex app-server README](https://github.com/openai/codex/blob/main/codex-rs/app-server/README.md)
- Claude Managed Agents: [overview](https://platform.claude.com/docs/en/managed-agents/overview) · [self-hosted sandboxes](https://platform.claude.com/docs/en/managed-agents/self-hosted-sandboxes)
- Claude Agent SDK: [configure permissions](https://code.claude.com/docs/en/agent-sdk/permissions)
- Mastra: [storage](https://mastra.ai/en/docs/storage/overview) · [composite storage](https://mastra.ai/reference/storage/composite) · [changelog 2026-01-20](https://mastra.ai/blog/changelog-2026-01-20)
- Goose: [session management (DeepWiki)](https://deepwiki.com/block/goose/4.3-session-management) · [block/goose](https://deepwiki.com/block/goose)
