---
type: Architecture
---

# File structure — where everything lives

One distribution, `shadow-hdk`, one import name, `shadow_hdk`; the specialised SDKs are extras
(D78). Phase numbers say when a part arrived; the tree is the one on disk, and an invariant refuses
a document that names a path that is not there.

```
shadow-hdk/
  pyproject.toml                     the one distribution: dependencies, extras, scripts, entry points; ruff · mypy · pytest
  src/shadow_hdk/
    __init__.py  py.typed            the package, and its typing marker — once, at the root
    kernel/                          pure types, imports nothing                                     Phase 0
      effects.py  components.py  composition.py  observations.py  leases.py  events.py
      ports.py                       the ports — Model · Component · Governance · Sink · Observer ·
                                     Clock · Agent · ThreadStore · Store
      contracts.py                   the published schemas; dump · load · round_trip
      activity.py  usage.py          what is happening beside the record (D63); what a step spent
      threads.py                     ThreadRecord · TurnRecord — turns, mode, roots, environment, session id
      workspace.py                   Workspace · Root — one or many roots, the first the primary (D76)
      rules.py  providers.py         ActRule (D65); Provider · Behaviour — a provider is a file (D40, D64)
    runtime/                         depends only on the kernel                                     Phase 0
      __init__.py                    run · resume · current_run · Ports · RunOptions · Approvals
      bindings.py                    Ports · RunOptions · RunContext · the contextvar; spawn_options
      session.py  emit.py            Session · LeaseMeter; Emitter — seq · clock stamp · queue
      registry.py  inputs.py         Registry — union of component ports; bindings → JSON
      step.py  compile.py  state.py  loop.py   the seven moves; Composition → StateGraph; run · resume
      children.py  cancel.py         spawn · send · release; held children; cancellation (D15, D16)
      approvals.py  person.py        the host's handle for a live question (D58); ask_person (D65)
      planning.py                    compose — a plan proposed as a component (D110); admitted in children.spawn (D108)
      items.py  replay.py            the fold: events → items (D46); replay determinism
      environment.py  leash.py       an environment has a mode and a workspace (D48, D76); the leash
      processes.py  lines.py         start_held — the one place a session leader starts (D77); LineBuffer
      threads.py  offer.py           Thread (D62); the registry offered to an agent that owns its loop
      store.py  switched.py          InMemoryStore (D66); a port minus what the store switches off
      acting.py  devices.py  trust.py  clock.py  errors.py
      testing/                       InMemoryComponents · ScriptedModel · ListSink · ListObserver · FixedClock
    wire/                            JSON-RPC 2.0 over stdio and HTTP/SSE                            Phase 9 · 26
      protocol.py  peer.py  channel.py  context.py  remote.py
      sides.py                       HostSide · RuntimeSide — the inverted ports (D21)
      threads.py                     ThreadHost · ThreadMethods — thread/* · turn/* · approvals/* · store/* ·
                                     tools/list · skills/list · files/* (D67, D73, D76)
      serve.py  stdio.py             the loopback listener with SSE; newline-delimited JSON on a pipe
      schemas.py                     publish · published — the schemas/ directory
    providers/                       your key, or your subscription                                 Phase 20
      resolution.py  probes.py  environment.py  surface.py  library.py
      library/                       claude-code.toml · codex.toml · opencode.toml — a provider is a file
    serve/                           the front door                                                Phase 26 · 27
      host.py                        ServeHost (the wire's ThreadHost) · workshop · a_thread · modes_for · skills_for
      facade.py  config.py           Harness — three lines; harness.toml, every key a port or a profile (D71)
      batteries.py  web.py           a battery is a file (D70); batteries_library/ (wigolo, ddgs)  [search]
      keeping.py                     KeepingSink — what a run proposes for keeping, kept (ENH-011)
      stores.py                      stores_for(url) — the Store, the ThreadStore and the checkpointer from one url (D79)
      __main__.py                    shadow-hdk serve [harness.toml] --stdio | --http [--page]
    testing/                         what a product tests with (D91): contracts.py — one suite per
      contracts.py  providers.py     port, shipped; providers.py — a scripted AgentPort; the runtime's doubles re-exported
    adapters/
      basic/                         allow-all · Controlled · stdout · file · callback · system clock ·
                                     callable · SqliteStore · SqliteThreads                        Phase 0
      agent/                         the model loop as a component; patterns; the skill registry
        library/  skills_library/    the shipped patterns and skills, as TOML                       Phase 0 · 8 · 24
      langchain/                     one ModelPort over every LangChain provider; stream  [langchain]  Phase 1
      mcp/                           MCP servers as components; held.py — the server's process ours  Phase 1 · 28
      acp/                           an agent over ACP — OpenCode, anything Zed-compatible           Phase 4
      jsonl/                         a CLI answering in line-delimited JSON — Claude Code, Codex     Phase 20
      recording/                     our registry as an MCP server over an authenticated socket     Phase 5 · 23
      modes/                         ModeSpec · ModeRegistry · ActRules; rules as rows; mode files   Phase 1 · 10 · 25
      environment/                   local on the OS sandbox; a box (OpenSandbox)  [sandbox]; one or many roots  Phase 22 · 28
      derivation/                    total expressions over typed tables                          Phase 12
      otel/                          the event stream exported as a trace  [otel]                 Phase 14
      devices/                       sensors, actuators, witnesses                                Phase 15
      mqtt/                          one link, three roles over MQTT 3.1.1  [mqtt]                Phase 16
      postgres/                      the record on Postgres — PostgresStore · PostgresThreads · the checkpointer  [postgres]  Phase 29
  docs/packages/                     one page per part — what it is for, its seams, its decisions
  schemas/                           the published contracts, one JSON Schema each, and index.json
  clients/typescript/                types generated from the schemas; a thin JSON-RPC/SSE client (D68)
  tests/
    invariants/                      the properties, held by walks (see testing.md)
    kernel/  runtime/  wire/  providers/  serve/
    adapters/
      contract/                      the doubles held to the shipped suites (the suites themselves ship: src/shadow_hdk/testing/)
      <adapter>/                     each adapter's own tests, subclassing its contract suite
    testing/                         the shipped suites and doubles, proven from the wheel
    test_bare_harness.py             the definition of done
    test_the_*_example.py            the examples, driven
  examples/
    bare.py  real.py                 the bare demo; the demo on real components
    coder/                           a coding agent on the facade — three lines
    host/                            the deep demonstration: a product's own governance, record, view
    studio/                          a page shadow-hdk serve serves; talks the wire only (D69)
  specs/                             momentum: vision · planning · architecture · phases · decisions · backlog
  .github/workflows/                 ci (ruff · format · mypy · pytest · the TypeScript client) · publish · live
```

## Rules that shape it

- **One distribution, one import name.** `shadow-hdk` on PyPI; `shadow_hdk` in code — an ordinary
  package with `__init__.py`, its parts subpackages. The specialised SDKs are extras
  (`[langchain]` and its providers, `[mqtt]`, `[otel]`, `[sandbox]`, `[search]`, `[all]`); the
  part that needs one imports it lazily and names the extra when it is missing (D78).
- **Layering is a test.** `tests/invariants` walks the AST: nothing under `src/shadow_hdk/`
  imports a product; the kernel imports no I/O, clock, logging or framework; the runtime imports no
  adapter; no adapter imports another; the wire and the providers import no adapter. And a base
  install needs no extra: every third-party import outside an extra's part is in the base
  dependencies — by a walk, not by trust.
- **A demo outside the tree.** `../shadow-hdk-demo/` (not in this repository) runs the studio over
  this package by path, editable — how a product consumes it before pinning the release.
