# Consuming the kit from a product

A development kit does not own the product's shape. Every layer of Shadow HDK is usable without
the layer above it, and every piece of state lives behind a port — so a product enters where
its ownership begins, and keeps everything it already has.

## The four doors

| door | who owns the conversation | who owns the rows | when |
|---|---|---|---|
| `run()` — the governed loop | the product (its own messages) | the product | your product has a conversation model of its own and a model you call yourself |
| `Conversation` — the governed turn | the product | the product | as above, with a provider that owns its loop — a coding CLI on a subscription |
| `Thread` — turns as runs, kept | the kit's record | either (`ThreadStore`) | you want threads, turns, items and parked runs on the record, in-process |
| `Harness` / `serve` — the app server | the kit | one url, or handed in | a Python process behind your backend, or any language over the wire |

The recommended shape for most products is the last door **behind the product's backend**:
users, permissions and the product's tables stay there; threads, turns, the record and parked
runs are here; the product's tables hold only the join — a user's row carries a thread id.

At every door, requirements belong to the host and capabilities belong to the implementation.
Pass `ExecutionRequirements` at construction (or in `thread/start` over protocol 2); Shadow opens
the provider only after its record and the effective environment prove a compatible pair. Omitted
requirements preserve the 0.29.1 behavior, while omitted capability facts remain `unknown` and
cannot satisfy an explicit production requirement.

## The ownership map

| the product owns | the kit owns | the join |
|---|---|---|
| users, workspaces, permissions, tenancy | nothing — it sees `principal` and `attributes` on every judgement (D82) | the backend sets them on `thread/start`; a rule a person keeps is scoped to them |
| its own messages and screens, if it has them | threads, turns, items, activity, the questions open, what was spent (D62, D80, D84, D90) | a message is a turn's prompt plus its items; `thread_id` on the product's row |
| its policy, its verbs, its gate | the governed loop, effects, the sandbox, the shipped modes and rules (D85), providers, approvals (D58, D88) | the product's ports handed to `Ports` — `GovernancePort`, `callable` components, `SinkPort`; two governments as one with `Routed` (D92) |
| modes and rules as its own settings | `ModeRegistry` / `ActRules` reading them live (D66) | a `Store` over the settings rows, or the kit's tables beside them |
| a worker on the person's machine | the environment there, the governed turn, a parked job that survives (`sqlite:///`) | the product's channel as sink and observer; the record stays on the server |

## One composition per process

```python
from shadow_hdk.serve import ServeHost, Settings, stores_for

host = ServeHost(
    Settings(root=WORK, mode="ask", store=DATABASE_URL),  # sqlite:///… or postgresql://…
    # or your own tables: store=MyStore(), threads=MyThreads(), run_store=MyRunStore()
)
thread = await host.open(
    root="",
    mode="",
    want=None,
    name="tools",
    observer=None,
    principal=user_id,
    attributes={"workspace": ws_id},
    budget={"steps": 200, "cents": 100},
)
```

- **The stores from one url** (D79) — the `Store` the registries read, the `ThreadStore`, and
  the checkpointer a parked run sleeps in; Postgres behind the `[postgres]` extra. Your own
  tables: implement `Store`, `ThreadStore` (nine methods, the hold included) and `RunStore`
  (four methods, D93), and prove each with the shipped suites — `from shadow_hdk.testing import
  ThreadStoreContract`.
- **A resident thread per conversation**, not a thread per turn: open once, `thread_id` on your
  row, `host.resume(thread_id)` on the next request (a CLI resumes on its own session id); a
  provider idles out after `[provider] idle_seconds` and is reopened at the next turn (D94).
- **Identity on every judgement**: `principal` is your name for the person, set by your backend,
  never by a page; `attributes` are your words (a tenant, a workspace); a rule made at a card is
  the answerer's (D82).

## A question, end to end

A policy that says *ask* puts the call to the host's `Questions` handle (D91) while the provider
waits. Three ways to answer:

- **Live** — `approvals/answer {kind: approve | deny | approve_and_add_rule}` while the request
  that started the turn is still open (a stream per session, as the React example does).
- **Later** — `turn/start {on_question: "park"}` for a request that must return (D88): the turn
  ends `parked`, the question is on the record, the parked act sleeps in the checkpointer;
  `approvals/answer` on any later request runs it and the agent is told at its next turn. A
  host that is there but cannot decide now answers `{kind: "park"}` for one question. The
  agent's own question (`ask_person`) parks the same way (0.29.1, BUG-044): the agent hears
  *not now* and stops; the person's text, given later, is folded ahead of the next prompt.
- **After a restart** (D80) — the same: the question comes back with `thread/resume`.

In-process the same three are `Thread.turn(text, on_question=)`, `Thread.pending` (the kept
questions, each with its `turn`), `Thread.settle(handle, answer) -> events`, and
`Approvals.answer(handle, Parked())`. A page or an API that lists questions lists the live ones
and the kept ones together (`approvals/pending` does; a kept one carries `turn`), and shows a
kept one as such — the React example's card says *kept — answer when ready*.

## What is measured, and where

`thread/remaining` is the budget less what the record says was spent — steps, the turns'
running seconds, cents, tokens in and out, with `unpriced` and `unmetered` saying when a call
reported nothing (D84, D90). A thread may be opened on a budget of its own.

## Testing a product

`shadow_hdk.testing`: the contract suites for every port; `ScriptedAgent`, a provider that
calls the tools it is scripted to and says its line; the runtime's doubles. A product's tests of
its governance, its verbs and its record reach no model, no CLI and no network.

## Don't

Subclass `Approvals` to change the runtime's side — implement `Questions`. Open a `Thread` per
turn over an in-memory store to get one governed turn — take `Conversation`. Keep a staged-act
store beside the kit's checkpointer — park the turn. Run two checkpointers on one database —
hand the kit your `RunStore`. Parse the reply's prose for structure — your `Proposal` verbs are
the structure. Let a page choose its `principal` — the process that authenticated it does.
