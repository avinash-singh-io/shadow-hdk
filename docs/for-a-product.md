# For a product — what the kit answers, and how to compose it

> Written 2026-09-19 for Intent Studio (lane P) against **shadow-hdk 0.31.0**, in answer to ten
> questions asked so the product neither assumes a mechanism nor rebuilds one. Every claim below
> was checked against the code at that version before it was written; where the kit has no
> answer it says so and names the follow-up. The rule the answers serve: *the product composes
> the kit; it never rebuilds a mechanism the kit has; a gap in the kit is fixed in the kit.*

The map first, then the ten answers, then the follow-ups that answering raised.

## The map — what a product registers, what it reads, what it never touches

| the product **registers** (its own, on a port) | the product **reads from configuration** | the product **never writes** |
|---|---|---|
| its tools — a `ComponentPort` with an honest `EffectProfile` per tool | `harness.toml` — environment, provider, store, budget, batteries, idle | the provider records (`codex.toml` and kin): the kit's measurements, not the product's |
| its modes — documents under a modes directory, or store rows, or `ModeSpec` in code | the shipped modes `read-only · ask · workspace-write · full` and their plan limits | the kernel's grammar, events and contracts (an ADR, not a product) |
| its rules — `ActRule` rows in the store | | |
| its record — the `Store` port (rows), a `ThreadStore`, a `RunStore` | | |
| its authority — `AuthorityPort`, `AuthorizerPort`, `EffectJournalPort` | | |
| its sink, observer, clock | | |

Three doors, one composition (`docs/consuming.md` has the full table): `Thread` in-process where the
product owns the process (a Computer); `serve` behind the product's backend where it does not (the
server); `run()` for a workflow with no conversation. `serve/host.py::workshop()` is the shipped
composition every door uses — a product that drops to `Thread` calls the same function and adds its
own components to what it returns.

---

## 1. Producing an artifact as an act

**A registered component in the product's registry, beside the record tools.** Not a pattern, not
an effect with a sink. The kit has no artifact concept and by its admission rule never will —
"artifact" is a product concept. What the kit has is exactly enough:

- **The act.** A registration (say `write_artifact`) with an honest `EffectProfile`:
  `writes=ScopeSet.of("artifacts")`, `reaches=True` if the bytes leave the machine, `reversible`
  as the product's store makes it. The mode then judges it like every other act — `read-only`
  refuses it, `ask` asks, `workspace-write` needs a rule because `artifacts` is not the workspace
  scope. That is D1: govern effects, not names.
- **Where the content lives: the product's.** The kit's `Store` port (D66) is the product's rows —
  a document body can be a row, or live in the product's blob store with `Completed.output`
  carrying `{id, revision, url}`. The kit's record holds the trail — `Invoked(inputs)` and
  `Observed(Completed(...))` — never the bytes. `Item.inputs` is bounded at 64 KiB with an explicit
  omission marker (`runtime/items.py`), so the body does not belong in the inputs.
- **Versions.** The kit has no "the same artifact, later." Two honest shapes: the product's key
  with `store.version(collection)` (a version per collection is in the port); or
  **propose-never-commit** — `context.propose(Proposal(kind="artifact", payload={...}))` through
  the `SinkPort`, the product committing the revision (D6). The second is what the kit already does
  for a rule made at a card.
- **"Shall I write this up?"** — it depends who is asking. The *agent* asking the person is
  `ask_person` (`runtime/person.py`, D65) → `InputRequested` → the same card path, park-able (D88).
  The *policy* asking before the write is an `ask` rule on the component's effects →
  `ApprovalRequested` → approve · deny · approve_and_add_rule · park. Both are kit mechanisms; the
  product surface is the card it already draws.

Not this: Phase 34 (*the harness as data*, Epic 0009) is about harness blueprints and bundles —
artifacts *of the harness*, not documents the agent writes. Nothing here waits on it.

## 2. Modes and behaviour

- **A plan mode is a kit mode.** `read-only` is precisely "reads, the skills, the person, the web;
  nothing written or run." Since 0.31 it also admits plans (3 deep, 8 wide, 64 steps) with every
  step still judged, so a `compose` under `read-only` proposes and reads but changes nothing. A
  product mode document naming the `read-only` policy, with a behaviour that says *propose, do not
  do*, is the whole feature — a file, not code.
- **Rigor and depth are `Behaviour`, and `Behaviour` lives on the mode.** A `ModeSpec` is policy +
  behaviour + presentation + environment + plan. `Behaviour` carries `system`, `append_system`,
  `model`, `effort`, `temperature`, `tools_offered`. So: drop the persona as a separate knob and
  make each former persona a mode document whose behaviour carries `append_system` and `effort`.
  **One pill.** The catch, named honestly since 0.31 (ENH-020): only the Claude Code record maps
  `system`/`append_system`/`model`/`effort` to flags; Codex and OpenCode map none. `thread/start`,
  `thread/resume` and `thread/set_mode` return `unmapped_behaviour` — hide the control for that
  provider rather than show one that does nothing.
