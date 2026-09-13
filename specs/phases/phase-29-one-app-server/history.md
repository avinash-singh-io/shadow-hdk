---
type: History
phase: 29
---

# History — Phase 29

Append-only. Decisions as `### [DECISION] date — D<n>: title`; the index in
`specs/decisions/index.md` is regenerated from them.

### [NOTE] 2026-09-14 — Opened, from the owner's decision and the research note

The owner, on the research note `specs/research/2026-09-14-how-comparable-runtimes-do-it.md`:
*one app server behind every surface* — the harness is the one process a product's local
install, web app (through its backend), phone and cloud runner all talk to. The eight proposals
of the note become this phase's seven groups. The desk has a local Postgres 16 running; CI gets
a service container. Phases *context engineering* and *collaboration* move to 30 and 31.

### [DECISION] 2026-09-14 — D79: the record chooses its store — one url, three things

**Decision.** `[store] url` in `harness.toml` — `sqlite:///…` or `postgresql://…`; `[store]
path` stays as sugar for the sqlite url — names where the record lives, and `serve.stores_for(url)`
answers the three things a record needs from that one choice: the `Store` the registries read
(modes, rules, skills, switches), the `ThreadStore`, and the checkpointer a parked run sleeps in.
Nothing named is memory, for the process. Postgres is `adapters.postgres` behind the `[postgres]`
extra (`PostgresStore`, `PostgresThreads` over psycopg's async pool; LangGraph's own
`AsyncPostgresSaver`), named in the refusal when it is not installed. `ServeHost(store=, threads=,
checkpointer=)` takes a product's own for any of the three; what is handed in is never made from
the url. `langgraph-checkpoint-sqlite` is a base dependency now: a parked run on disk is the
default, not an extra.

**Why.** Every comparable runtime configures persistence as one choice — LangGraph Server's
checkpointer, ADK's session service, Mastra's storage, the OpenAI SDK's session backends — and a
product behind one app server keeps its state where the rest of its state is. Three settings for
three stores would let a product put its threads in Postgres and its parked runs in memory without
noticing, which is the failure D80 closes.

**Rule.** A url fills all three or a host hands all three in; a scheme nobody implements is
refused by name with the ones that are; the contract suites run against every store the url can
name — Postgres under `SHADOW_HDK_TEST_POSTGRES_URL`, skipped and said so without it.

### [DECISION] 2026-09-14 — D80: a parked turn survives the host

**Decision.** A question nobody has answered is on the thread's record (`ThreadRecord.pending`:
handle, turn, step, question, kind, component, inputs, and the run that parked on it) from the
moment it is asked to the moment its step is observed or refused; every served thread runs on
the host's checkpointer (a `Thread` opened by `ServeHost` never had one before). A thread
resumed with a turn still `running` was left by a host that died: with a question of that turn
open the turn is **`parked`** and the questions stay pending; with none it is **`cancelled`**,
the text saying the host went away. `thread/resume` answers `pending` and pushes each question as
an `approval_request`/`input_request`; `approvals/pending` lists them beside the live ones;
`approvals/answer` on a left handle is `Thread.settle`: an approval resumes the parked child run
from the checkpointer — the act runs, or is refused, exactly where it stopped — and either kind
is folded ahead of the next prompt so the agent is told what became of the call it made.

**Why.** The agent's own transcript cannot be rewound (D62's reason for honest forks), and a
call it never heard back from is one it would make again. The industry's answer is the same:
Codex marks the turn interrupted; LangGraph resumes the parked graph. Here the graph that parked
is the tool call — a child run — so it resumes; the provider is told rather than pretended to.

**Not decided here.** A turn's outcome after settlement stays `parked`: it ended without the
agent's answer, and rewriting it `completed` would claim a completion the provider never gave.

### [NOTE] 2026-09-14 — BUG-041, found by the first crash

The first test that killed a host mid-question hung on its own cancellation: `run()` drives the
graph in a task and its `finally` waited for that task, which was blocked on a question nobody
would answer. Every `thread/close` with a card open would have hung the same way. The reader's
cancellation now cancels the drive, and the question is withdrawn (D59). Filed and closed in the
same group, RED first.

### [DECISION] 2026-09-14 — D81: one thread, one holder; a second turn is a named choice

**Decision.** The `ThreadStore` port says who holds a thread: `hold(thread_id, holder,
ttl_seconds)`, `renew`, `release`, `held_by` — a lease on the store's own clock, because two
processes cannot agree on one of theirs. `Thread.open` and `resume` take it for the `holder` they
are given, renew it every third of its life while the thread is open, release it at close;
`ThreadHeld` names the holder when another process has it, and a hold nobody renews lapses
(30 s) so a dead host is out of the way. `ServeHost` names itself `host:pid:nonce`. `thread/list`
rows carry `held_by`. `turn(text, when=)` — `enqueue` (the default; the turn lock, now named),
`reject` (`TurnRunning`, naming the running turn; nothing recorded), `interrupt` (the running
turn stopped as `interrupt()` stops it, ending `cancelled`; this one starts). A thread opened
without a holder takes no hold: the in-process shape with nothing to share the store with.

**Why.** One app server behind every surface is one process per thread, and the industry says
so plainly: LangGraph Server locks a thread per run and names its double-texting strategies
(reject · enqueue · interrupt · rollback); Codex's app-server owns its threads outright. A lease
rather than a lock because the process that holds it can die; a name rather than a boolean
because the person who is refused should know by whom.

