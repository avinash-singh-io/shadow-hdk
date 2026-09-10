---
type: Architecture
---

# Adapters — every plug, and the contract each must satisfy

> Each adapter is its own package, `shadow-hdk-adapters-<x>`, importing `shadow_hdk.runtime`
> and `shadow_hdk.kernel` and **never another adapter**. Each subclasses the abstract contract
> suite for the port it implements (`tests/adapters/contract`), so "it implements the port" is a
> test result rather than a claim.

## The map

| adapter | port | phase | notes |
|---|---|---|---|
| `basic` — allow-all, **`Controlled`** (only controlled satisfies consent-before-effect, D30), stdout sink, **file sink** (JSON lines, on disk before it returns), callback observer, system clock, **callable** | governance · sink · observer · clock · component | 0 | `callable` turns a Python function into a component; it is how a product registers its own tools |
| `agent` | component | 0 | the model loop as a component (D1); patterns decide its meta-tools (D3) |
| `langchain` | model | 1 | one adapter over LangChain's integrations; `stream` for tokens |
| `mcp` | component | 1 | an MCP server's tools become components; annotations fill half a profile |
| `modes` | governance | 1 | a mode is a ceiling profile plus an ask line — data |
| `workspace` | component | 3 | files within a root; `writes: {workspace}` |
| `sandbox_subprocess` | component | 3 | run code with limits; `contained` only where the deployment says so |
| `acp` | model + component | 4 | Codex or Claude Code driven over Zed's Agent Client Protocol |
| `recording` | component | 5 | an MCP server exposing our registry to a child agent; every call an observation |
| `effect_rules` | governance | 10 | rules as rows over profiles, composed by intersection, with the narrowing check |
| `sandbox_gvisor`, `sandbox_firecracker` | component | 11 | contained execution |
| `derivation` | component | 12 | total expressions over typed tables |
| `otel` | observer | 14 | the run's shape as a trace over the OpenTelemetry API alone — ids, kinds, reasons, the lease, usage, an act's receipt; never a payload (D28) |
| `devices` | component | 15 | one device contract, three roles (D31): a sensor reads `world`, an actuator writes it irreversibly with the lease read at the act and a receipt, a witness reports acts it did not command as observed receipts; fakes ship; MQTT (16), OPC-UA and ROS 2 (`[~]`) are adapters over it |
| `mqtt` | component (devices) | 16 | MQTT topics as the three roles over `paho-mqtt` on 3.1.1: a subscribed topic is a sensor, a command topic an actuator (QoS 1; the receipt says `published`, or carries the device's own ack by key), an event topic a witness; the envelope is the payload (D32); a failed act breaks the link so nothing in flight is re-sent |
| device protocols — MQTT, OPC-UA, ROS 2 | component | epic 0007 | sensors read `{world}`; actuators write it irreversibly |

## The agent adapter — how one product gets ReAct and another gets an orchestrator

```python
@dataclass(frozen=True)
class Pattern:
    """An agent architecture, as data. Ships as a file; a team writes its own the same way."""
    name: str
    system: str                                   # the role prompt
    meta_tools: frozenset[str]                    # which of compose · propose · done · spawn · … exist
    tool_names: frozenset[str] | None = None      # None → every component the policy leaves visible
    ceiling: EffectProfile | None = None          # narrows this role, beyond the mode
    max_turns: int = 12

single              = Pattern("single", ROLE_SINGLE, meta_tools=frozenset({"propose", "done"}))
plan_and_execute    = Pattern("plan-and-execute", ..., meta_tools=frozenset({"compose", "propose", "done"}))
orchestrator_workers= Pattern("orchestrator-workers", ..., meta_tools=frozenset({"compose", "spawn", "send", "release", "propose", "done"}))
critic_pair         = Pattern("critic-pair", ...)
reflect_until       = Pattern("reflect-until", ...)
```

`single` offers no `compose` and no `spawn`, so the model **cannot** change its shape: it sees its
tools and answers. That is a fully deterministic one-agent product, with the same runtime a dynamic
product uses. Adding a pattern — today's or one invented in five years — is a file.

```python
class AgentComponent(ComponentPort):
    def __init__(
        self, *, pattern: Pattern, effects: EffectProfile, name="agent", skill: Skill | None = None
    ): ...
    # No `tools=`: an agent sees what the run's registry leaves visible, which is the same
    # computation the policy narrows — so *what the model was offered* and *what the runtime will
    # let it invoke* cannot drift apart. A `skill` is checked against that before the first turn.

    async def invoke(self, registration, inputs) -> Observation:
        ctx = current_run()                                  # None → this agent is the root
        messages = [system(self.pattern.system), user(inputs["brief"])]
        for turn in range(self.pattern.max_turns):
            catalogue = self._visible(ctx) + self._meta()    # D13: filtered, then compacted
            response  = await ports.model.complete(ModelRequest(tuple(messages), catalogue))
            if not response.tool_calls:
                return Completed({"text": response.text})
            composition = self._compose(response.tool_calls) # n calls → FanOut; compose → as authored
            if composition is DONE:
                return Completed({"text": response.text, "proposals": self._proposed})
            async for event in run(composition, ports, options=ctx.spawn_options(...)):
                messages += self._as_tool_messages(event)
        return Completed({"text": ..., "truncated": True})
```

**The floor.** If the model says *done* before `lease.floor.min_steps`, the adapter nudges once —
*"you have not tried N things yet"* — and accepts the second answer. A model trained to be agreeable
gives up early; the floor is the honest counter, and one nudge is the whole of it.

## The model adapter — one adapter, every provider

```python
class LangChainModel(ModelPort):
    def __init__(self, spec: str, **kw):          # "openai:gpt-…", "ollama:llama3.1", "huggingface:…"
        self._chat = init_chat_model(spec, **kw)
    async def complete(self, request) -> ModelResponse: ...
    async def stream(self, request) -> AsyncIterator[ModelChunk]: ...   # kernel minor bump, Phase 1
```

Providers are LangChain's integrations, each an optional extra checked by the licence test:
OpenAI and every OpenAI-compatible endpoint, Anthropic, **Ollama**, **HuggingFace**
(`langchain-huggingface` — Inference API, endpoints, local pipelines), Bedrock, Vertex, Mistral, and
the rest. We write a direct adapter only where LangChain has nothing — ACP is ours. LiteLLM is a
noted fallback, not adopted: two libraries for one job is a smell.

**Usage is honest.** A provider that reports no token count yields `Usage(None, None, None)` —
*unknown*, never zero. The meter treats unknown as unknown.

## The modes adapter — governance as data

```python
@dataclass(frozen=True)
class Mode:
    name: str
    ceiling: EffectProfile                      # the widest thing anything may do
    ask_above: EffectProfile | None = None      # narrower than the ceiling → Ask instead of Allow

READ  = Mode("read",  EffectProfile(reads=EVERYTHING))
BUILD = Mode("build", EffectProfile(reads=EVERYTHING, writes=ScopeSet.of("workspace")))
ACT   = Mode("act",   ASSUME_WORST, ask_above=EffectProfile(reversible=True))
AUTO  = Mode("auto",  ASSUME_WORST)

class ModeGovernance(GovernancePort):
    def __init__(self, modes: Mapping[str, Mode], *, key="mode", default: str): ...
    async def judge(self, effects, context):
        mode = self._modes[context.attributes.get(self._key, self._default)]
        if not effects.narrows(mode.ceiling):              return Refuse(f"{mode.name} does not permit this")
        if mode.ask_above and not effects.narrows(mode.ask_above): return Ask(self._question(effects))
        return Allow()
```

Two modes, ten, or one called `auto`: a different mapping, the same adapter. Layers compose by
`EffectProfile.meet`, so a team's layer can only narrow — proven by the kernel's property tests, not
by review. The full rules-as-rows engine with mode *files* checked in CI is `effect_rules`, Phase 10.

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

## The workspace and code adapters — the agent writes things

```python
WorkspaceComponents(root: Path)      # read_file · write_file · list_dir · delete_file
#   write_file: EffectProfile(writes=ScopeSet.of("workspace"), reversible=True)
#     (corrected 2026-09-10, BUG-008: the code does not set `contained`, and a spec that says it
#      does invites a rule to be written against a field nobody sets)
#   every path resolved and refused outside root — the adapter's own invariant, not governance's

SubprocessSandbox(root, *, timeout_s, memory_mb, network=False, contained: bool)
#   memory_mb caps the child's address space with `prlimit` **on Linux**; macOS has no `prlimit`
#   and refuses `RLIMIT_AS`, so there it is not a limit. `runtime.leash.MEMORY_LIMIT_ENFORCED`
#   says which. (Corrected 2026-09-10, BUG-009: it was documented and did not exist at all.)
#   A leashed program runs in its own process group and the group is killed when the leash
#   returns, so nothing it started outlives the step (D35). `HOME` is not in its environment.
#   run_python · run_shell — EffectProfile(writes={workspace}, reaches=network,
#                                          reversible=False, contained=contained, costs=False)
```

A deployment that is not contained registers the sandbox with `contained=False`; a mode whose ceiling
requires `contained` then **refuses** it, and the component is not even visible to the model. So "may
the agent run code here" is a deployment fact expressed once, not a branch in the loop. Writing a
markdown file, rendering an HTML page, or generating a script is the workspace component; running the
script is the sandbox.

## Contract suites — what every adapter must pass

| suite | asserts |
|---|---|
| `ComponentPortContract` | registrations are well-formed and stable; unknown id → `Failed`, never an exception; every observation round-trips through JSON; effects are declared (never `None`) |
| `ModelPortContract` | a tool-less request returns text; a request with tools may return calls whose arguments are JSON; unknown usage is `None`, never `0` |
| `GovernancePortContract` | total over the profile lattice: never raises; `NOTHING` is never refused; `ASSUME_WORST` under a narrow ceiling is refused |
| `SinkPortContract` | accepts every `Proposal` shape; never raises for a well-formed one |
| `ObserverPortContract` | accepts every event kind; a raising observer does not fail a run |
| `ClockPortContract` | `now()` is monotone non-decreasing; `new_id()` never repeats within a process |
