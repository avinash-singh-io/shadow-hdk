---
type: Architecture
---

# Adapters — every plug, and the contract each must satisfy

> Each adapter is its own package under `shadow_hdk.adapters.<x>`, importing `shadow_hdk.runtime`
> and `shadow_hdk.kernel` and **never another adapter**. Each subclasses the abstract contract
> suite for the port it implements (`tests/adapters/contract`), so "it implements the port" is a
> test result rather than a claim.

## The map

| adapter | port | phase | notes |
|---|---|---|---|
| `basic` — allow-all, **`Controlled`** (only controlled satisfies consent-before-effect, D30), stdout sink, **file sink** (JSON lines, on disk before it returns), callback observer, system clock, **callable** | governance · sink · observer · clock · component | 0 | `callable` turns a Python function into a component; it is how a product registers its own tools |
| `agent` | component · agent | 0 · 32 | the model loop as a component (D1), and `ModelAgent` as the same loop below `AgentPort`; patterns decide its meta-tools (D3) |
| `langchain` | model | 1 | one adapter over LangChain's integrations; `stream` for tokens |
| `mcp` | component | 1 | an MCP server's tools become components; annotations fill half a profile |
| `modes` | governance | 1 · 25 · 28 | a mode is a ceiling profile plus an ask line — data; since D64 a `ModeSpec` is policy + behaviour + presentation, and since D76 it names the environment mode it needs; four ship — `read-only`, `ask`, `workspace-write`, `full` — and the rest are files or store rows |
| `environment` | component | 22 · 28 | where effects land, with a mode, on one or many roots — the `workspace` and `sandbox_subprocess` adapters of Phase 3 folded into it (D48–D50, D76) |
| `acp` | model + component | 4 | OpenCode, or anything Zed-compatible, driven over the Agent Client Protocol |
| `jsonl` | agent | 20 | a CLI answering in line-delimited JSON — Claude Code, Codex — resident or per turn, resumed on its own session id (D76) |
| `recording` | component | 5 · 20 · 23 | an MCP server exposing our registry to a child agent; every call an observation. Served over a loopback socket through a relay console script (D44), and **nothing reaches it without the token the serve minted** — first line, constant time, refusals counted and never logged (D52). A call the policy asks about runs as a held child and the question is put to the host **live** while the CLI waits (D58) |
| `effect_rules` | governance | 10 | rules as rows over profiles, composed by intersection, with the narrowing check |
| `sandbox_gvisor`, `sandbox_firecracker` | component | 11 | contained execution |
| `derivation` | component | 12 | total expressions over typed tables |
| `otel` | observer | 14 | the run's shape as a trace over the OpenTelemetry API alone — ids, kinds, reasons, the lease, usage, an act's receipt; never a payload (D28) |
| `devices` | component | 15 | one device contract, three roles (D31): a sensor reads `world`, an actuator writes it irreversibly with the lease read at the act and a receipt, a witness reports acts it did not command as observed receipts; fakes ship; MQTT (16), OPC-UA and ROS 2 (`[~]`) are adapters over it |
| `modes` · `Routed` | governance | 30 | governance composed by routing (D92): one port per component name, another for the rest — a product's own constitution over its verbs, the shipped modes over the machine's operations, as one port |
| `postgres` | store · thread store · checkpointer | 29 | the record on Postgres (D79): `PostgresStore` and `PostgresThreads` hold the same contracts the sqlite ones do, over `psycopg`'s async pool; the checkpointer is LangGraph's own `AsyncPostgresSaver`; `[store] url = "postgresql://…"` fills all three — `[postgres]` extra |
| `mqtt` | component (devices) | 16 | MQTT topics as the three roles over `paho-mqtt` on 3.1.1: a subscribed topic is a sensor, a command topic an actuator (QoS 1; the receipt says `published`, or carries the device's own ack by key), an event topic a witness; the envelope is the payload (D32); a failed act breaks the link so nothing in flight is re-sent |
| device protocols — MQTT, OPC-UA, ROS 2 | component | epic 0007 | sensors read `{world}`; actuators write it irreversibly |

`ServeHost`/`Harness` are the ready-made production assembly: their store backend supplies a durable
effect journal, and their reference authority/authorizer bind an irreversible controlled act to the
current principal, scope and revision. A custom host may supply those ports. An adapter is called
`controlled` only where that common transaction boundary is honored; a generic remote irreversible
registration is deliberately downgraded to `observed`. OpenTelemetry records an `effect_recorded`
transition with status and digest, never an effect receipt, refusal detail, inputs or grant.

## The agent adapter — how one product gets ReAct and another gets an orchestrator

```python
@dataclass(frozen=True)
class Pattern:
    """An agent architecture, as data. Ships as a file; a team writes its own the same way."""

    name: str
    system: str  # the role prompt
    meta_tools: frozenset[str]  # which of compose · propose · done · spawn · … exist
    tool_names: frozenset[str] | None = None  # None → every component the policy leaves visible
    ceiling: EffectProfile | None = None  # narrows this role, beyond the mode
    max_turns: int = 12


single = Pattern("single", ROLE_SINGLE, meta_tools=frozenset({"propose", "done"}))
plan_and_execute = Pattern(
    "plan-and-execute", ..., meta_tools=frozenset({"compose", "propose", "done"})
)
orchestrator_workers = Pattern(
    "orchestrator-workers",
    ...,
    meta_tools=frozenset({"compose", "spawn", "send", "release", "propose", "done"}),
)
critic_pair = Pattern("critic-pair", ...)
reflect_until = Pattern("reflect-until", ...)
```

`single` offers no `compose` and no `spawn`, so the model **cannot** change its shape: it sees its
tools and answers. That is a fully deterministic one-agent product, with the same runtime a dynamic
product uses. Adding a pattern — today's or one invented in five years — is a file.

Since Phase 36 a pattern also carries `plan: PlanLimits | None` — met with the host's and the
mode's at admission (D109) — and `absorb: bool` (D112): `True`, the plan's results come back as
the tool result the model reads; `False`, the loop admits the plan, **defers** it, closes the
planner's step on the record and runs the plan as the same run's child — the planner is told it
was admitted, never its results. A refused plan is the tool result, every mismatch named (D111);
the `compose` meta-tool and the registered `compose` component (`runtime/planning.py`, D110) are
one path into `children.spawn`, and the loop treats a plan-labelled registration as its meta-tool
rather than a second tool, so `single` stays unable to plan.

```python
class AgentComponent(ComponentPort):
    def __init__(
        self, *, pattern: Pattern, effects: EffectProfile, name="agent", skill: Skill | None = None
    ): ...

    # No `tools=`: an agent sees what the run's registry leaves visible, which is the same
    # computation the policy narrows — so *what the model was offered* and *what the runtime will
    # let it invoke* cannot drift apart. A `skill` is checked against that before the first turn.

    async def invoke(self, registration, inputs) -> Observation:
        ctx = current_run()  # None → this agent is the root
        messages = [system(self.pattern.system), user(inputs["brief"])]
        for turn in range(self.pattern.max_turns):
            catalogue = self._visible(ctx) + self._meta()  # D13: filtered, then compacted
            response = await ports.model.complete(ModelRequest(tuple(messages), catalogue))
            if not response.tool_calls:
                return Completed({"text": response.text})
            composition = self._compose(
                response.tool_calls
            )  # n calls → FanOut; compose → as authored
            if composition is DONE:
                return Completed({"text": response.text, "proposals": self._proposed})
            async for event in run(composition, ports, options=ctx.spawn_options(...)):
                messages += self._as_tool_messages(event)
        return Completed({"text": ..., "truncated": True})
```

**The floor.** If the model says *done* before `lease.floor.min_steps`, the adapter nudges once —
*"you have not tried N things yet"* — and accepts the second answer. A model trained to be agreeable
gives up early; the floor is the honest counter, and one nudge is the whole of it.

**One product surface (Phase 32).** `ModelAgent(model, pattern)` implements `AgentPort` by running
this same loop against only the `ToolSource` handed to `open`. A `ModelPort` can therefore enter
`Thread`, `a_thread`, `Harness` or `ServeHost` through `model=` while a CLI enters through
`agent=`; construction refuses both together. The choice is below the durable boundary, so turn,
parking, holding, capability selection, usage, activity, interruption and resume retain one shape.
Interruption cancels an active model call, a parked child maps back to its durable run, and absent
provider usage remains unknown/unmetered rather than zero.

**Skills are a registry, offered as a component** (Phase 24, D54–D56). `SkillRegistry` is a union
of sources — `DirectorySkills` (shipped, or a team's directory of TOML), the host's own kept ones,
and `minted`, the run's own — later shadowing earlier by name, on the record. A skill says what it
is for (one line) and where it came from. `SkillComponents(registry, minting=)` registers
`use_skill` — pure; the names and lines ride its description; choosing runs D17's check against
`visible()` and the body arrives as the tool's answer — and `mint_skill`, which writes `{record}`:
it adds to `minted` and *proposes* `kind="skill"` through the sink. The runtime keeps nothing;
`kept_from(proposal)` is the host's half. Because it is a component, choosing and minting are steps
on the record and reach an in-process agent, an agent over the wire, and a CLI by subscription
through the registry socket alike — measured: a subscription provider chose a shipped skill and
followed it. The `skill=` on `AgentComponent` (a fixed procedure for a role) stays.

## The model adapter — one adapter, every provider

```python
class LangChainModel(ModelPort):
    def __init__(self, spec: str, **kw):  # "openai:gpt-…", "ollama:llama3.1", "huggingface:…"
        self._chat = init_chat_model(spec, **kw)

    async def complete(self, request) -> ModelResponse: ...
    async def stream(self, request) -> AsyncIterator[ModelChunk]: ...  # kernel minor bump, Phase 1
```

Providers are LangChain's integrations, each an optional extra checked by the licence test:
OpenAI and every OpenAI-compatible endpoint, Anthropic, **Ollama**, **HuggingFace**
(`langchain-huggingface` — Inference API, endpoints, local pipelines), Bedrock, Vertex, Mistral, and
the rest. We write a direct adapter only where LangChain has nothing — ACP is ours. LiteLLM is a
noted fallback, not adopted: two libraries for one job is a smell.

**Usage is honest.** A provider that reports no token count yields `Usage(None, None, None)` —
*unknown*, never zero. The meter treats unknown as unknown.

**Selection is evidence-backed (Phase 31, D96–D98).** Every provider record carries a typed
`ProviderCapabilities`: tool path (`controlled` through `uncontrolled`), session continuity,
interruptibility, streaming, reasoning and token/cost reporting. Each fact may carry measured,
derived, declared or unknown evidence; omission means `unknown`, never permission. `detect()` keeps
that record on `Available`, so discovery and construction compare the same facts. A host states
`ProviderRequirements`; the total compatibility check reports every mismatch in stable axis order
and construction refuses before the provider is opened.

The shipped records are deliberately unequal rather than normalized into a fictional common
denominator:

| provider | tool path | session | interrupt | stream | reasoning | tokens | cost |
|---|---|---|---|---|---|---|---|
| Claude Code | controlled | resumable | native | live | yes | yes | yes |
| Codex CLI | uncontrolled | resumable | terminate | live | unknown | yes | no |
| OpenCode | controlled | process | none | final | unknown | unknown | unknown |

Those are facts measured or derived at the dates in the provider files, not promises about future
versions. A third-party or handed provider starts entirely unknown unless its adapter supplies an
explicit record.

## The modes adapter — governance as data

```python
@dataclass(frozen=True)
class Mode:
    name: str
    ceiling: EffectProfile  # the widest thing anything may do
    ask_above: EffectProfile | None = None  # narrower than the ceiling → Ask instead of Allow


READ = Mode("read", EffectProfile(reads=EVERYTHING))
BUILD = Mode("build", EffectProfile(reads=EVERYTHING, writes=ScopeSet.of("workspace")))
ACT = Mode("act", ASSUME_WORST, ask_above=EffectProfile(reversible=True))
AUTO = Mode("auto", ASSUME_WORST)


class ModeGovernance(GovernancePort):
    def __init__(self, modes: Mapping[str, Mode], *, key="mode", default: str): ...
    async def judge(self, effects, context):
        mode = self._modes[context.attributes.get(self._key, self._default)]
        if not effects.narrows(mode.ceiling):
            return Refuse(f"{mode.name} does not permit this")
        if mode.ask_above and not effects.narrows(mode.ask_above):
            return Ask(self._question(effects))
        return Allow()
```

Two modes, ten, or one called `auto`: a different mapping, the same adapter. Layers compose by
`EffectProfile.meet`, so a team's layer can only narrow — proven by the kernel's property tests, not
by review. The full rules-as-rows engine with mode *files* checked in CI is `effect_rules`, Phase 10.

**What ships now** (D64, D75, D76). A `ModeSpec` is a policy, a behaviour (who the model is — a
system prompt, a model, an effort, mapped to the CLI's flags by the provider file), a
presentation (id, name, description) and the **environment mode it needs**. Four ship:

| mode | environment | judges |
|---|---|---|
| `read-only` | read-only | reads, the skills, the person, the web; nothing written or run |
| `ask` | workspace-write | the workspace is the ceiling; every write, run or delete inside it is asked about — Claude Code's *default*, Codex's *on-request* |
| `workspace-write` | workspace-write | writes and commands inside the roots, silently; the web hidden (it reaches, uncontained) |
| `full` | full | everything; a write outside the workspace, or a command that reaches, is asked about |

A `ModeSpec` also carries `plan: PlanLimits | None` (D109, Phase 36) — how much plan the mode
admits: depth, fan-out, steps. The shipped ceilings (`PLAN_OF`) narrow from `full` (4 · 32 · 256)
through `workspace-write` (4 · 16 · 128) to `ask` and `read-only` (3 · 8 · 64) — generous on
purpose, the lease the floor, but a ceiling so a runaway plan is refused before its first step.
A mode document's `[plan]` table inherits the named policy's value on any axis it leaves out and
is refused by name if it widens the policy on any axis (`widens_plan`, beside `widens`). The
conversation meets the host's limits with the mode's at every turn, so `set_mode` changes what
the next plan may be, live. A behaviour field the provider's record maps no flag for is named on
the session's `unmapped`, the thread's `unmapped_behaviour` and the wire — never dropped (D64,
ENH-020).

Yours are files (`modes/reviewer.md`) or store rows naming a shipped policy — never effects by
hand. The host's `ActRules` (D65, D85) are read in the field's order — **deny, then the
ceiling, then ask, then the mode, then allow**: a `deny` rule refuses in every mode, `full`
included; an `ask` rule puts the act to the person in every mode; an `allow` rule stands in for
the person only where the mode would have asked — a rule never widens a ceiling, and among the
rules that match the strongest decides whatever order they were written in. A rule's inputs may
be patterns (`"path": "finance/**"`, `"command": "git *"`) matched against the input as the tool
receives it — a path relative to the primary root, or `name/…` for another root. `Thread.set_mode` flips the policy, re-opens the environment when
the named environment mode differs, and reopens the provider on its own session so its
catalogue is the new mode's (BUG-032). A child run is judged in its parent's context (D74): the
mode a host set reaches every tool call, not only the turn's own step.

**Who a row is for** (D82). A rule or a mode may carry a `scope` — a principal's name, or
`attribute:value` in the product's own words (`tenant:acme`); empty is everyone. A thread is
opened for a `principal` with `attributes`, both on the record and on every judgement's context
(the turn's step, every tool call, the catalogue `tools()` judges); `ModeGovernance` reads a
rule only in its scope and a mode out of scope is *not a mode here*; the registries list in
scope when a thread is named (`rules/list {thread_id}`, `modes/list {thread_id}`) and everything
when none is — the operator's view. A rule made at a card is scoped to the person who answered
it; a rule for everyone is written to the store by whoever may write there. Two ways to keep
tenants apart, both named: **by scope** — one process, one store, rows and threads carrying the
tenant, the product's backend the only thing that reaches the bearer; **by process** — one
`serve` per tenant with its own `[store] url`, when the product's policy says rows must never
share a table. The kit does not choose; a product's own authorisation engine plugs into the
governance port and sees the same principal and attributes.

## Plugging your record in — the twenty lines a host writes

A host's memory, record or database is two things: **components** to read and write it, and a
**sink** to receive proposals. Nothing else.

```python
# 1 — the store's operations, as components
async def note_fact(subject: str, text: str) -> dict:
    ctx = current_run()
    ctx.propose(Proposal(kind="fact", payload={"subject": subject, "text": text},
                         provenance=Provenance("agent", "callable", ctx.now())))
    return {"noted": True}

record_tools = CallableComponents([
    callable_component(note_fact, effects=EffectProfile(writes=ScopeSet.of("record"), reversible=True)),
    callable_component(read_facts, effects=EffectProfile(reads=ScopeSet.of("workspace"))),
])

# 2 — the sink: where proposals become the host's truth
class MyStoreSink(SinkPort):
    async def propose(self, proposal: Proposal) -> None:
        if self.gate.admits(proposal):            # the host's policy, entirely the host's business
            await self.store.append(proposal.kind, proposal.payload, proposal.provenance)

ports = Ports(model=…, components=(record_tools, mcp_tools), governance=ModeGovernance(...),
              sink=MyStoreSink(store), observer=MyUiObserver(ws))
```

A product with its own domain verbs — two dozen ways to write to its record, say — is exactly this:
`callable` components with `writes: {record}, reversible: true, reaches: false`, whose
implementations propose, and a sink that is the host's gate. **The runtime never learns what a claim
is**, and that is the point of the example rather than the verbs themselves.

## Batteries — a tool consumed behind the component port (Phase 27, D70)

A *battery* is a file in `serve`'s `batteries_library` (or a directory, or a store row): an MCP
server — its command on PATH or through an environment variable — or a Python callable, the tools
to expose under the harness's names, and the **effects a deployment vouches for**. The MCP adapter
takes `only=`, `aliases=`, `effects=` for exactly this; a server that annotates nothing is assumed
the worst of until a file says otherwise. `wigolo` (web search and fetch; AGPL, its own process,
never linked) and `ddgs` (the light alternative, an optional extra) ship. A battery's profile is
honest — it reaches the web from a process outside the sandbox, `contained = false` — and the
modes judge it by that: `workspace-write` and `ask` hide it, `read-only` and `full` offer it; no
rule. A battery's process is a session leader the runtime holds (`start_held`, D53, BUG-033):
the MCP adapter's `held_stdio_client` is the SDK's transport with the process ours, ended with its
group on close and when the interpreter ends. What a run proposes for keeping — a minted skill —
is kept by the composition's sink (`KeepingSink`, ENH-011): a `skills` row, offered after a
restart with source `store`; every proposal still reaches the sink behind it. The composition
installs as one distribution, `shadow-hdk`, the shipped providers' transports (`jsonl` for
Claude Code and Codex, `acp` for OpenCode) in the base and the specialised SDKs as extras (D78).
**A parked run behind a port of ours** (D93): `RunStore` — four methods over bytes — with the
runtime library's checkpointer built over it (`runtime.checkpoints.saver_over`), so a product on
its own database keeps parked runs there with no knowledge of the library; `ServeHost(run_store=)`.
**Which batteries are on is rows** (D83): `[tools] batteries` seeds the store's `wanted`
collection (`{id, on}`) at the host's first open, a row already there left as it is, and from
then on the store rules — `store/put wanted ddgs {"id": "ddgs", "on": true}` opens it at the next
thread, `"on": false` closes it; a battery's server is the process's, not a thread's, so one
switched off is gone from every thread at once. `batteries/list` says on · off · unavailable by
those rows.

## The environment — where the agent's effects land (Phase 22, D48–D50)

Three adapters used to hold three opinions about one boundary — a workspace that checked every
path, a subprocess sandbox that checked nothing, a proven box for a third kind of run — and a mode
permitting workspace writes was told three different truths about what a write reaches. One was
false (BUG-018). They are **one environment with a mode** now:

```python
Mode = "read-only" | "workspace-write" | "full"

LocalEnvironment.open(root, mode=...)  # this machine, inside the OS sandbox
LocalEnvironment.open(workspace=Workspace((Root("finance", "…"), Root("sales", "…"))), mode=...)
SandboxEnvironment.open(backend, root, mode=...)  # a box somebody else built, root mounted
#   six operations, every environment: read_file · write_file · delete_file · list_dir ·
#                                      run_shell · run_python
#   every profile from ONE derivation — runtime.environment.effects_of(isolation, mode, operation)
#     `Isolation` is what is TRUE (writes confined, reads confined, network denied, proven) — set by
#     a watched denial (D36) or an honest no, never by a wrapper's claim
#     `Mode` is what is WANTED; a mode the isolation cannot make true is refused at construction
#     (CannotEnforce) rather than quietly widened
#   read-only:        writes = ∅;      write_file and delete_file are not offered at all
#   workspace-write:  writes = {workspace} iff confined and proven, else refused
#   full:             everything, said out loud — an ordinary host reaches the machine
```

`LocalEnvironment` wraps every command in `sandbox-exec` (macOS) or bubblewrap (Linux) — Codex's
model, consumed rather than rebuilt — and **proves it before it exists**: a write outside the root
must fail, a socket must fail, a write inside must succeed. What it declares is what the proof
found. Measured 2026-09-11 on macOS 26: *Operation not permitted*, denied, runs. Where no OS
sandbox exists, a confined mode refuses naming the fix; `full` always constructs.

**A workspace is one or many roots** (D76). `Workspace`/`Root` are kernel data — a name and a
path, the first the primary; VS Code's multi-root, Claude Code's `--add-dir`, Codex's
`writable_roots`. The environment opens on it: the OS profile allows writes under every root, the
proof writes inside *each* and outside *all*, and `inside()` resolves a path by the rule the
tools describe — another root's name wins (`sales/notes.md`), the primary's own name is not an
address (a relative path is relative to it), and an entry of the primary spelled like another
root is refused when that root is named, never guessed at per path (D77). `Environment.reopen`
takes a new workspace or a new mode, proves again, and refuses unchanged where it cannot; a
thread's `add_root` and a mode's `environment` go through it. The policy's scope stays
`workspace`; a rule that wants to tell roots apart names the path (D65).

`SandboxEnvironment` takes an `IsolationBackend` that can open a `Box` — run, read, write, delete,
list, close — and proves the box with **two** denials (D50): a socket, as Phase 11 did, and a write
outside the mount, which is the boundary BUG-018 was about. The first backend is OpenSandbox
(Docker locally; gVisor, Kata, Firecracker on a cluster; needs a server, and says so). E2B and
Daytona are the same seam, one adapter each. A box mounts one root and is proven for one mode;
it refuses a re-open honestly — a second root or another mode there is another box.

Every command runs on the runtime's leash inside the box — a timeout, a capped output, the
operator's environment withheld, the process tree killed with the step (D35). Widening — *may I
read elsewhere?* — is an `Ask`, not a tool.

`capabilities_of(isolation, mode)` projects the effective environment into
`EnvironmentCapabilities`: maximum read/write reach, network posture, secret posture and whether
the boundary was proven. Requirements are upper bounds (`reads_within`, `writes_within`) plus
optional denied-network, denied-secrets and proof requirements. On the measured macOS local
workspace mode, writes are workspace-confined and network is denied, while reads remain
machine-wide and process secrets remain ambient; the report says exactly that. `LocalEnvironment`
and `SandboxEnvironment` reject an incompatible `EnvironmentRequirements` with the same typed
`IncompatibleCapabilities` result used at every other construction door.

## Contract suites — what every adapter must pass, and what a product runs against its own

Shipped as `shadow_hdk.testing.contracts` (D91): a product implementing a port subclasses the
suite in its own tests and hands it a fresh implementation; `shadow_hdk.testing.providers`
ships a scripted `AgentPort` for the tests that open a thread on nothing.

| suite | asserts |
|---|---|
| `ComponentPortContract` | registrations are well-formed and stable; unknown id → `Failed`, never an exception; every observation round-trips through JSON; effects are declared (never `None`) |
| `ModelPortContract` | a tool-less request returns text; a request with tools may return calls whose arguments are JSON; unknown usage is `None`, never `0` |
| `GovernancePortContract` | total over the profile lattice: never raises; `NOTHING` is never refused; `ASSUME_WORST` under a narrow ceiling is refused |
| `SinkPortContract` | accepts every `Proposal` shape; never raises for a well-formed one |
| `ObserverPortContract` | accepts every event kind; a raising observer does not fail a run |
| `ClockPortContract` | `now()` is monotone non-decreasing; `new_id()` never repeats within a process |
| `StoreContract` | rows round-trip; `put` replaces; a version moves per collection, and deleting nothing moves nothing (D66) |
| `ThreadStoreContract` | a record round-trips field for field (pending questions included, D80); listing hides archived unless asked; **one holder at a time** — a hold is exclusive while it lives, its holder keeps and renews it, release frees it, a stranger's release changes nothing, and it lapses when nobody renews (D81) |
