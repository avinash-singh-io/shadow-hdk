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
