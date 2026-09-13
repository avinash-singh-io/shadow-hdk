---
type: Plan
phase: 29
---

# Plan — Phase 29

Seven groups; each lands on `staging` then `main` with CI green before the next starts; the
release is one, **0.28.0**, at the end (a contract change: new parameters, new methods, a port
that grew). RED first for every rule; a mutation for every load-bearing assertion; the records
(this history, the backlog, the changelog, the architecture documents the change touches) in
the same commit as the change.

## Group 1 — the record chooses its store; a parked run survives (P1, P2)

**Design.** `[store] url` in `harness.toml` — `sqlite:///live.sqlite` or `postgresql://…`;
`[store] path = "live.sqlite"` stays as sugar for the SQLite url. `serve.stores_for(url)` answers
the three things a record needs — a `Store`, a `ThreadStore`, a LangGraph checkpointer — from
one choice: SQLite from `adapters.basic` plus `langgraph-checkpoint-sqlite` (a base dependency
now, because durable parked runs are the default, not an extra); Postgres from a new
`adapters.postgres` behind a `[postgres]` extra (`psycopg[binary,pool]`,
`langgraph-checkpoint-postgres`), imported lazily and named in the refusal when missing — the
`[sandbox]` pattern. `ServeHost(settings, store=, threads=, checkpointer=)` for a host that has
its own; the wire's `RuntimeSide` keeps its per-session `InMemorySaver` for the first shape
(`run`/`resume`) and the served threads use the host's. The contract suites `StoreContract` and
`ThreadStoreContract` run against Postgres when `SHADOW_HDK_TEST_POSTGRES_URL` is set (the
desk: the local Postgres 16; CI: a service container); skipped, and said so, otherwise.

**A parked run survives.** `Thread` takes the host's checkpointer. On `thread/resume`, a record
whose last turn is `parked` has its pending question rebuilt from the checkpoint's interrupt
payload and offered on `Approvals` again — `approvals/pending` lists it, the card appears, the
answer resumes the run from the checkpoint. Measured: park in one host, close it, open a new
host on the same store, resume, answer, the turn completes.

## Group 2 — one thread, one holder (P3)

**Design.** `ThreadStore` grows `acquire(thread_id, holder, ttl_seconds) -> bool`, `renew`,
`release`; SQLite, Postgres and in-memory implement it; the contract suite says what a lease
means (a second holder refused while the first renews; free after the ttl lapses). `Thread.open`
and `resume` acquire, renew on a task while open, release on close; a refusal names the holder
(`ThreadHeld`); the wire answers it as a refusal with the holder and the remaining ttl;
`thread/list` rows carry `held_by`. `turn/start {when: "enqueue" | "reject" | "interrupt"}` —
`enqueue` is what the turn lock already does, now named and recorded; `reject` refuses at once
when a turn is running; `interrupt` interrupts the running turn (the existing `turn/interrupt`)
and starts. `TurnRecord` says how it was started.

## Group 3 — identity on the thread, scope on the rows (P4)

**Design.** `thread/start {principal, attributes}` → `ThreadRecord.principal` and
`.attributes` (a tenant, a workspace id — the product's words); `RunOptions.principal` and the
context's attributes come from the thread on every turn, so a governance port sees them (this is
where a product's own policy — an RBAC engine — plugs in without the kit knowing it).
`ModeSpec.scope` and `ActRule.scope`: empty means everyone; otherwise a principal, or
`attribute:value` (`tenant:acme`); `modes_for`, `store_rules` and the skill registry take the
thread's scope and read only rows in it; `approve_and_add_rule` from a card writes
`scope = principal`. `Context.principal` is set for every judgement of the thread's runs.

## Group 4 — batteries live (P5)

**Design.** The battery registry already reads shipped files, a directory and the store; what
is *wanted* becomes rows too: `[tools] batteries` seeds the `batteries` collection at the host's
first open (rows `{id, on}`), and `store/put batteries <id> {on}` switches from the next thread.
`ServeHost` opens a wanted battery when a thread needs it and holds it for the process (as
today); a battery switched off is not offered to the next thread. `batteries/list` says which
rows are on.

## Group 5 — the budget on the record (P6)

**Design.** `thread/start {budget: {steps, seconds, cents}}` overrides the file's defaults per
thread; `ThreadRecord.budget` and `ThreadRecord.spent` (steps, seconds, cents) are saved at the
end of every turn; `thread/remaining` answers `budget − spent`; a resumed thread's meter starts
from `spent`. Closes ENH-013.

## Group 6 — the rules the field has (P7)

**Design.** `ActRule.decision` gains `ask`: a matching ask rule sends the call to the person in
every mode, `full` included (Claude Code's ask rules hold in `bypassPermissions`); a `deny` rule
holds in `full` too — measured, and an invariant. A rule's `inputs` values may be glob patterns
(`"path": "finance/**"`) matched against the call's inputs, anchored to the workspace's roots
(`second/**`). A mutation: a rule that does not hold in `full` fails the test.

## Group 7 — operations (P8)

**Design.** `GET /healthz` on the HTTP door: `{ok, version, sessions, threads}` without a bearer;
`admin/sessions` and `admin/threads` on the wire (the bearer is the admin — one app server, one
operator); `initialize` answers the kit's version. **The per-run token, decided**: with one app
server behind every surface, the product's backend authenticates people and holds the one
bearer; a per-run token would be a second credential for the same trust boundary — closed as
D-, not built, and `wire.md`'s note updated.

## The release

0.28.0: the wire's schemas regenerated; the TypeScript client's facade grown (`thread.start`
takes `principal`, `attributes`, `budget`; `turn.start` takes `when`; `admin.*`; `thread/list`
rows carry `held_by`, `principal`, `spent`); the demo's tour updated where it shows a changed
thing (the threads station: held_by and spent; the backend station: the principal it now
passes); `adapters.md`, `wire.md`, `runtime.md`, `testing.md`, `file-structure.md` describing
the tree; the Pins row.