- **Mid-thread.** `set_mode` reopens the provider on its own session id (D76). Safe on **Claude
  Code** (`--resume`) and **Codex** (`exec resume`), both measured. **OpenCode** is
  `session = "process"` — ACP's `session/load` is not wired — so a mode change mid-thread there is a
  fresh session with the conversation's memory gone. `set_mode` is not guarded against a running
  turn; the honest contract is *between turns*, and `Thread.turning` says which it is.

## 3. Holding a question across a process death

**Park; do not hold. The standing-answer code rebuilds D80 — delete it.**

`runtime/threads.py` — `_keep_pending` and `_settle_what_the_last_host_left`. Even with
`on_question="wait"`, the running turn's open questions are written to the record *as they open*
("so a host that dies with a card up leaves them where the next host finds them"), and the parked
act sleeps in the checkpointer. On `thread/resume`, a turn still `running` with a question open
becomes `parked`, the question is re-offered **with the same handle**, and `settle(handle, answer)`
runs the act from its checkpoint. No re-ask, no second card, no standing answer.

Handle identity: the executor's is `run_id:step_id` — stable for a step across parks (0.31's
BUG-055 fix leans on exactly this: the same run, the same step, one handle). What is on the record
is what the card had.

A Computer that may die should use `on_question="park"`: the request returns, the question is on
the record, and the lease is not burning while nobody answers — the clock runs only in a turn
(D90). Re-offering the Run on lease expiry is unnecessary.

## 4. Delegation

- **`runtime/children.py` is the runtime's mechanism; the agent reaches it through two doors the
  product turns on.** The `spawn` · `send` · `release` meta-tools on a `Pattern`
  (`orchestrator_workers` has them; `single` does not — that is the choice), and since 0.31 the
  registered `compose` component (`runtime/planning.py`), which a resident CLI reaches through the
  socket. Nothing else to register: a child is a run under a carved lease (D16, D37), admitted
  under the plan limits in force (D108, D109).
- **The parent's trail carries everything.** Only the root feeds the observer; a child forwards
  its events up (`runtime/loop.py`). So: `Spawned(child_run_id, lease)` on the parent, then the
  child's own `Started`, `Composed`, `Invoked`, `Observed`, `Spent`, `Ended` stamped with the
  child's `run_id`, and `Held` when the parent parks it. `run_items(nested=True)` folds them with
  `Item.parent = (run_id, step)` — the activity row's nesting is already computed.
- **A child's questions** arrive on the *same* host handle — `Approvals` is inherited by children
  (`runtime/bindings.py`) — and a step whose child parks parks itself with the child's question as
  its own (D57). On the wire `approval_request` carries `thread_id`.
- **Spend.** The child's lease is carved from the parent's (`LeaseMeter.carve`) and settles back
  (`settle`) — steps, cents, tokens, with `unpriced`/`unmetered` propagating. `thread/remaining` and
  `ThreadRecord.spent` already include children.

## 5. Capability inventory

**Not published, and the observation is structural, not a bug.** The registry's direction is *ours
→ the CLI* (D42): the kit offers the run's tools to Codex through the socket; a CLI's own tools, MCP
servers and plugins never come back. Codex's record says `tool_path = "uncontrolled"` because its
configured MCP servers cannot be excluded — the kit cannot enumerate what it cannot exclude.

What the kit publishes: `ProviderCapabilities` with evidence per axis — tool path, session,
interruptibility, streaming, reasoning, usage tokens, cost (Phase 31) — through `providers/list`
and `capabilities/check`; and `tools/list` · `skills/list` · `batteries/list` — what *we* offer,
each with the mode's judgement.

Routing by "what it can do" beyond those axes needs a new evidence axis measured by the status
probe. It is kit-shaped (two field runtimes have `mcp list`) but not planned — **ENH-025** below.

## 6. The trail's facts for edits and commands

- **Only what the component returned.** `Completed.output` is the component's; the kit computes no
  diffs. A command's output is capped by the environment's `output_limit` in bytes —
  `LocalEnvironment` defaults 64,000, `serve`'s composition sets 32,000, some sandbox backends
  4,000 — host-set, and the same on every CLI because it is *our* component running the command,
  not theirs. Inputs are bounded at 64 KiB with a marker (`Item.inputs`).
- **The cloud-safe projection stays the product's, for now.** It is the product's `ObserverPort`,
  which is where the kit puts "what leaves the process"; a second product needing the same policy
  makes it a kit adapter (the admission rule). The two facts a policy would key on already exist:
  `EffectProfile.reaches` and the `Posture` on every `Observed` (D30).

