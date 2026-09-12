---
type: Plan
phase: 27
---

# Plan — Phase 27

## Group 1 — a battery is a file
`shadow_hdk.serve.batteries`: a `Battery` (id, name, kind `mcp` | `python`, command and
args or a dotted callable, the tools to expose — each with the harness's name and a declared
`EffectProfile` — a licence note, and what to say when it cannot run); shipped battery files
in the serve package (`wigolo.toml`, `ddgs.toml`); `BatteryRegistry` over sources — shipped,
a directory, a store (`store_batteries`) — so the invariant that every registry has a store
source holds. `McpComponents` grows `only=`, `aliases=` and `effects=`: a deployment vouching for
a tool's effects is what the adapter's docstring always allowed for, and the names it exposes
are the harness's. A battery that cannot start (its command absent) is a *problem* the registry
reports, never a silent absence. RED: a scripted MCP server in a test, exposed as `web_search`
with `reaches=True`, refused by a mode that narrows `reaches` and allowed by one that does not.

## Group 2 — batteries in the composition
`[tools] batteries = ["web"]` in `harness.toml`; `workshop(batteries=)` starts each battery and
offers its components beside the environment's; `ServeHost` and `a_thread` take them. Live: wigolo
installed into the scratchpad (`npm i wigolo`, never globally), run as its stdio MCP server, a
search through the studio on the subscription — or, recorded honestly, `ddgs` where wigolo cannot
run here.

## Group 3 — the facade
`Harness` in `shadow_hdk.serve` (the decision: one package is the host's front door,
in-process and over the wire). `Harness.load("harness.toml")` and `Harness(root=, mode=, …)`;
`async with h:` opens a thread; `h.turn(text)` yields *parts* — events, items and activity in
order, the turn's record last; `h.approvals`, `h.set_mode`, `h.thread` for everything deeper.
`[budget]` in the file (`steps`, `seconds`, `cents`) is a `Lease` underneath — the owner's word
for it in the file and the facade, the kernel's underneath. Two invariants: the facade's module
imports only public names of the port packages (an AST walk; no `_name` anywhere); every
`harness.toml` key maps to a port or a profile (a table in the test walked against the loader's
`KNOWN`). RED: the three lines against a scripted provider.

## Group 4 — the examples reduced
`examples/coder` and `examples/host` on the facade; the studio unchanged (it is the wire's).
README: the three lines, run for real by a test.

## Group 5 — the optimiser port, specified
an `optimiser` document under the architecture specs: the port (`OptimiserPort.improve(program, evaluator) →
program`), what a program is here (a mode's behaviour, a skill's text, a pattern's prompt — all
data), the locked evaluator Rule 11 requires before any loop, and what DSPy would sit behind it.
Not built.

## Close
Decisions; index; status/roadmap/changelog/README; version per D9; land; board.
