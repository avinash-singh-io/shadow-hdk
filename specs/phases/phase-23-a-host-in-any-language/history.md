---
type: History
phase: 23
---

# History — Phase 23

### [DECISION] 2026-09-11 — D51: the agent runs where the record is, whichever side of the wire that is

Topics: wire, parity, children, agent, spawn
Affects-phases: phase-23-a-host-in-any-language
Affects-specs: architecture/wire.md, architecture/runtime.md#children

The agent adapter's `carry_out` ran the plan the model authored through a **local** `run()` — a
nested run on the host's own loop, with its events on a stream nobody read when the agent was on
the far side of a wire. That was the one thing keeping the agent from running remotely at all, and
it hid a second gate: the pattern's ceiling was applied by the nested run's ports rather than by
the runtime that owns the lease.

The agent now spawns its plan **through the runtime**: `children.spawn(composition, ceiling,
within=pattern.ceiling)`. The pattern's ceiling crosses the wire as data and is applied where the
child is spawned as a second gate, `Narrowed`, which lives in `runtime/children.py` and not in the
adapter. Everything a `RunContext` offers either crosses — `visible`, `floor_met_now`,
`spawn_options_now`, `reasoned` with its step, `children.spawn/send/release/is_held` through a
`WireChildren` proxy — or is named in `NOT_CROSSING` with a reason, and an invariant holds that
table to the class. A second invariant holds the wire's published schemas to the kernel's event
kinds, `Reasoned` and `Step` included.

*Why:* a host in any language means the agent on the other side, and an agent whose sub-agents run
somewhere the host cannot see is not visible. *Overturned by:* a `RunContext` method that cannot
cross and cannot be named — none has been found.

---

### [DECISION] 2026-09-11 — D52: nothing reaches a run's registry without the token it minted

Topics: socket, token, authentication, recording, d44
Affects-phases: phase-23-a-host-in-any-language
Affects-specs: architecture/adapters.md#recording

D44 served the registry over an ephemeral loopback port and left a debt: any process on the
machine that guessed the port could act inside somebody else's run. A token is minted per serve
with `secrets`, travels to the relay in its **environment** (never argv, which `ps` shows to every
user), and is sent as the first line before any MCP traffic. The server reads exactly one line —
up to the newline and no further, so the first MCP frame is left intact — compares in constant
time, and serves or closes. A JSON-RPC frame where the token should be is a refusal; so is an
empty line, which is the case a prefix compare accepts and the test that told.

Refusals are **counted on the holder**, never logged with what was presented. The count is handed
in as a callback rather than sniffed off mcp's `Server` — the first cut looked for an attribute on
the wrong object and counted nothing, which the count test caught. The token appears on no event,
in no `Available`, in no log.

*Why:* loopback is a trust boundary between users, not between processes. *Overturned by:* an OS
that hands out a per-process capability for a socket — then the token is redundant, not wrong.

---

### [DECISION] 2026-09-11 — D53: a provider's child dies with the process that held it, whatever ended it

Topics: processes, bug-019, atexit, signals, leash
Affects-phases: phase-23-a-host-in-any-language
Affects-specs: architecture/runtime.md#processes

`close()` ends a session's group when it is reached. A person leaving a REPL with Ctrl-C, a
`sys.exit`, a `SIGTERM` from a supervisor, an exception nobody caught: none of those promised to
reach it, and two `claude -p` children were found alive ten hours after their sessions ended, each
holding a subscription seat (BUG-019). Reproduced under all four endings before the fix.

Every session leader the runtime starts — the leash's two shapes, the jsonl session, the ACP agent
— is `hold`-ed in `runtime/processes.py`, and the interpreter's ending ends them all. `atexit`
covers every normal exit and every propagated exception; `SIGTERM` and `SIGHUP` with the default
disposition would skip `atexit`, so they get a handler **only where the host installed none** — a
host with its own handler keeps it and exits through it. The chained handler ends what is held,
restores the default and re-raises, so a supervisor that sent `SIGTERM` sees death by `SIGTERM`.
`end_the_group` lets go, so a pid ended and reaped is never killed again at exit — by then it may
be somebody else's.

*Why:* a step owns the tree it starts (D35), and a session the host holds across steps is the same
obligation one level up. *Overturned by:* a platform with a real process-death signal for
children (`PR_SET_PDEATHSIG`); Linux has one, macOS does not, and the rule has to hold on both.

---

### [NOTE] 2026-09-11 — what the host example found

Topics: host, projection, ask, bug-020
Affects-phases: phase-23-a-host-in-any-language

Three things the example surfaced by being run rather than read.

**A host rendering steps live saw nothing for the whole run.** `run_steps` yields a top-level step
when it closes, and an orchestrator's own step closes last — after every sub-agent's step it
nested. `run_steps(nested=True)` yields every step as it closes, the child's before the parent's,
each with a new `Step.parent`; the default is unchanged and `Step.json` republished.

**An `Ask` inside an agent's tool call never reaches the host** (BUG-020). The child parks,
`carry_out` sees no `observed` for the call, and the model is told *that step did not run* — the
scripted worker then proposed and finished claiming it had written a file it never wrote. The
top-level Ask parks, persists on the file and resumes from the next call (proven); inside an
agent, consent-before-effect is currently a silent no. Filed P1; not the example's to fix.

**The coder's `show()` never rendered a refusal.** It checked `kernel.Refused` — the observation —
against events; the event is `RefusedEvent`. Corrected in both examples.

Also: `detect()` dropped `bin_env_key`, found by pointing it at a Codex installed into the scratch
directory; and an `Ask`'s `Refuse` answer arrives as the step's *observation*, which the host's
view now reads for its reason.

---
