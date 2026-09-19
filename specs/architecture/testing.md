---
type: Architecture
---

# Testing — the layers, and every case

> Rule 13 is on: every group starts red, and **every assertion is mutation-checked** — change the
> code so the assertion should fail, confirm it does, revert. An assertion that cannot fail is
> deleted, not kept.

## Layers

| layer | what it proves | where |
|---|---|---|
| kernel unit + property | the order is an order; the meet is a greatest lower bound; leases carve | `tests/kernel/` ✅ |
| runtime unit | the governed step, the compiler, leases, events, spawning, errors | `tests/runtime/` |
| contract suites | every adapter satisfies the port it claims — and so does a product's own implementation: the suites ship as `shadow_hdk.testing.contracts` (D91) | `src/shadow_hdk/testing/contracts.py`, run from `tests/adapters/<x>/` |
| adapter tests | each adapter's own behaviour, against a fake of the thing it wraps — or the thing itself where a fake would prove nothing: the Postgres adapter runs against a real server named by `SHADOW_HDK_TEST_POSTGRES_URL` (CI's service container; the desk's own), and skips, saying so, without one (D79) | `tests/adapters/<x>/` |
| determinism | two runs, same inputs, identical streams | `tests/runtime/test_replay.py` |
| benchmark | the per-step budget holds (D11) | `tests/runtime/test_benchmark.py` |
| invariants | the decoupling is a property, not a claim — including that no vendor's name is in the kernel's or the runtime's code (D40, Phase 45) | `tests/invariants/` ✅ |
| the bare harness | "generic" is true | `tests/test_bare_harness.py` |
| the OS layer | the Linux helper watched denying and allowing on a kernel — a write outside, a socket, io_uring, a write inside, the exit codes — compiled out off Linux; the argument parser everywhere | `native/sandbox/tests/confines.rs`, `native/sandbox/src/args.rs` (`cargo test`) |
| the runners | the same suite on every operating system the kit claims and on every Python it claims (3.12 · 3.13 · 3.14, ENH-032), each asserting the mechanism in force before it runs: Linux with the helper (`landlock`), Linux with the helper set aside (`bubblewrap`, the AppArmor sysctl), macOS (`seatbelt`); the crate's gate; the helper's four platform wheels built and the x86_64 one installed and watched confining — a red job blocks a release (Epic 0010, D126) | `.github/workflows/ci.yml`, `.github/workflows/helper-wheels.yml` |

## Cases — Phase 0

**`runtime/test_compile.py`**
- each step kind compiles to the documented node shape
- one `Invoke` runs one node and yields `Invoked` then `Observed`
- `Sequence` preserves order under repeated runs
- `FanOut`: every child is `Invoked` before any child's `Observed` (barrier stub) — real concurrency
- `Until` stops when the condition is satisfied
- `Until` stops at `max_iterations` and says so
- a nested composite compiles to a subgraph with its own namespace
- a `Binding(ref=…)` resolves from an earlier step's handle
- a dangling ref is a `Failed` observation, not an exception
- the same composition compiles once — the structural-hash cache is hit (D11)

**`runtime/test_governance.py`**
- `Refuse` → `Refused` event **and** `Refused` observation; the component is never called
- `Ask` → `Asked` event, the run parks, `resume(Allow)` invokes the component
- `resume(Refuse)` → refused, component never called
- `Context` carries run id, step id, principal and the opaque attributes verbatim
- governance is called **before** every step, including inside a `FanOut` child

**`runtime/test_leases.py`**
- the step ceiling ends the run `lease_exhausted` before step n+1 begins
- the wall ceiling ends it (fixed clock advanced)
- the cost ceiling ends it, charged from model usage
- a child is carved and the parent is debited by the carve
- a child asking for more than the parent has left → `Failed`, parent unharmed
- unknown usage does not charge zero — it charges unknown and the meter says so
- the floor is visible to the agent adapter and one nudge is issued before `gave_up`

