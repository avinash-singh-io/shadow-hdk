---
type: Phase
phase: 29
name: one-app-server
status: complete
topics: [store, postgres, checkpointer, parked, lease, concurrency, principal, scope, batteries, budget, rules, operations]
deps: [phase-28-the-workspace]
---

# Phase 29 — One app server behind every surface

**The harness as the one process every surface of a product talks to — a local install, a
web app through its backend, a phone through the same backend, a cloud runner — and what that
needs from it in production**: a record that lives in the database the product chooses; a
parked run that outlives the page that parked it; one thread, one holder; the person's identity
on every judgement and every row; the registries all live; the budget on the record; the rules
the field has and we lacked; and the operations a hosted process owes.

Opened from the owner's decision of 2026-09-14 — *"one app server behind every surface"* —
after the research note `specs/research/2026-09-14-how-comparable-runtimes-do-it.md`, which read
LangGraph Server, the OpenAI Agents SDK, Google ADK, the Codex app-server, Claude Managed
Agents, the Claude Agent SDK, Mastra and Goose against seven axes and found where they agree.
Every group below is one of that note's proposals (P1–P8), made generic: nothing here is one
product's shape.

## What this phase makes true

- **The record chooses its store** (group 1): `[store] url` names SQLite or Postgres; one choice
  fills the `Store`, the `ThreadStore` and the checkpointer; a Postgres adapter behind the same
  contract suites; an in-process host hands the three in.
- **A parked run survives** (group 1): a turn waiting on an approval is on the checkpointer the
  store chose; a page closed, a process restarted — `thread/resume` re-presents the question and
  the answer resumes the run where it parked.
- **One thread, one holder** (group 2): a thread is leased to the process that opened it, the
  lease renewed while it is open and expiring when the process dies; a second `turn/start`
  while one runs is `enqueue` (the default), `reject` or `interrupt` by name.
- **Identity on the thread, scope on the rows** (group 3): `thread/start {principal,
  attributes}` is on the record and in every judgement's context; a mode or a rule may carry a
  `scope`, and the registries read only what is in scope; a rule minted from a card is scoped to
  who answered.
- **Batteries live** (group 4): wanted by rows as well as the file; opened at the next thread
  that wants one, not at the process's start.
- **The budget on the record** (group 5): `thread/start {budget}`; what a thread spent is on
  its record and resumes with it (closes ENH-013).
- **The rules the field has** (group 6): an `ask` rule that holds in every mode; a `deny` rule
  that holds in `full`; path patterns in a rule's inputs, anchored to a root.
- **Operations** (group 7): a health answer, an admin listing of sessions and threads, a
  version on the wire; the per-run token debt closed as a decision.

## What does not change

The kernel's six-field effects, the governed step, the wire's methods a product already calls
(every group adds parameters or methods; none is removed), `harness.toml` files that name
`[store] path` (sugar for a SQLite url), SQLite as the default with nothing configured.