## 7. The served runtime

- **It is the intended cloud shape.** One `serve` process per deployment, many sessions, the
  product's backend in front — Phase 29's *one app server behind every surface* (D79–D86),
  `docs/consuming.md` ("the recommended shape … behind the product's backend"), and chapter 7 of
  the React demo (`--token`, `x-shadow-hdk-session`, `thread/start {principal}`, reattach with
  `Last-Event-ID`). In-process `Harness`/`Thread` and served are the *same* composition
  (`workshop()`); the wire adds process separation and language independence, nothing else. Keep
  in-process on the Computer; serve on the server.
- **Handing things to a served runtime.** Modes, rules, store, batteries, budget, provider, idle —
  `harness.toml` and store rows (`store/put`, `modes/list`, `rules/list`). Identity —
  `thread/start {principal, attributes, budget, requirements, plan_limits}` (D82).
- **The product's own tools are the honest gap.** Neither `Harness` nor `ServeHost` takes
  `components=`; a served thread's components are the serving process's. Today a product's tools
  reach a served thread as a **battery** — an MCP server declared in a file under `batteries_dir`
  (D70, `serve/batteries.py`, kinds `mcp` | `python`), switched on by rows. The record tools as one
  MCP server is that shape. A `components=` hand-in is **ENH-022** below.

## 8. Session resume

- **Supported and measured on Claude Code and Codex; not on OpenCode** (`session = "process"`). The
  same working tree is the product's side: the kit reopens on `resume=` at whatever `root` the
  record says (D76) and does not verify the tree matches.
- **When the vendor's session is gone: a failed turn, not a silent fresh session.** The CLI errors
  on its own resume flag, the stream ends without a done event, and the session returns
  `Turn(text="", failed=True)` with the CLI's stderr on `session.stderr`. The product can act on
  `failed`; there is no typed *session gone* kind — **ENH-024** below.

## 9. Spend

- **Show what the kit says.** `Usage` is `input_tokens`, `output_tokens`, `cost_cents`, each `None`
  when the source did not report; `Spent` carries `unpriced` and `unmetered` so a footer can be
  honest per call (D84, D90). The same shape for API-metered and CLI sources.
- **No cache-read or cache-write field, and not planned** — but it meets the admission rule (Claude
  Code reports cache-read and cache-creation tokens; Codex reports cached input): an additive kernel
  field and two dialect paths. **ENH-023** below.

## 10. Registration and composition

What to register and what to read is the map at the top. The single example that shows a product's
tools, authority, modes, rules and the two doors together did not exist when the questions were
asked; it is below. `examples/host/` composes the in-process door with its own governance and sink;
the React demo is the wire side; `docs/consuming.md` is the map.

---

## Composing the kit as a product

One composition, two doors. The product's parts are the same in both; only who owns the process
differs.

### The product's parts

```python
from shadow_hdk.adapters.basic import CallableComponents
from shadow_hdk.adapters.modes.registry import ModeSpec
from shadow_hdk.kernel import Behaviour, EffectProfile, PlanLimits, ScopeSet

# 1. Tools — an honest effect profile per tool; the mode judges the effects, never the name.
tools = CallableComponents()
tools.add(propose_claim, effects=EffectProfile(writes=ScopeSet.of("record")))
tools.add(ask_inquiry, effects=EffectProfile(writes=ScopeSet.of("record")))
tools.add(
    write_artifact,
    effects=EffectProfile(writes=ScopeSet.of("artifacts"), reaches=True, reversible=True),
)

# 2. Modes — the former personas as behaviour on a mode; plan mode is the read-only policy.
#    In code here; as documents under a modes directory or as store rows in a deployment.
DEEP_DIVE = ModeSpec.of(
    "deep-dive",
    name="Deep dive",
    behaviour=Behaviour(append_system="Go deep. Ask before assuming.", effort="high"),
    environment="workspace-write",
    plan=PlanLimits(depth=4, fan_out=8, steps=64),
)
PLAN = ModeSpec.of(
    "plan",
    name="Plan",
    behaviour=Behaviour(append_system="Propose a plan. Change nothing."),
    environment="read-only",
)

# 3. Rules — `ActRule` rows in the store (`rules` collection): deny, ask, allow, in that order.
# 4. Authority — the two one-protocol ports the product already implements:
#    `shadow_hdk.serve.HostAuthority`, `shadow_hdk.serve.HostAuthorizer`.
```

### Door one — in-process, where the product owns the process (a Computer)