**`runtime/test_events.py`**
- `seq` starts at 0 and strictly increases across the whole run
- every event carries the clock port's stamp, never a real clock
- `Started` is first, `Ended` is last, exactly once each
- an observer that raises does not fail the step, and the failure is counted
- the iterator and the observer see identical sequences

**`runtime/test_spawn.py`**
- a `run()` inside a step becomes a child: `Spawned` on the parent, `Started(parent_run_id=…)` on the child
- child events are forwarded into the parent's stream in order
- a child's proposals reach the sink carrying the child's provenance
- `parent=None` in options makes a root run even inside a step

**`runtime/test_errors.py`**
- a component raising → `Failed` observation, the run continues to the next step
- a model port raising → `Ended(reason="failed")`, no exception escapes `run()`
- a sink raising → `Ended(reason="failed")`
- a governance port raising → `Ended(reason="failed")` — a broken host is not reasoned past

**`runtime/test_replay.py`**
- scripted model + fixed clock, run twice → JSON-identical event streams
- the same, with a `FanOut` — order within the fan is stable by step id

**`runtime/test_benchmark.py`**
- 100 sequential no-op steps under allow-all < 100 ms
- 50-way fan-out < 50 ms
- p50 per-step overhead reported in CI

**`adapters/agent/`**
- one tool call → `Composed` carrying one `Invoke`
- two parallel calls → `Composed` carrying a `FanOut`
- `compose` → the composition the model authored, verbatim
- `propose` → a `Proposed` event and a sink call
- `done` → `Completed`; no tool calls → `Completed`
- lease exhausted mid-loop → the loop ends cleanly, no exception
- `single` offers no `compose` and no `spawn` — the model is never shown them (D3)
- done before the floor → exactly one nudge, then accepted

**`adapters/basic/`** — allow-all allows everything including `ASSUME_WORST`; the stdout sink writes
one JSON line per proposal; `callable_component` carries the declared effects and turns an exception
into `Failed`.

**`adapters/contract/`** — the six abstract suites, subclassed by `basic`, `agent` and the runtime's
own doubles in Phase 0; by every adapter thereafter.

**`invariants/`** — the properties, held by walks over the tree rather than by review: the
kernel is pure and the runtime imports no adapter and no adapter imports another (`stands_alone`);
every narrow scope is enforced; every port implementation is held to its contract suite; every
registry has a store source (D66); every `harness.toml` key maps to a port or a profile and the
facade reaches only public APIs (D71); the wire is at parity — every context method and every
public method of `Thread`, `Approvals` and `Store` crosses or says why, every event kind is
published (D51, D67); the TypeScript client is current with the schemas (D68); a session leader
is started in one place (`start_held`, D77); the decisions index is true; these documents name
only paths that exist; the gate covers every package; a wheel carries what it needs; the live
job only runs when asked.

**`test_bare_harness.py`** — an MCP-shaped stub component, an agent component, a sub-agent, allow-all
governance, the stdout sink; the marker comes off, and the CI job fails if it is ever re-added.

## Cases — Phase 31

- `kernel/test_capabilities.py` locks the closed capability vocabularies, evidence validation,
  conservative unknown, total mismatch ordering and JSON round trips.
- provider tests prove absent facts remain unknown, malformed nested records fail by path, shipped
  Claude Code/Codex/OpenCode matrices are explicit, and discovery carries the same record.
- environment tests use fake matrices for every axis and the machine's live confinement proof;
  workspace writes and denied network are not allowed to imply confined reads or denied secrets.
- construction tests require refusal before agent open and identical accepted selections through
  `a_thread`, `Harness`, `ServeHost`, JSON-RPC protocol 3 and the generated TypeScript client.
- `wire/test_schemas.py` pins the schema publisher to this repository, preventing a default build
  from silently writing generated contracts outside the checkout (BUG-045).

## Cases — Phase 32

- `runtime/test_one_agent_surface.py` drives the same Thread lifecycle through a CLI-style
  `AgentPort` and a `ModelAgent`: tools, parking/settlement, holding, usage, activity, resume and
  interruption. A blocked model call must be cancelled at the provider call, and unknown usage
  stays unmetered.
