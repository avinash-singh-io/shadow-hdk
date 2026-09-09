---
type: History
phase: 0-the-runtime
---

# Phase 0 — history

Append-only. Newest at the bottom.

| Entry type | Meaning |
|---|---|
| `[DECISION]` | a choice made, with what it rules out |
| `[ARCH_CHANGE]` | a structural change to the code or the specs |
| `[DISCOVERY]` | something the code or a library turned out to be |
| `[CORRECTION]` | a previous entry or plan proven wrong |

---

### [DECISION] 2026-09-10 — thirteen decisions taken at founding, before any runtime code
Topics: founding, runtime, patterns, latency, build-vs-buy
Affects-phases: phase-0-the-runtime
Affects-specs: specs/architecture/decisions.md, specs/epics/0001-the-bare-harness.md

`09-the-agentic-system.md` decides the design and leaves thirteen things open. Each was settled in
the founding conversation and recorded with what would overturn it.

The four that changed the shape of this phase:

**D1 — the agent loop is a component.** The alternative was a second entry point, `run_agent()`
beside `run()`. That would have made "which kind of agent" a code path, and the whole reason a
pattern can be a *file* is that an agent is a component like any other: `single` is a composition of
one step over an agent whose pattern offers no `compose` and no `spawn`.

**D2 — spawning is ambient.** A `run()` started inside a step finds its parent through a contextvar,
the way LangGraph's own `get_stream_writer()` does. The alternative — a `spawn` port, or a label the
runtime branches on — puts a product concept ("sub-agent") into a runtime that is supposed to know
only effects.

**D11 — latency is a budget with a benchmark.** ≤ 1 ms p50 of runtime overhead per step, measured on
a no-op component under allow-all, with the benchmark written *in this phase* rather than
retrofitted. It is recorded as six design rules — governance in-process, no per-step serialisation,
a compiled-graph cache keyed by structural hash, the observer off the critical path behind a queue,
opt-in checkpointing, real concurrency for `FanOut` — because a budget with no mechanism is a wish.

**D12 — LangGraph executes; we compile and govern.** Build-versus-buy was asked directly. We write a
compiler and a governed step, a few hundred lines; execution, concurrency, checkpointing,
interrupts, streaming, retries and timeouts are the engine's. CrewAI, AutoGen and the OpenAI Agents
SDK were considered and declined for the same reason each time: they impose an agent shape, which is
the thing this design exists to refuse — their shapes remain portable later as pattern files.

---

### [DECISION] 2026-09-10 — the principle was written wrongly, and the correction is the whole boundary
Topics: proposals, effects, sink, record
Affects-specs: specs/vision/principles.md, specs/architecture/overview.md

The draft principle read *"propose, never commit — the runtime has no write method."* Read plainly
that says the agent cannot do anything, which is false and would have shaped the code wrongly.

There are two kinds of write and only one is forbidden. **Acting on the world** — writing a file,
rendering a page, running code, calling an API, moving an actuator — happens through **components**
whose effects are declared and judged per step. **Recording** — having the host remember something —
happens through the **sink**, as a proposal the host's gate decides on. The runtime has no write path
into any host's durable store; it has no restriction at all on effects it is permitted to have.

The principle is now *"Act through components; record through the sink."*

Two consequences in this phase: `callable_component` moves into Phase 0's `basic` adapter, because
registering a product's own operations as components is how the agent proposes at all; and
`architecture/adapters.md` carries a worked twenty-line example of plugging a host's record in — two
things, components and a sink, and nothing else.

---

### [DECISION] 2026-09-10 — one model adapter, not ten; modes are data; tools scale by scoping
Topics: providers, huggingface, modes, catalogue
Affects-specs: specs/architecture/adapters.md, specs/planning/roadmap.md

**Providers.** One `ModelPort` over LangChain's integrations (`init_chat_model`), so OpenAI and every
OpenAI-compatible endpoint, Anthropic, Ollama, **HuggingFace**, Bedrock, Vertex and Mistral arrive as
optional extras rather than ten adapters. A direct adapter is written only where LangChain has
nothing — ACP is the case. LiteLLM was considered as a second breadth library and declined: two
libraries for one job is a smell.