```python
from dataclasses import replace
from pathlib import Path

from shadow_hdk.providers import environment_for, open_with, ready, search_dirs
from shadow_hdk.runtime import Approvals
from shadow_hdk.runtime.threads import Thread
from shadow_hdk.serve.host import a_lease, modes_for, workshop
from shadow_hdk.serve.stores import stores_for


async def open_thread(root: Path, *, principal: str, store_url: str) -> Thread:
    stores = stores_for(store_url)  # the product's rows, threads, parked runs, effect journal
    modes = modes_for(stores.store, files=root / ".harness" / "modes")  # rows and files, live

    # The shipped composition — environment, batteries, skills, `ask_person`, `compose` — with the
    # product's authority. Then the product's tools beside them: one registry, one judgement.
    ports = await workshop(
        root,
        mode="workspace-write",
        store=stores.store,
        modes=modes,
        authority=authority,
        authorizer=authorizer,
        effect_journal=stores.effects,
        principal=principal,
    )
    ports = replace(ports, components=(*ports.components, tools))

    # Whichever signed-in CLI this machine has (D41: nothing installed, no credential read).
    found = await ready()  # or ready("codex"); raises `NoProvider` naming what would fix it
    agent = await open_with(
        found.provider,
        binary=found.binary,
        env=environment_for(found.provider, base={}, search=search_dirs()),
        workspace=root,
    )

    return await Thread.open(
        agent=agent,
        ports=ports,
        store=stores.threads,
        root=root,
        lease=a_lease(),
        approvals=Approvals(),
        checkpointer=await stores.checkpointer(),
        modes=modes,
        mode="deep-dive",
        principal=principal,
        plan_limits=PlanLimits(depth=3, fan_out=8, steps=64),  # the host's ceiling; the mode narrows
    )
```

A turn is `thread.turn(text, on_question="park")` — the request returns; a question is on the
record with its handle; `thread.settle(handle, answer)` later, from any process that resumes the
thread. A question the agent asks the person is `ask_person`, already in the composition.

### Door two — served, behind the product's backend (the server)

The same parts, in a file the product's deployment writes and a process the product's backend
fronts. The product's tools reach the served thread as a battery (an MCP server), until
`components=` lands (ENH-022).

```toml
# harness.toml — every key maps to a port or a profile; an unknown key is refused by name
[environment]
root = "/srv/work"
mode = "workspace-write"

[provider]
want = ""                    # the first ready CLI, or claude-code / codex / opencode
idle_seconds = 900

[store]
url = "postgresql://…"       # threads, parked runs, rules, modes, the effect journal

[tools]
batteries = ["intent-studio-record"]   # the product's tools as an MCP server, by row (D70)

[budget]
steps = 400
seconds = 3600
cents = 500
```

```toml
# batteries/intent-studio-record.toml — the product's record tools behind the component port
[battery]
id = "intent-studio-record"
name = "Intent Studio — the record"
kind = "mcp"
command = "intent-studio-mcp"   # resolved on PATH; absent, a problem naming what would install it
args = ["--stdio"]

[tools.propose_claim]
effects = { writes = ["record"] }

[tools.write_artifact]
effects = { writes = ["artifacts"], reaches = true, reversible = true }
```

```bash
shadow-hdk serve harness.toml --http --port 8765 --token-file /run/secrets/harness-token
```

The backend then speaks the wire (the generated TypeScript client, or any language):
`thread/start {principal, attributes, mode, plan_limits}` → `turn/start {on_question: "park"}` →
`approvals/answer` from any later request → `thread/amend` to change a parked plan. Chapter 7 of
the React demo is this exact arrangement, with the reattach after a drop.

### What the two doors share

The record, the events, the fold, the questions, the lease, admission, authority — every mechanism
in this document — because they are one composition. A product that starts in-process and moves a
deployment behind `serve` changes where the process runs, not what it does.

---

## Follow-ups this raised — filed on the kit's backlog

| id | what | why it is the kit's |
|---|---|---|
| ENH-022 | `components=` on `ServeHost` and `Harness`, so a product's own tools join a served thread's registry without an MCP hop | the seam found answering question 7; every product with tools of its own meets it |
| ENH-023 | `Usage.cache_read_tokens` and `cache_write_tokens`, read from the Claude Code and Codex dialects | two field runtimes report it; a footer cannot be honest about cost without it |
| ENH-024 | a typed `session_gone` refusal when a CLI's resume flag is rejected, instead of a bare failed turn | the product can act on it without reading stderr; it is a measured CLI behaviour, not a product concept |
| ENH-025 | a capability-inventory evidence axis — a CLI's MCP servers and plugins — on the status probe | routing a Run by what a machine can do; two CLIs expose the list |
| ENH-026 | this chapter kept true: re-read at every release that touches a port it names | a chapter a product builds against is a contract |

What stays the product's: the artifact concept and its versions, the cloud-safe projection, the
persona *names*, the settings ladder that resolves a mode, and the backend that fronts `serve`.