- `runtime/test_item_inputs.py` proves exact canonical-JSON retention through 64 KiB and the typed
  omission marker above it; wire/schema/client tests prove the field crosses without a second fold.
- `runtime/test_streams.py` locks monotone bounded replay, replay-then-live-once, single attachment,
  typed stale cursors, injected-clock grace expiry, and heartbeats that allocate no id and enter no
  replay record.
- HTTP D94 integration proves the 15-second heartbeat, unique frame ids, reattachment with
  `Last-Event-ID`, and terminal stale-cursor behavior. The deterministic TypeScript silence smoke
  proves 45-second-default recovery without waiting on wall time.
- serve authentication tests lock file → environment → local-flag precedence, duplicate-source
  refusal, owner/regular-file/non-symlink/permission/size/UTF-8/one-line checks, argv secrecy and
  redacted failures.

## Cases — Phase 33

- `benchmarks/effect-transaction-v1.json` is a SHA-256-frozen corpus for legal histories,
  stale-authority refusal, duplicate delivery and crash/recovery outcomes; changing the evaluator
  requires a versioned successor, never a quiet fixture edit.
- authority, journal and transaction suites prove canonical secret-free records, legal
  compare-and-append state transitions, grant single-use, stale re-reads, child isolation and
  idempotent reconciliation. SQLite and Postgres reference journals run the same contract.
- `runtime/test_effect_records_are_public.py`, wire/schema/client parity and OpenTelemetry tests
  prove the generic `effect_recorded` lifecycle is public while receipt/refusal detail and grants
  do not leak into traces. Protocol 3 refuses older peers rather than omitting it.

## Cases — Phase 41

- `tests/adapters/environment/test_linux_confinement_is_native_first.py` proves the candidates'
  order per platform, `SHADOW_HDK_SANDBOX` narrowing and refusing an unknown name, the helper's
  argv, that a candidate confining nothing is passed over for one that does and that a refusal
  names each one tried, and that `Isolation.mechanism` reaches the capability evidence; six cases
  run only where the helper is installed on a Linux kernel (the CI runner) and prove it from the
  environment's side — outside denied, a socket refused, `/dev/null` writable in `read-only`, a
  temp file under the root.
- `tests/test_versions.py` holds the crate, its distribution and the kit's pin to one number.
- The D36 proof is mechanism-independent by construction: the same three legs on seatbelt, the
  helper and bubblewrap, and the same test file (`test_local_is_confined_for_real.py`) green on all
  three runners.

## Cases — Phase 45

- `tests/adapters/jsonl/test_cache_tokens_are_read.py`, `tests/adapters/langchain/test_cache_tokens_come_through.py`,
  `tests/runtime/test_the_meter_counts_cache_tokens.py` — the cache's tokens from the two dialects
  and LangChain, counted and carried, unknown never zero (D141).
- `tests/adapters/jsonl/test_a_session_gone_is_said.py` — the measured Claude Code and Codex texts
  → `session_gone`; a megabyte on stderr no longer wedges a turn (BUG-059);
  `tests/runtime/test_a_turn_names_why_it_failed.py` and `tests/wire/test_session_gone_crosses_the_wire.py`
  — the record's `failure`, `SessionGone`, the wire kind with both ids (D139).
- `tests/runtime/test_a_turns_words_are_the_turns.py`, `tests/wire/test_a_turns_words_cross_the_wire.py`
  — a turn's words on that turn's judgements only, the catalogue between turns without them, a
  resume's words replacing the record's, the reserved names (D140, BUG-061).
- `tests/adapters/modes/test_a_reach_from_the_process_is_an_egress_channel.py` — the four shipped
  policies over an uncontained reach, the `allow`-rule door in `ask`, a rule never widening (D138).
- `tests/invariants/test_a_provider_is_a_file.py` — no vendor's name in kernel or runtime code;
  the walk's self-test plants one.
- Live, recorded in the phase's history: Phase 36's planning proof on Claude Code; Codex's argv
  with `-m` and `-c model_reasoning_effort`; cache tokens and `session_gone` on both CLIs.