**Not built.** `rollback` as a fourth strategy: the harness's `thread/rollback` is a fork of the
first N turns (D62), a different thing from discarding a running turn's effects, which a
provider's transcript cannot do.

**Found on the way.** A second turn arriving while one ran was refused *no steps left* (BUG-042):
the remaining was read before the turn lock, while the running turn's reservation held everything;
it is read under the lock now, where the earlier turn has settled. The plan's `TurnRecord.started_as`
is not added: an interrupted turn's outcome already says what happened to it, and `enqueue` is
nothing the record needs to remember.

### [DECISION] 2026-09-14 — D82: identity on the thread, scope on the rows

**Decision.** `thread/start {principal, attributes}` → `ThreadRecord.principal` and
`.attributes` (a tenant, a workspace id — the product's words; a reserved name is refused as it
is on a run), and both on every judgement's `Context` of the thread's runs — the turn's step,
every tool call (a child carries its parent's principal), the catalogue `tools()` judges, a parked
act `settle` resumes. `ActRule.scope` and `ModeSpec.scope` — empty for everyone, a principal's
name, or `attribute:value` — with one kernel word, `in_scope`; `ModeGovernance` reads a rule only
in its scope and a mode out of scope is *not a mode here*; `ActRules.all_now` and
`ModeRegistry.find/all` take the identity and answer in scope, everything when nobody is named;
`rules/list` and `modes/list` take a `thread_id` for the scoped view; `set_mode` refuses a mode
out of the thread's scope. A rule made at a card (`approve_and_add_rule`) is scoped to the
principal who answered when it names no scope of its own.

**Why.** Every runtime the note read puts the person on the container and filters rows by it —
LangGraph's `@auth.on` owner metadata, ADK's `user_id` on the session, Codex's per-user
approvals. The kit does not become an authorisation engine: a product's own plugs into the
governance port and sees the same principal and attributes; the kit gives rows a scope so the
shipped registries are safe by default in a shared process, and names the other way — one
process per tenant — where a product's policy demands separate tables.

**Not built.** Roles, groups, hierarchies of scope: `attribute:value` is one comparison on
purpose; a product with roles puts the role among the attributes.

### [DECISION] 2026-09-14 — D83: batteries live — what is wanted is rows

**Decision.** `[tools] batteries` seeds the store's `wanted` collection (`{id, on}`) at the
host's first open — a row already there is left as it is — and from then on the rows say which
batteries the next thread gets: `ServeHost` reads them at every thread's open, opens what is
wanted and not yet open (held for the process, as before), closes what is open and no longer
wanted. `batteries/list` says on · off · unavailable by those rows; a row naming no battery is
reported, not fatal.

**Why.** Every other registry the host reads is live through the store (D66: modes, rules,
skills, switches); batteries were the one thing fixed at the process's start, so a product could
not turn a search engine on for its users without restarting the server every surface stands
behind. A row is the same door the others use.

**The truthful edge.** A battery's server is the process's, not a thread's: one switched off is
closed at the next thread's open and gone from every thread at once. Holding it until the last
thread opened with it closes would need the host to know its threads' lifetimes, which the wire
knows and the host does not — named here, not built.

### [DECISION] 2026-09-14 — D84: the budget on the record

**Decision.** `thread/start {budget: {steps, seconds, cents}}` opens a thread on a ceiling of
its own over the file's default (`ThreadRecord.budget`; `None` when the default is meant, which
is not repeated on the record); what the thread has spent is on the record (`ThreadRecord.spent`:
steps, seconds, cents, unpriced) after every turn, and the meter of every opening starts from
it — `remaining` is budget less spent however many times the thread is resumed. Closes ENH-013,
measured over the wire: the reload that used to read `400 · 500` after `399 · 492` reads what was
left.

**Why.** A budget a product shows its person is a promise about the whole conversation, not
about the process that happens to hold it now; every runtime the note read keeps usage on the
container (Codex's thread, LangGraph's thread metadata, ADK's session state).

**The truthful edge.** A turn the host died in charged its steps in memory only: what it spent
is not on the record. The spend of a crash is unknown, and the record says what it knows.

### [DECISION] 2026-09-14 — D85: the rules the field has

**Decision.** `ActRule.decision` is `allow`, `deny` or **`ask`**, and `ModeGovernance` reads the
rules in Claude Code's order with the ceiling where a ceiling goes: **deny, then the ceiling,
then ask, then the mode, then allow**. A deny rule refuses in every mode, `full` included, and
below the ask line too (a read of `.env*` a product forbids); an ask rule puts the act to the
person in every mode; an allow rule stands in for the person only where the mode would have
asked. Among the rules that match, the strongest decides (`deny` > `ask` > `allow`) whatever
order the rows were written in — first-match was defeatable by row order. A rule's inputs may be
patterns: `**` crosses `/`, `*` and `?` stay within a segment, `[…]` is a class, a `*` at the
very end takes the rest as the prefix rule always did; matched against the input as the tool
receives it — a path relative to the primary root, or `name/…` for another root, which is what
anchors a pattern to a root without a second vocabulary.

**Why.** Claude Code's rules hold in `bypassPermissions`; Codex's execpolicy amendments hold
across sandbox modes; a product that cannot forbid `rm -rf` in `full` or ask before every write
under `finance/` has no policy, only a mode. The shipped governance had rules only after the
mode said *ask*, which made a deny rule silent exactly where it mattered.

**Not built.** Rules that reach into an input's structure beyond top-level keys; a rule over
the tool's *effects* rather than its name (that is what a mode is).