**Modes.** A mode is a ceiling effect profile plus an ask line — data. Two modes, ten, or one called
`auto` is a different mapping through the same `ModeGovernance` adapter, and layers compose by
`EffectProfile.meet`, so a team layer can only narrow — proven by the kernel's existing property
tests rather than by review. Moved into Phase 1; the rules-as-rows engine with mode files checked in
CI stays Phase 10, where the product needs it.

**Catalogue size.** The concern was 25 record tools plus a product's own plus the harness's. The
harness ships almost none — three meta-tools, and the pattern decides which the model sees. Scale is
handled by four mechanisms recorded as D13: computed visibility, patterns scoping tools per role,
sub-agents partitioning them, and catalogue compaction with a `describe` meta-tool above a threshold
(Phase 8). Adding tools never changes the runtime.

---

### [ARCH_CHANGE] 2026-09-10 — founded; branch flow is phase → staging → main
Topics: momentum, specs, branches, ecosystem
Affects-specs: specs/config.md, specs/status.md, specs/planning/roadmap.md

momentum installed with the claude-code adapter; the repository joined `intent-ecosystem` as member
`shadow-hdk`. The foundation is authored rather than scaffolded: charter, principles, success
criteria, roadmap, config, project rules, seven architecture documents, Epic 0001 and this phase.

`branch_flow` is `staging, main`: phases land on `staging` with the owner's single-use approval
sentinel, and `main` is touched only at a release. `release_flow` is `tag-only` until a licence is
chosen — a permissive licence grants rights for that version irrevocably, so publishing waits on the
owner.

The roadmap is ordered by what lane P needs at each product release (R0 → R3), and every phase names
the release it serves. Everything after the R3 join is the harness's own growth, pulled forward the
moment a product asks.

---

### [ARCH_CHANGE] 2026-09-10 — Group 0: the spine, and four layering guards that now bite
Topics: runtime, session, meter, emitter, doubles, invariants
Affects-phases: phase-0-the-runtime
Affects-specs: specs/phases/phase-0-the-runtime/tasks.md

`packages/runtime` exists: `Ports` and `RunOptions` (D4), `RunContext` and the contextvar (D2),
`Session` with `Handles` and `LeaseMeter`, the `Emitter`, `RunState` with commutative reducers, the
four errors, and the five doubles. 44 tests green, mypy strict clean over 21 files.

**The meter distinguishes three things the draft collapsed into two.** `charge(None)` means *this
step made no model call* — no cost, and that is known. `charge(Usage(..., cost_cents=None))` means
*a model call nobody could price* — after one of those the meter stops claiming to know the total,
`cost_is_known` goes false, and `remaining().ceiling.max_cost_cents` becomes `None` rather than a
number it cannot stand behind. R2's rule — *unknown, never zero* — is therefore arithmetic here
rather than a note in a document.

**The emitter has two queues, not one.** One consumer would have made D6 impossible: `run()` yields
from the stream queue while the observer is drained by a task of its own, so `emit()` puts twice and
returns. A test asserts that with a timeout rather than an assertion, because an emitter that
awaited its observer would hang rather than fail — and a hang is a worse test than a failure.

**Nine assertions mutation-checked, and the harness that checked them had a bug.** The first pass
reported *"one adapter imports another — still passes"*, which read as a vacuous guard. It was not:
`[tool.uv.workspace] members = ["packages/*"]` matched `packages/adapters`, a container with no
`pyproject.toml`, so `uv run` errored, pytest never ran, and a check that grepped for the word
*failed* saw none and called it a pass. Two real defects, both fixed: the glob is now
`["packages/kernel", "packages/runtime", "packages/adapters/*"]`, and the mutation helper reports
INCONCLUSIVE rather than folding an error into either outcome.

