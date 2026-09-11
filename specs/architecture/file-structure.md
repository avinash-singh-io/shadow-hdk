---
type: Architecture
---

# File structure — where everything lives, and when it arrives

```
shadow-hdk/
  pyproject.toml                     uv workspace root; package = false; ruff · mypy · pytest config
  packages/
    kernel/                          shadow-hdk-kernel                        ✅ shipped
      src/shadow_hdk/kernel/
        __init__.py  effects.py  components.py  composition.py
        observations.py  leases.py  events.py  ports.py  contracts.py  py.typed
    runtime/                         shadow-hdk                               Phase 0
      src/shadow_hdk/runtime/
        __init__.py                  run · resume · current_run · Ports · RunOptions
        bindings.py                  Ports · RunOptions · RunContext · the contextvar
        session.py                   Session · LeaseMeter · Handles
        emit.py                      Emitter — seq · clock stamp · queue · observer task
        registry.py                  Registry — union of component ports; resolve · visible
        inputs.py                    bindings → JSON; DanglingRef
        step.py                      StepExecutor.invoke — the seven moves
        compile.py                   Composition → StateGraph; structural-hash cache
        state.py                     RunState + reducers
        loop.py                      run · resume — Started … Ended, child forwarding
        errors.py                    LeaseExhausted · Cancelled · PortFailure · DanglingRef
        testing/                     InMemoryComponents · ScriptedModel · ListSink · ListObserver · FixedClock
    providers/                       shadow-hdk-providers                     Phase 20
      src/shadow_hdk/providers/
        resolution.py                every candidate, and further than PATH
        probes.py                    version · authentication · the five answers
        environment.py               set · strip · backfill, from the record not a branch
        library.py                   a provider is a file
        surface.py                   detect · open — by entry point, importing no adapter
        library/                     the shipped providers, as TOML a team can read and edit
    adapters/
      basic/                         allow-all · stdout · callback · system clock · callable   Phase 0
      agent/                         the model loop as a component; Pattern; single            Phase 0
        library/                     the shipped patterns, as TOML a team can read and edit    Phase 8
      langchain/                     one ModelPort over every LangChain provider; stream       Phase 1
      mcp/                           MCP servers as components                                 Phase 1
      acp/                           an agent over ACP — OpenCode, anything Zed-compatible      Phase 4
      jsonl/                         a CLI answering in line-delimited JSON — Claude Code, Codex  Phase 20
      recording/                     our registry as an MCP server                             Phase 5
      modes/                         rules as rows; the narrowing check                        Phase 1 / 10
      environment/                   where effects land, with a mode; local on the OS sandbox   Phase 22
      derivation/                    total expressions over typed tables                       Phase 12
      otel/                          the event stream exported                                 Phase 14
      devices/                       sensors, actuators, witnesses                             Phase 15
      mqtt/                          one link, three roles over MQTT 3.1.1                     Phase 16
  tests/
    invariants/                      stands alone · layering · no adapter cross-imports · every port
                                     contracted · the decision map · these documents
    kernel/                          order properties · leases · contracts round-trip
    runtime/                         compile · governance · leases · events · spawn · errors · replay · benchmark
    adapters/
      contract/                      one abstract suite per port
      <adapter>/                     each adapter's own tests, subclassing its contract suite
    test_bare_harness.py             the definition of done
  examples/
    bare.py                          the demo the bare-harness test drives
  specs/                             momentum: vision · planning · architecture · epics · phases · decisions
  .github/workflows/ci.yml           ruff · ruff format · mypy · pytest · benchmark report
```

## Rules that shape it

- **One import name.** `shadow_hdk` is a PEP 420 namespace package: every package contributes
  `src/shadow_hdk/<part>/`. There is never a `shadow_hdk/__init__.py`.
- **Distributions.** `shadow-hdk-kernel`, `shadow-hdk` (the runtime), and
  `shadow-hdk-adapters-<x>` — versioned together until 1.0 (D9).
- **Layering is a test.** `tests/invariants` walks the AST: nothing under `packages/` imports a
  product; the kernel imports no I/O, clock, logging or framework; the runtime imports no adapter;
  no adapter imports another.
- **Optional extras carry providers.** `shadow-hdk-adapters-langchain[ollama,huggingface,anthropic]`
  — the base install pulls no provider SDK, and the licence test gates every extra.
