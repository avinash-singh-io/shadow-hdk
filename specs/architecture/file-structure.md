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
    adapters/
      basic/                         allow-all · stdout · callback · system clock · callable   Phase 0
      agent/                         the model loop as a component; Pattern; single            Phase 0
      langchain/                     one ModelPort over every LangChain provider; stream       Phase 1
      mcp/                           MCP servers as components                                 Phase 1
      modes/                         Mode · ModeGovernance                                     Phase 1
      workspace/                     files within a root                                       Phase 3
      sandbox_subprocess/            run code with limits                                      Phase 3
      acp/                           Codex · Claude Code over ACP                              Phase 4
      recording/                     our registry as an MCP server                             Phase 5
      effect_rules/                  rules as rows; the narrowing check                        Phase 10
      sandbox_gvisor/  sandbox_firecracker/                                                    Phase 11
      derivation/                    total expressions over typed tables                       Phase 12
      otel/                          the event stream exported                                 Phase 14
  patterns/                          single.md · plan-and-execute.md · … (data, not code)      Phase 0 / 8
  tests/
    invariants/                      stands alone · layering · no adapter cross-imports
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