The four layering guards are proven at the subject rather than at the guard — a temporary file that
imports an adapter from the runtime, an adapter that imports another adapter, a package that imports
the product, a kernel module that imports `time`. Each fails the build; each is removed after.

### [DISCOVERY] 2026-09-10 — ruff 0.16 formats Python inside markdown
Topics: gate, specs

`ruff format --check` rewrote the fenced Python in the architecture documents — illustrative code
with aligned comments, which a formatter is right to dislike and wrong to own. `specs`, `.claude`,
`.agent`, `.githooks` and `.momentum` are excluded from the formatter: prose is not source, and
momentum's scaffold is vendored.

---

### [ARCH_CHANGE] 2026-09-10 — Group 1: the seven moves, and three things the design had wrong
Topics: registry, inputs, step, governance, errors
Affects-specs: specs/architecture/runtime.md, specs/phases/phase-0-the-runtime/tasks.md

`registry.py`, `inputs.py` and `step.py` exist. Every node of every compiled graph calls
`StepExecutor.invoke`, and nothing else touches a component or asks the governance port — which is
what makes *"was this judged?"* a structural fact rather than a review question. 54 tests green.

**[CORRECTION] Handles live in the graph state, not on the Session.** Group 0 put them on
`Session`, which is wrong the moment a run parks on `interrupt()`: a resume may be a different
process, and what comes back is a checkpoint, never a Python object. `Session.handles` is deleted;
the executor reads `state["handles"]` and the compiler writes them back through the reducers.

**[CORRECTION] A refusal emits one event, not two.** The draft had `Refused` *and* `Observed`. The
refusal is the record of what happened to that step; a second event saying the same thing twice is
how two narrations come to disagree.

**[CORRECTION] `Invoked` is emitted only where a component is actually called.** The first version
emitted it from the shared observe path, so a step that failed to resolve or whose input referred to
a step that produced nothing would have put a call in the record that never happened. Pre-invocation
failures now emit `Observed` alone.

**The registry is refreshed on every step**, because `09` §4 says the registry is live and connecting
an MCP server mid-session must show its tools on the next step. That is one `await` per component
port per step; making it cheap is the *adapter's* business — an adapter over something remote caches
and decides when to re-read. Group 5's benchmark is where the claim gets checked rather than
asserted.

**The kernel stopped hiding a name.** `Refuse` was exported as `RefuseJudgement` to avoid a clash
that does not exist: `Refused` is the observation, `RefusedEvent` is the event, and `Refuse` was
free all along. Renamed while it costs nothing.

Five assertions mutation-checked. One of the five did not apply on its first attempt — the sed
pattern missed a reformatted line — and reported *"still passes"*, which would have read as a
vacuous test. The mutation script now asserts its own target is present before running, so a
mutation that changes nothing fails loudly instead of quietly passing.

---

### [CORRECTION] 2026-09-10 — handles had two homes; the graph state is the one that survives concurrency
Topics: runtime, state, handles, fanout
Affects-phases: phase-0-the-runtime
Affects-specs: specs/architecture/runtime.md
Detail: Group 0 shipped a `Handles` object on `Session` *and* a `handles` field in `RunState`. Group
1 made the conflict concrete: `resolve_inputs` has to read one of them, and `FanOut` writes from
several branches at once. `RunState` is merged by commutative reducers, which is exactly what
concurrent writes need; `Session.handles` is shared mutable state across branches and would diverge
under the one condition the reducers exist to handle. `Handles` is deleted and `invoke` reads
`state["handles"]`. Two sources of truth for the same fact is the defect, not the size of either.

---

### [DECISION] 2026-09-10 — a catalogue that will not answer is empty, not fatal
Topics: registry, resilience, ports
Affects-phases: phase-0-the-runtime
Affects-specs: specs/architecture/runtime.md
Detail: `Registry.refresh` calls `registrations()` on every component port, every step, because the
registry is live (`09` §4). D7 says a port raising ends the run — but applied here it would mean one
unreachable MCP server costs a whole turn's work. So the catalogue call is the exception to the
exception: a port that will not list contributes nothing this step and is recorded in
`Registry.unreachable`. `invoke()` raising is unchanged and still becomes a `Failed` observation.
This is the design's own "the registry can shrink, and that is as ordinary as it growing".

---

### [DISCOVERY] 2026-09-10 — the mutation harness lied nine times, and the shell was why
Topics: testing, tdd, rule-13, verification
Affects-phases: phase-0-the-runtime
Affects-specs: none
Detail: The first Group 1 mutation pass reported all nine mutations "still passing", which read as
nine assertions that could not fail. None of it was true. The harness held its test paths in a shell
variable and expanded it unquoted; zsh does not word-split unquoted parameters, so pytest received
one path made of two filenames joined by a space, found nothing, and printed a message the verdict
regex did not match — which the harness scored as "the test still passed".

Two failure modes, one lesson. A mutation check must prove **the patch applied** and **tests were
collected** before it is allowed to report anything; a verdict derived from absence is not a verdict.
The harness is now a Python script that refuses a pattern it cannot find and refuses a run that
collected zero tests. Re-run against Group 1: ten mutations, ten killed — including two the shell
version had reported as survivors.

---

---

### [DISCOVERY] 2026-09-10 — LangGraph re-runs the whole node on resume, so `Asked` was recorded twice
Topics: interrupt, resume, events, g2
Affects-specs: specs/architecture/runtime.md

The Ask test failed in a way the design did not predict: after `resume(Allow())` the stream read
`asked · invoked · observed` rather than `invoked · observed`. Measured against langgraph directly
rather than reasoned about — a three-node probe confirms that `interrupt()` raises on the first
pass, the graph parks, and on resume **the node is executed again from its first line**, with
`interrupt()` returning the resume value the second time.

Everything above the interrupt therefore happens twice: the lease check, the registry refresh, the
governance call — all harmless, all arguably correct on a resume — and the `Asked` event, which is
not: one question would have appeared in the record as two asks.

The fix is to move the emit onto the raising path. The interrupter's contract is now *raise to
park, return to proceed*, and `Asked` is emitted in the `except` before re-raising. Exactly one ask
per question, and the event still precedes the park, so a host learns the question before the
process may end.

### [ARCH_CHANGE] 2026-09-10 — Group 2: compositions compile to graphs
Topics: compile, fanout, until, send, plan-cache, g2

`compile.py` walks a composition once into a `Plan` — nodes, edges, fan-out dispatchers, loop
routers — and then binds an executor to it. The plan carries no executor, which is what makes it
cacheable: the same shape, however often an agent re-authors it, is planned once (D11), and the
test asserts five hits and no new misses.

`Sequence` becomes edges, `FanOut` becomes a dispatcher returning `Send`s plus a join, `Until`
becomes a tick node and a conditional edge on condition-or-count, `Ask` becomes `interrupt()`.

**Fan-out is proven parallel by a barrier no sequential implementation can pass** — each of three
children waits for the other two to arrive before any returns. It is written under
`asyncio.wait_for` because a sequential compiler would hang here rather than fail, and a hang is a
worse test than a failure.

**A composite nested in another is inlined**, not compiled to a subgraph. The plan said subgraph;
inlining is correct, simpler, and observably identical here. True subgraphs earn their cost in
Phase 6, where a sub-agent needs its own checkpoint namespace — recorded rather than silently
dropped.

`:` cannot appear in a node name — LangGraph reserves it for checkpoint namespaces — so synthetic
nodes use `__`.

---

### [ARCH_CHANGE] 2026-09-10 — Group 3: the drive, and what a disposable runtime cannot remember
Topics: run, resume, spawn, forward, replay, g3

`run()` is an async generator that yields events **while** the graph runs on a task of its own, so a
host watching a long run sees it happen rather than hearing about it afterwards. `Started` … `Ended`,
five end reasons, and a parked run emits no `Ended` at all — it has not ended, and whoever resumes
it will close it.

**[CORRECTION] `resume` takes the composition back.** The plan wrote
`resume(run_id, answer, ports, options)`. That cannot work: the runtime owns nothing durable (`09`
§6), so it does not have the shape of the run it parked. The checkpointer holds the state and
whoever resumes holds the plan — which is the disposability property showing up as an API rather
than as a paragraph. `options.run_id` and `options.checkpointer` are both required, and both raise
by name when absent.

**A child is carved, announced and forwarded.** `Spawned` is stamped on the parent (so it carries
the parent's sequence); the child's own events are forwarded **verbatim**, keeping the child's run
id and its own sequence. One consumer therefore sees the whole tree and every event says whose it
is, without the runtime inventing a hierarchy in the numbering.

**A stop is a reason, not a traceback.** LangGraph may wrap a node's exception, so the drive walks
the `__cause__`/`__context__` chain for a `RuntimeStop` rather than checking the top.

### [DISCOVERY] 2026-09-10 — five mutations, and the one that found a hole in the tests
Topics: g3, d2, mutation-check

Four of five mutations failed the suite as they should. The fifth — making `_parent_of` ignore the
contextvar entirely — **left every test green**, and the reason matters: every spawn test reached
its child through `ctx.spawn_options(...)`, which names the parent explicitly. So D2's actual claim
— that a run started inside a step becomes a child *without being told* — was never exercised. The
tests proved the explicit path and the design's headline was untested.

`test_a_plain_run_inside_a_step_becomes_a_child_without_being_told` starts a run the way a naive
component would, with no parent argument, and asserts it is carved, announced and forwarded. The
mutation now fails the suite.

This is the second time a mutation check has found a vacuous test rather than a bug, and the second
time the fix was a better test rather than better code.

---

### [CORRECTION] 2026-09-10 — a carve was a spend, and a step's price had stopped arriving
Topics: leases, reservation, usage, g4

Two defects found while writing Group 4, both in code that was already green, and both found by
asking *what will the agent's turn loop do to this?* rather than by reading it again.

**A carve reserved and never released.** `LeaseMeter.carve` added the child's worst case to
`_carved_steps` and nothing ever took it away. An agent running twelve turns — each turn a child
composition asking for five steps and spending one — would have drained sixty steps from a parent
that had twenty, and the fourth turn could not have been carved at all. The end-to-end test reads
`[18, 17, 16]` now; before the fix it read `[14, 9, 4]`.

The fix makes the pair symmetric and puts it in one place. `carve` is a **reservation**: it holds
the child's worst case so two concurrent children cannot both be promised the same budget.
`settle` releases the hold and charges what the child actually spent, and the drive calls it in a
`finally`, so a run that ended badly still gives its budget back. `spawn_options` no longer carves —
it proposes a ceiling, and the *drive* carves, whoever asked. So a child passing its own lease is
carved from the parent exactly like one that asked politely.

**A step's price had stopped reaching the meter.** The Group 1 refactor moved `meter.charge()` to
the top of `invoke` — which is right, because a step counted when it *begins* tells against the
ceiling and stops concurrent children collectively overrunning it — but it dropped the `usage`
argument on the way, and `_usage_of` went with it. The cost ceiling could no longer bite in a real
run; only the meter's own unit tests still exercised it, and they passed.

Counting and pricing are now two moves because they happen at two moments: `charge()` counts the
step as it starts, `charge_cost(usage)` prices it when the observation comes back. Two tests assert
the second one arrives — one for a priced call, one for a call the provider would not price, which
must leave `cost_is_known` false rather than charging zero.

Five mutations, all failing the suite. Two of them reported TARGET MISSING on the first attempt
because the labels contained apostrophes and broke the mutation script's own quoting — caught
because the script prints TARGET MISSING rather than treating a no-op as a pass, which is the
guard added after the same thing happened silently in Group 1.

---

### [ARCH_CHANGE] 2026-09-10 — Group 4: the agent is a component, and a pattern is what makes it one kind
Topics: agent, pattern, single, adapters, basic, contracts, g4

`packages/adapters/basic` and `packages/adapters/agent` exist. 135 tests green, mypy strict over 35
files, fourteen mutations checked across the two.

**A turn is a child run.** The agent shows the model what it can see, reads what it wants to do,
turns that into a **composition**, and calls `run()` — the same entry point a host uses. So a turn's
work has its own lease, its own events and its own `Composed`, and the plan the model made is on the
record whether or not it worked. That is D1 paying for itself: there is no second execution path to
keep in step with the first.

**What the model may do is the pattern's decision.** `single` offers `propose` and `done` and not
`compose`, so it cannot change its own shape — a fully deterministic one-agent product on the same
runtime a dynamic one uses. A mutation that hands every meta-tool to every pattern fails the suite.

**A pattern holds no callables.** The draft had `tool_filter: Callable[[Registration], bool]`. A
pattern is meant to ship as a *file* a team can read and edit, so a filter is a set of names —
`tool_names` — and it is a display choice, not a permission. Permission stays `ceiling`, and stays
effects.

**One registry per run.** The agent needs to know what the model may see, and the first version
built its own `Registry` and asked governance itself. That was two answers to one question and they
could drift: what the model was *offered* and what the runtime will *let it invoke*. `RunContext`
now carries the run's registry and answers `visible()`, and the executor resolves against the same
object.

**The floor gets exactly one nudge.** A model trained to be agreeable gives up early; a second nudge
would be nagging and the run would never end. Two mutations cover it — removing the nudge, and
letting it repeat.

`patterns/single.md` is deliberately **not** written. The role already travels inside the `Pattern`;
a markdown file nothing reads would be a second source of truth for the same prompt. The loader that
makes a pattern a file is Phase 8, and the file arrives with it.

---

### [ARCH_CHANGE] 2026-09-10 — Group 5: the bare harness is green, and the demo found two defects
Topics: bare-harness, examples, observer, leases, benchmark, versions, g5

Phase 0 is complete. 150 tests, mypy strict over 37 files, 96 % line coverage on the runtime, every
package at 0.1.0. **The `xfail` marker is off `tests/test_bare_harness.py`**, and four invariants
keep it that way.

**The demo found two things no unit test had**, which is the argument for building it rather than
asserting it.

*An observer was called once per nesting level.* Every child run inherited the host's observer, so
an event two levels down reached it three times — while the yielded stream was perfectly correct,
which is why nothing had caught it. Read straight off the demo's own output: twenty-three events,
forty-four lines. Only the root feeds the observer now; children forward to their parent and the
parent forwards on, so the observer is reached exactly once however deep the tree.

*A turn's plan was carved `len(steps) + 1` steps.* Right for tool calls; wrong the moment a step is
itself an agent, because a sub-agent needs steps for its own turns and got two. It died
`lease_exhausted` after one turn — **silently**, because a lease ending a run is not an error, and
the parent then read the sub-agent's next scripted answer as its own. Turns are sequential and each
settles before the next, so a turn now gets whatever the parent has left; the parent's own ceiling
still bounds the lot. Also fixed: finishing via `done` reported `turns: None`.

**The latency budget is measured, not hoped for** (D11). 100 sequential no-op steps in **58.6 ms
(0.586 ms/step)** and a 50-way fan-out in **26.5 ms**, against targets of 100 ms, 1 ms and 50 ms.
The assertions sit at three times the target so a shared runner cannot flake them, which means they
catch an order of magnitude rather than a drift — the printed numbers are the real signal, and CI
prints them.

`patterns/single.md` was deliberately not written: the role travels inside the `Pattern`, and a
markdown file nothing reads would be a second source of truth for one prompt. The loader that makes
a pattern a file is Phase 8, and the file arrives with it.

**Not run: `/complete-phase`'s merge step.** Nothing merges to `staging` or `main` without the
owner. Phase 1 branches from `phase-0-the-runtime`, and the chain is what carries the code.
